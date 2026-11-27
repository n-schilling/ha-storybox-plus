"""The push channel against a simulated MQTT broker: subscriptions, parsing, reconnects, commands."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Generator
import contextlib
import itertools
import json
import logging
import ssl
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import aiomqtt
import pytest

from custom_components.storybox_plus.cloud import (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SETTINGS_APPLIED,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    Battery,
    CloudAuthError,
    CloudConnectionError,
    Playback,
    PushClient,
    PushEvent,
    SleepTimer,
    TokenSet,
    Volume,
)
from custom_components.storybox_plus.cloud.push import (
    BACKOFF_FIRST,
    HOST,
    PORT,
    SESSION_EXPIRY,
    SUBSCRIBED,
    TOPIC_PREFIX,
)

from .conftest import MAC, USER_ID

OTHER_MAC = "0A1B2C3D4E5F"
SSL_CONTEXT = ssl.create_default_context()


def topics(mac: str) -> set[str]:
    """Return the topics subscribed for one box."""
    return {f"{TOPIC_PREFIX}/{mac}/{topic}" for topic in SUBSCRIBED}


class FakeMqttClient:
    """One connection to the broker, as aiomqtt.Client offers it."""

    def __init__(self, broker: FakeBroker, hostname: str, port: int, **kwargs: Any) -> None:
        self.broker = broker
        self.hostname = hostname
        self.port = port
        self.kwargs = kwargs
        self.subscriptions: list[str] = []
        self.unsubscriptions: list[str] = []
        self.published: list[tuple[str, str, int]] = []
        self.publish_error: Exception | None = None
        self.open = False
        self._queue: asyncio.Queue[Any] = asyncio.Queue()

    async def __aenter__(self) -> FakeMqttClient:
        if self.broker.connect_errors:
            raise self.broker.connect_errors.pop(0)
        self.open = True
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.open = False

    @property
    def messages(self) -> AsyncIterator[Any]:
        """Yield what the test feeds, until it feeds an error."""
        return self._messages()

    async def _messages(self) -> AsyncIterator[Any]:
        while True:
            item = await self._queue.get()
            if isinstance(item, Exception):
                raise item
            yield item

    async def subscribe(self, topic: str, qos: int = 0) -> None:
        assert qos == 1
        self.subscriptions.append(topic)

    async def unsubscribe(self, topic: str) -> None:
        self.unsubscriptions.append(topic)

    async def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append((topic, payload, qos))

    def feed(self, topic: str, payload: Any) -> None:
        """Deliver one message."""
        self._queue.put_nowait(SimpleNamespace(topic=topic, payload=payload))

    def drop(self) -> None:
        """Lose the connection."""
        self._queue.put_nowait(aiomqtt.MqttError("connection lost"))


class FakeBroker:
    """Creates the connections and remembers them."""

    def __init__(self) -> None:
        self.clients: list[FakeMqttClient] = []
        self.connect_errors: list[Exception] = []

    def __call__(self, hostname: str, port: int = 1883, **kwargs: Any) -> FakeMqttClient:
        client = FakeMqttClient(self, hostname, port, **kwargs)
        self.clients.append(client)
        return client

    @property
    def current(self) -> FakeMqttClient:
        """Return the newest connection."""
        return self.clients[-1]


class FakeAuth:
    """Hands out access tokens, or the errors a test asks for."""

    def __init__(self) -> None:
        self.outcomes: list[Exception] = []
        self.refreshes = 0

    async def async_refresh(self) -> TokenSet:
        self.refreshes += 1
        if self.outcomes:
            raise self.outcomes.pop(0)
        return TokenSet(f"access-{self.refreshes}", "refresh", time.time() + 300, None)


class _Delegating:
    """Stands in for a module, overriding a few names."""

    def __init__(self, module: Any, **overrides: Any) -> None:
        self._module = module
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._module, name)


@pytest.fixture
def broker() -> Generator[FakeBroker]:
    """Replace aiomqtt's client by the simulated broker."""
    fake = FakeBroker()
    with patch(
        "custom_components.storybox_plus.cloud.push.aiomqtt",
        _Delegating(aiomqtt, Client=fake),
    ):
        yield fake


@pytest.fixture
def sleeps() -> Generator[list[float]]:
    """Record the backoff pauses of the channel instead of waiting."""
    recorded: list[float] = []

    async def sleep(delay: float) -> None:
        recorded.append(delay)
        await asyncio.sleep(0)

    with patch(
        "custom_components.storybox_plus.cloud.push.asyncio",
        _Delegating(asyncio, sleep=sleep),
    ):
        yield recorded


class Channel:
    """A running push client with what it reported."""

    def __init__(self, auth: FakeAuth, on_connected: bool = True) -> None:
        self.auth = auth
        self.events: list[PushEvent] = []
        self.connections: list[bool] = []
        self.push = PushClient(
            auth,  # type: ignore[arg-type]
            USER_ID,
            ssl_context=SSL_CONTEXT,
            on_event=self.events.append,
            on_connected=self.connections.append if on_connected else None,
        )
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Run the loop in the background."""
        self.task = asyncio.get_running_loop().create_task(self.push.async_run())

    async def until(self, condition: Callable[[], bool], steps: int = 100) -> None:
        """Let the loop run until the condition holds."""
        for _ in range(steps):
            if condition():
                return
            await asyncio.sleep(0)
        raise AssertionError("condition not met")

    async def stop(self) -> None:
        """Cancel the loop."""
        assert self.task is not None
        if not self.task.done():
            self.task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.task


@pytest.fixture
async def channel(broker: FakeBroker, sleeps: list[float]) -> AsyncIterator[Channel]:
    """A connected channel listening to one box."""
    running = Channel(FakeAuth())
    running.push.set_boxes([MAC])
    running.start()
    await running.until(lambda: running.push.connected)
    yield running
    await running.stop()


async def test_connects_and_subscribes(broker: FakeBroker, channel: Channel) -> None:
    """The connection carries the account and token; every topic of the box is subscribed."""
    client = broker.current
    assert client.hostname == HOST
    assert client.port == PORT
    assert client.kwargs["username"] == USER_ID
    assert client.kwargs["password"] == "access-1"
    assert client.kwargs["identifier"].startswith(f"{USER_ID}_storybox_plus_")
    assert client.kwargs["protocol"] is aiomqtt.ProtocolVersion.V5
    assert client.kwargs["transport"] == "websockets"
    assert client.kwargs["tls_context"] is SSL_CONTEXT
    assert client.kwargs["clean_start"] is False
    assert client.kwargs["properties"].SessionExpiryInterval == SESSION_EXPIRY
    assert set(client.subscriptions) == topics(MAC)
    assert len(client.subscriptions) == len(SUBSCRIBED)
    assert channel.connections == [True]
    assert channel.push.connected
    assert channel.auth.refreshes == 1


async def test_boxes_followed_while_connected(broker: FakeBroker, channel: Channel) -> None:
    """Boxes that join are subscribed on the open connection, boxes that leave unsubscribed."""
    client = broker.current
    channel.push.set_boxes([MAC, OTHER_MAC, ""])
    await channel.until(lambda: len(client.subscriptions) == 2 * len(SUBSCRIBED))
    assert set(client.subscriptions) == topics(MAC) | topics(OTHER_MAC)
    assert client.unsubscriptions == []

    channel.push.set_boxes([OTHER_MAC])
    await channel.until(lambda: len(client.unsubscriptions) == len(SUBSCRIBED))
    assert set(client.unsubscriptions) == topics(MAC)
    assert len(client.subscriptions) == 2 * len(SUBSCRIBED)

    # The same set changes nothing
    channel.push.set_boxes([OTHER_MAC])
    await asyncio.sleep(0)
    assert len(client.subscriptions) == 2 * len(SUBSCRIBED)
    assert len(client.unsubscriptions) == len(SUBSCRIBED)


async def test_boxes_set_before_connecting(broker: FakeBroker, sleeps: list[float]) -> None:
    """Boxes known before the connection are subscribed as soon as it is up; none means nothing."""
    running = Channel(FakeAuth())
    running.start()
    await running.until(lambda: running.push.connected)
    assert broker.current.subscriptions == []
    running.push.set_boxes([MAC])
    await running.until(lambda: len(broker.current.subscriptions) == len(SUBSCRIBED))
    await running.stop()
    assert running.connections == [True, False]


@pytest.mark.parametrize(
    ("topic", "payload", "expected"),
    [
        (
            TOPIC_BATTERY,
            b'{"percent": 80, "status": "charging"}',
            Battery(percent=80, charging=True, status="charging"),
        ),
        (TOPIC_BATTERY, b'{"percent": null, "status": null}', Battery(None, None, None)),
        (TOPIC_ONLINE, b'{"onlineState": "online"}', True),
        (TOPIC_ONLINE, b'{"onlineState": "offline"}', False),
        (TOPIC_VOLUME, b'{"level": 7, "hardwarePercentage": 55}', Volume(level=7, percent=55)),
        (
            TOPIC_SLEEP_TIMER,
            b'{"stl": {"state": "on", "duration": 600, "until": 1760000000}}',
            SleepTimer(state="on", duration=600, until=Mock()),
        ),
        (TOPIC_BATTERY, b"[1, 2]", Battery(None, None, None)),
        (TOPIC_SETTINGS_APPLIED, b'{"anything": 1}', True),
        (TOPIC_SETTINGS_APPLIED, b"", True),
    ],
)
async def test_messages_are_parsed(
    broker: FakeBroker, channel: Channel, topic: str, payload: bytes, expected: Any
) -> None:
    """Every subscribed topic is parsed into its value and delivered with the box's MAC."""
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{topic}", payload)
    await channel.until(lambda: bool(channel.events))
    (event,) = channel.events
    assert event.mac == MAC
    assert event.topic == topic
    if isinstance(expected, SleepTimer):
        assert isinstance(event.data, SleepTimer)
        assert (event.data.state, event.data.duration) == ("on", 600)
        assert event.data.until is not None
    else:
        assert event.data == expected


async def test_playback_messages(broker: FakeBroker, channel: Channel) -> None:
    """Playback carries the figure; an empty message means it was taken off."""
    now_ms = int(time.time() * 1000)
    broker.current.feed(
        f"{TOPIC_PREFIX}/{MAC}/{TOPIC_PLAYBACK}",
        json.dumps(
            {
                "tonie": "t1",
                "paused": False,
                "chapter": 1,
                "chapterUntilMs": now_ms + 150_000,
                "chapterDuration": 200,
                "ended": False,
                "downloading": False,
            }
        ).encode(),
    )
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{TOPIC_PLAYBACK}", b"")
    await channel.until(lambda: len(channel.events) == 2)
    playing, removed = channel.events
    assert isinstance(playing.data, Playback)
    assert playing.data.tonie_id == "t1"
    assert playing.data.chapter == 1
    assert playing.data.playing
    assert playing.data.position == pytest.approx(50, abs=2)
    assert isinstance(removed.data, Playback)
    assert removed.data.tonie_id is None
    assert not removed.data.playing


async def test_playback_messages_are_logged_by_their_keys(
    broker: FakeBroker, channel: Channel, caplog: pytest.LogCaptureFixture
) -> None:
    """With debug logging on, a playback message leaves only its keys in the log, no values."""
    caplog.set_level(logging.DEBUG, logger="custom_components.storybox_plus.cloud.push")
    broker.current.feed(
        f"{TOPIC_PREFIX}/{MAC}/{TOPIC_PLAYBACK}",
        json.dumps(
            {"tonie": "t1-secret", "chapter": 7, "contentVersion": 1730000000, "paused": False}
        ).encode(),
    )
    await channel.until(lambda: bool(channel.events))
    (event,) = channel.events
    assert isinstance(event.data, Playback)
    assert event.data.content_version == 1730000000
    logged = [r.message for r in caplog.records if "Playback message" in r.message]
    assert logged == [
        "Playback message with the keys ['chapter', 'contentVersion', 'paused', 'tonie']"
    ]
    assert "t1-secret" not in caplog.text
    assert "1730000000" not in caplog.text


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        (f"{TOPIC_PREFIX}/{MAC}/{TOPIC_BATTERY}", b"{not json"),
        (f"{TOPIC_PREFIX}/{MAC}/unknown/topic", b"{}"),
        (f"{TOPIC_PREFIX}/{MAC}", b"{}"),
        (f"internal/toniebox/{MAC}/{TOPIC_BATTERY}", b'{"percent": 1}'),
        (f"external/other/{MAC}/{TOPIC_BATTERY}", b'{"percent": 1}'),
    ],
)
async def test_unusable_messages_are_ignored(
    broker: FakeBroker, channel: Channel, topic: str, payload: bytes
) -> None:
    """Garbage, unknown topics and foreign prefixes deliver nothing and break nothing."""
    broker.current.feed(topic, payload)
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{TOPIC_VOLUME}", b'{"level": 3}')
    await channel.until(lambda: bool(channel.events))
    assert [e.data for e in channel.events] == [Volume(level=3)]


async def test_payload_that_is_no_bytes(broker: FakeBroker, channel: Channel) -> None:
    """A payload of another type counts as empty."""
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{TOPIC_ONLINE}", None)
    await channel.until(lambda: bool(channel.events))
    assert channel.events[0].data is None


async def test_reconnects_after_drop_with_growing_backoff(
    broker: FakeBroker, sleeps: list[float], channel: Channel
) -> None:
    """A lost connection is reported, then reopened with a fresh token after a pause that doubles."""
    first = broker.current
    first.drop()
    await channel.until(lambda: len(broker.clients) == 2 and channel.push.connected)
    assert channel.connections == [True, False, True]
    assert sleeps == [BACKOFF_FIRST]
    assert broker.current is not first
    assert broker.current.kwargs["password"] == "access-2"
    assert set(broker.current.subscriptions) == topics(MAC)

    broker.current.drop()
    await channel.until(lambda: len(broker.clients) == 3 and channel.push.connected)
    assert sleeps == [BACKOFF_FIRST, 2 * BACKOFF_FIRST]
    assert channel.connections == [True, False, True, False, True]


async def test_long_session_resets_backoff(
    broker: FakeBroker, sleeps: list[float], channel: Channel
) -> None:
    """After a connection that lasted, the pause starts small again."""
    base = time.monotonic()
    clock = Mock()
    # first session dropped after a second, second one started at +10 and dropped at +100
    clock.monotonic.side_effect = itertools.chain(
        [base + 1, base + 10, base + 100], itertools.repeat(base + 1000)
    )
    with patch("custom_components.storybox_plus.cloud.push.time", clock):
        broker.current.drop()
        await channel.until(lambda: len(broker.clients) == 2 and channel.push.connected)
        assert sleeps == [BACKOFF_FIRST]
        broker.current.drop()
        await channel.until(lambda: len(broker.clients) == 3 and channel.push.connected)
    assert sleeps == [BACKOFF_FIRST, BACKOFF_FIRST]


async def test_token_expiry_reopens_at_once_and_stays_up(
    broker: FakeBroker,
    sleeps: list[float],
    channel: Channel,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The broker's drop at the token's expiry is routine: no pause, no "down", only debug lines."""
    base = time.monotonic()
    clock = Mock()
    # the session lasted as long as its token (300 s); the next one runs on
    clock.monotonic.side_effect = itertools.chain([base + 299], itertools.repeat(base + 299))
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    with patch("custom_components.storybox_plus.cloud.push.time", clock):
        broker.current.drop()
        await channel.until(lambda: len(broker.clients) == 2 and channel.push.connected)
    assert sleeps == []
    assert channel.connections == [True]
    assert broker.current.kwargs["password"] == "access-2"
    levels = {
        r.getMessage().split(" ")[2]: r.levelno
        for r in caplog.records
        if "Push channel" in r.getMessage()
    }
    assert levels == {"closed": logging.DEBUG, "connected,": logging.DEBUG}


async def test_token_expiry_then_no_token_goes_down(
    broker: FakeBroker, sleeps: list[float], channel: Channel
) -> None:
    """A routine reopening that gets no token reports the channel down and waits."""
    base = time.monotonic()
    clock = Mock()
    clock.monotonic.side_effect = itertools.chain([base + 299], itertools.repeat(base + 299))
    channel.auth.outcomes.append(CloudConnectionError("Timeout while talking to the login server"))
    with patch("custom_components.storybox_plus.cloud.push.time", clock):
        broker.current.drop()
        await channel.until(lambda: len(broker.clients) == 2 and channel.push.connected)
    assert sleeps == [BACKOFF_FIRST]
    assert channel.connections == [True, False, True]


async def test_connect_error_backs_off(broker: FakeBroker, sleeps: list[float]) -> None:
    """A broker that refuses the connection is tried again after the pause."""
    broker.connect_errors.append(aiomqtt.MqttCodeError(5, "not authorized"))
    running = Channel(FakeAuth())
    running.push.set_boxes([MAC])
    running.start()
    await running.until(lambda: running.push.connected)
    assert len(broker.clients) == 2
    assert sleeps == [BACKOFF_FIRST]
    assert running.connections == [True]
    assert running.auth.refreshes == 2
    await running.stop()
    assert running.connections == [True, False]


async def test_refused_token_ends_the_loop(broker: FakeBroker, sleeps: list[float]) -> None:
    """A login the server refuses for good is passed on; nothing is retried."""
    auth = FakeAuth()
    auth.outcomes.append(CloudAuthError("Login refused (invalid_grant)"))
    running = Channel(auth)
    running.start()
    assert running.task is not None
    with pytest.raises(CloudAuthError):
        await running.task
    assert broker.clients == []
    assert sleeps == []
    assert running.connections == []


async def test_unreachable_login_server_is_retried(broker: FakeBroker, sleeps: list[float]) -> None:
    """Without a token the channel waits and asks again."""
    auth = FakeAuth()
    auth.outcomes.append(CloudConnectionError("Timeout while talking to the login server"))
    running = Channel(auth)
    running.start()
    await running.until(lambda: running.push.connected)
    assert sleeps == [BACKOFF_FIRST]
    assert auth.refreshes == 2
    await running.stop()


async def test_commands_need_the_connection(broker: FakeBroker, sleeps: list[float]) -> None:
    """Without the channel a command is a connection error."""
    running = Channel(FakeAuth())
    with pytest.raises(CloudConnectionError):
        await running.push.async_play(MAC)


async def test_commands_are_published(broker: FakeBroker, channel: Channel) -> None:
    """Play, pause, position, volume and sleep go to the box's control topics as JSON."""
    client = broker.current
    await channel.push.async_play(MAC)
    await channel.push.async_pause(MAC)
    await channel.push.async_set_position(MAC, 2, 42_700)
    await channel.push.async_set_position(MAC, -1, -5)
    await channel.push.async_set_volume(MAC, 7)
    await channel.push.async_set_volume(MAC, 99)
    await channel.push.async_set_volume(MAC, -3)
    await channel.push.async_set_sleep_timer(MAC, 1800)
    await channel.push.async_set_sleep_timer(MAC, 99_999)
    await channel.push.async_set_sleep_timer(MAC, 0)
    await channel.push.async_clear_sleep_timer(MAC)
    await channel.push.async_sleep(MAC)
    playback = f"{TOPIC_PREFIX}/{MAC}/app-control/playback"
    volume = f"{TOPIC_PREFIX}/{MAC}/app-control/volume"
    stl = f"{TOPIC_PREFIX}/{MAC}/app-control/stl"
    sleep = f"{TOPIC_PREFIX}/{MAC}/app-control/sleep"
    assert [(t, json.loads(p), q) for t, p, q in client.published] == [
        (playback, {"action": "start"}, 1),
        (playback, {"action": "pause"}, 1),
        (playback, {"action": "setPosition", "chapter": 2, "ms": 42700}, 1),
        (playback, {"action": "setPosition", "chapter": 0, "ms": 0}, 1),
        (volume, {"level": 7}, 1),
        (volume, {"level": 13}, 1),
        (volume, {"level": 0}, 1),
        (stl, {"state": "on", "duration": 1800}, 1),
        # The box counts the timer in 16 bits; more would wrap around
        (stl, {"state": "on", "duration": 65535}, 1),
        (stl, {"state": "on", "duration": 1}, 1),
        (stl, {"state": "off"}, 1),
        # Sleeping now is a short timer and the sleep command, as the app sends it
        (stl, {"state": "on", "duration": 300}, 1),
        (sleep, {}, 1),
    ]


async def test_failed_publish(broker: FakeBroker, channel: Channel) -> None:
    """A publish the broker refuses is a connection error that names the command."""
    broker.current.publish_error = aiomqtt.MqttError("not connected")
    with pytest.raises(CloudConnectionError, match="Command volume not sent"):
        await channel.push.async_set_volume(MAC, 5)


async def test_without_connected_callback(broker: FakeBroker, sleeps: list[float]) -> None:
    """The callback for the connection state is optional."""
    running = Channel(FakeAuth(), on_connected=False)
    running.start()
    await running.until(lambda: running.push.connected)
    broker.current.drop()
    await running.until(lambda: len(broker.clients) == 2 and running.push.connected)
    await running.stop()
    assert running.connections == []


async def test_failing_handler_keeps_the_channel(
    broker: FakeBroker, sleeps: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    """A message the handler cannot take is logged; the next one arrives on the same connection."""
    received: list[PushEvent] = []

    def on_event(event: PushEvent) -> None:
        if not received:
            received.append(event)
            raise KeyError("a field the handler did not expect")
        received.append(event)

    push = PushClient(FakeAuth(), USER_ID, ssl_context=SSL_CONTEXT, on_event=on_event)  # type: ignore[arg-type]
    push.set_boxes([MAC])
    task = asyncio.get_running_loop().create_task(push.async_run())
    running = Channel(FakeAuth())
    await running.until(lambda: push.connected)
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{TOPIC_VOLUME}", b'{"level": 3}')
    broker.current.feed(f"{TOPIC_PREFIX}/{MAC}/{TOPIC_VOLUME}", b'{"level": 4}')
    await running.until(lambda: len(received) == 2)
    assert [e.data for e in received] == [Volume(level=3), Volume(level=4)]
    assert len(broker.clients) == 1
    assert push.connected
    assert "Push message on" in caplog.text
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_unexpected_failure_reconnects(
    broker: FakeBroker, sleeps: list[float], channel: Channel, caplog: pytest.LogCaptureFixture
) -> None:
    """An error nobody expected closes the connection and opens a new one instead of ending the loop."""
    broker.current._queue.put_nowait(RuntimeError("something odd"))
    await channel.until(lambda: len(broker.clients) == 2 and channel.push.connected)
    assert channel.connections == [True, False, True]
    assert sleeps == [BACKOFF_FIRST]
    assert "Push channel failed" in caplog.text
