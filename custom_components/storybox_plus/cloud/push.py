"""The push channel: live state of the Toniebox 2 and commands to it.

The cloud runs an MQTT 5 broker behind a WebSocket. It accepts the account's
UUID as user name and the access token as password, drops the connection when
the token expires (every few minutes) and refuses a reconnect with the old
one. The loop here refreshes the token before every connect and backs off
when the broker is not reachable.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass
import json
import logging
import ssl
import time
from typing import Any
import uuid

import aiomqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from .auth import Auth
from .errors import CloudAuthError, CloudConnectionError, CloudError
from .models import (
    VOLUME_LEVELS,
    Alarm,
    AlarmRing,
    Battery,
    Headphones,
    Playback,
    SleepTimer,
    Volume,
    parse_alarm_ring,
    parse_battery,
    parse_headphones,
    parse_online,
    parse_playback,
    parse_sleep_timer,
    parse_volume,
)

_LOGGER = logging.getLogger(__name__)

HOST = "ici.tonie.cloud"
PORT = 443
TOPIC_PREFIX = "external/toniebox"
TOPIC_BATTERY = "metrics/battery"
TOPIC_ONLINE = "online-state"
TOPIC_PLAYBACK = "playback/state"
TOPIC_VOLUME = "volume/state"
TOPIC_SLEEP_TIMER = "app-reply/bedtime-state"
TOPIC_HEADPHONES = "metrics/headphones"
# The tone an alarm rings now; {"tone": null} once it stopped
TOPIC_ALARM = "app-reply/alarm"
# The box took the settings saved in the cloud; what it sends with it is not read
TOPIC_SETTINGS_APPLIED = "settings-applied"
SUBSCRIBED = (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_VOLUME,
    TOPIC_SLEEP_TIMER,
    TOPIC_HEADPHONES,
    TOPIC_SETTINGS_APPLIED,
    TOPIC_ALARM,
)
# While the channel is recorded: every topic of a box, the app's commands included
EVERYTHING = ("#",)

COMMAND_PLAYBACK = "playback"
COMMAND_VOLUME = "volume"
COMMAND_SLEEP_TIMER = "stl"
COMMAND_SLEEP = "sleep"
# The app sends this before it arms an alarm; without it the box jumps to full volume
COMMAND_ALARM_PREVIEW = "alarm-preview"
# The box keeps the timer as an unsigned 16-bit number of seconds; more wraps around
SLEEP_TIMER_MAX_SECONDS = 65_535
SLEEP_TIMER_MAX_MINUTES = SLEEP_TIMER_MAX_SECONDS // 60
# The app arms this timer right before it tells the box to sleep
SLEEP_NOW_SECONDS = 300

BACKOFF_FIRST = 5
BACKOFF_MAX = 300
KEEPALIVE = 60
# A session that ends this close to the token's expiry ended because of it (s)
EXPIRY_GRACE = 15
# Seconds the broker should keep the session (and queue messages) between reconnects
SESSION_EXPIRY = 600

type PushData = Battery | Playback | Volume | SleepTimer | Headphones | AlarmRing | bool | None
# Gets every message raw while the channel is recorded: the box's MAC, the topic below it, the payload
type CaptureSink = Callable[[str, str, bytes], None]


@dataclass(frozen=True, slots=True)
class PushEvent:
    """One message of a box."""

    mac: str
    topic: str
    data: PushData


class PushClient:
    """Keeps the push channel open and forwards what the boxes report."""

    def __init__(
        self,
        auth: Auth,
        user_id: str,
        *,
        ssl_context: ssl.SSLContext,
        on_event: Callable[[PushEvent], None],
        on_connected: Callable[[bool], None] | None = None,
        host: str = HOST,
        port: int = PORT,
    ) -> None:
        """Deliver messages to on_event; on_connected tells when the channel is up or down."""
        self.seen_keys: dict[str, frozenset[str]] = {}
        self._auth = auth
        self._user_id = user_id
        self._ssl = ssl_context
        self._on_event = on_event
        self._on_connected = on_connected
        self._host = host
        self._port = port
        self._macs: set[str] = set()
        # What the broker's session holds per box; it outlives a connection
        self._held: dict[str, tuple[str, ...]] = {}
        self._capture: CaptureSink | None = None
        self._client: aiomqtt.Client | None = None
        self._connected = False
        self._resubscribe = asyncio.Event()
        # One client ID per instance; the broker keeps the session for it
        self._client_id = f"{user_id}_storybox_plus_{uuid.uuid4().hex[:12]}"

    @property
    def connected(self) -> bool:
        """Return whether the channel is open right now."""
        return self._connected

    def set_boxes(self, macs: Iterable[str]) -> None:
        """Tell which boxes to listen to; new ones are subscribed on the open connection."""
        wanted = {m for m in macs if m}
        if wanted == self._macs:
            return
        self._macs = wanted
        self._resubscribe.set()

    def set_capture(self, sink: CaptureSink | None) -> None:
        """Record every message raw into sink, or stop recording with None.

        While recording, a box is followed on all of its topics instead of
        the ones read; each message still arrives once.
        """
        if (sink is None) == (self._capture is None):
            self._capture = sink
            return
        self._capture = sink
        self._resubscribe.set()

    def _topics(self) -> tuple[str, ...]:
        return EVERYTHING if self._capture is not None else SUBSCRIBED

    async def async_run(self) -> None:
        """Keep the channel open until cancelled.

        The broker drops the connection when the access token expires (every
        five minutes). That end is routine: the channel opens again at once
        with a fresh token, logged at debug level only. Any other end waits
        before the next attempt, longer each time, and is logged at info
        level. A refused token ends the loop with CloudAuthError: the account
        needs a new login, which the caller asks the user for.
        """
        backoff = BACKOFF_FIRST
        # Whether the next connection is worth an info line: the first one, and
        # the first after a failure
        tell = True
        while True:
            try:
                tokens = await self._auth.async_refresh()
            except CloudAuthError:
                self._set_connected(False)
                raise
            except CloudError as err:
                self._set_connected(False)
                _LOGGER.debug("Push channel: no token (%s), retry in %ss", err, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
                tell = True
                continue
            started = time.monotonic()
            # The broker ends the session when this token expires
            lifetime = tokens.access_expires_in()
            routine = False
            try:
                await self._async_session(tokens.access_token, tell)
            except aiomqtt.MqttError as err:
                lasted = time.monotonic() - started
                routine = lasted >= lifetime - EXPIRY_GRACE
                if routine:
                    # The channel counts as up while it is reopened at once: what
                    # depends on it (listening time, battery) goes on undisturbed
                    _LOGGER.debug(
                        "Push channel closed as the token expired after %.0f s, reconnecting now",
                        lasted,
                    )
                else:
                    if lasted > 60:
                        backoff = BACKOFF_FIRST
                    _LOGGER.info(
                        "Push channel closed after %.0f s (%s), reconnecting in %ss",
                        lasted,
                        err,
                        backoff,
                    )
            except Exception:
                _LOGGER.exception("Push channel failed, reconnecting in %ss", backoff)
            finally:
                if not routine:
                    self._set_connected(False)
            if routine:
                backoff = BACKOFF_FIRST
                tell = False
                continue
            tell = True
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    async def _async_session(self, token: str, tell: bool = True) -> None:
        properties = Properties(PacketTypes.CONNECT)  # type: ignore[no-untyped-call]
        properties.SessionExpiryInterval = SESSION_EXPIRY
        async with aiomqtt.Client(
            self._host,
            port=self._port,
            username=self._user_id,
            password=token,
            identifier=self._client_id,
            protocol=aiomqtt.ProtocolVersion.V5,
            transport="websockets",
            websocket_path="/",
            tls_context=self._ssl,
            keepalive=KEEPALIVE,
            clean_start=False,
            properties=properties,
            timeout=30,
        ) as client:
            self._client = client
            subscribed: dict[str, tuple[str, ...]] = {}
            await self._async_subscribe(client, subscribed)
            self._set_connected(True)
            _LOGGER.log(
                logging.INFO if tell else logging.DEBUG,
                "Push channel connected, following %s boxes",
                len(subscribed),
            )
            self._resubscribe.clear()
            try:
                async with asyncio.TaskGroup() as group:
                    group.create_task(self._async_receive(client))
                    group.create_task(self._async_follow_boxes(client, subscribed))
            except* Exception as group_error:
                raise group_error.exceptions[0] from None
            finally:
                self._client = None

    async def _async_receive(self, client: aiomqtt.Client) -> None:
        async for message in client.messages:
            # One message that cannot be handled must not cost the channel
            try:
                if (sink := self._capture) is not None:
                    parts = str(message.topic).split("/", 3)
                    payload = message.payload
                    sink(
                        parts[2] if len(parts) > 2 else "",
                        parts[3] if len(parts) > 3 else str(message.topic),
                        bytes(payload) if isinstance(payload, bytes | bytearray) else b"",
                    )
                event = self._parse(str(message.topic), message.payload)
                _LOGGER.debug(
                    "Push message on …/%s: %s",
                    str(message.topic).rsplit("/", 2)[-1] if message.topic else "",
                    type(event).__name__ if event is not None else "ignored",
                )
                if event is not None:
                    self._on_event(event)
            except Exception:
                _LOGGER.exception("Push message on %s not handled", message.topic)

    async def _async_follow_boxes(
        self, client: aiomqtt.Client, subscribed: dict[str, tuple[str, ...]]
    ) -> None:
        while True:
            await self._resubscribe.wait()
            self._resubscribe.clear()
            await self._async_subscribe(client, subscribed)

    async def _async_subscribe(
        self, client: aiomqtt.Client, subscribed: dict[str, tuple[str, ...]]
    ) -> None:
        """Follow the wanted boxes on the topics wanted now, and nothing else.

        The broker keeps a session's subscriptions across reconnects, so what
        it holds from before (recording switched meanwhile) is dropped first:
        a message must not arrive twice.
        """
        wanted = self._topics()
        for mac in sorted(self._macs):
            if subscribed.get(mac) == wanted:
                continue
            held = self._held.get(mac)
            if held is not None and held != wanted:
                for topic in held:
                    await client.unsubscribe(f"{TOPIC_PREFIX}/{mac}/{topic}")
            for topic in wanted:
                await client.subscribe(f"{TOPIC_PREFIX}/{mac}/{topic}", qos=1)
            subscribed[mac] = self._held[mac] = wanted
        for mac in sorted((subscribed.keys() | self._held.keys()) - self._macs):
            topics = subscribed.pop(mac, None) or self._held[mac]
            for topic in topics:
                await client.unsubscribe(f"{TOPIC_PREFIX}/{mac}/{topic}")
            self._held.pop(mac, None)

    def _set_connected(self, connected: bool) -> None:
        if connected == self._connected:
            return
        self._connected = connected
        if self._on_connected is not None:
            self._on_connected(connected)

    def _parse(self, topic: str, payload: Any) -> PushEvent | None:
        parts = topic.split("/", 3)
        if len(parts) != 4 or f"{parts[0]}/{parts[1]}" != TOPIC_PREFIX:
            return None
        mac, subtopic = parts[2], parts[3]
        raw = payload if isinstance(payload, bytes | bytearray) else b""
        data: Any = None
        if raw.strip():
            try:
                data = json.loads(raw)
            except ValueError:
                _LOGGER.debug("Push channel: unreadable message on %s", subtopic)
                return None
        if not isinstance(data, dict):
            data = {}
        if data and subtopic in SUBSCRIBED and (subtopic != TOPIC_PLAYBACK or data.get("tonie")):
            # For the check of the interface: the keys of the last message per topic.
            # A box whose figure was taken off names no more than that
            self.seen_keys[subtopic] = frozenset(data)
        if subtopic == TOPIC_BATTERY:
            return PushEvent(mac, subtopic, parse_battery(data))
        if subtopic == TOPIC_ONLINE:
            return PushEvent(mac, subtopic, parse_online(data))
        if subtopic == TOPIC_PLAYBACK:
            _LOGGER.debug("Playback message with the keys %s", sorted(data))
            return PushEvent(mac, subtopic, parse_playback(data))
        if subtopic == TOPIC_VOLUME:
            return PushEvent(mac, subtopic, parse_volume(data))
        if subtopic == TOPIC_SLEEP_TIMER:
            return PushEvent(mac, subtopic, parse_sleep_timer(data))
        if subtopic == TOPIC_HEADPHONES:
            return PushEvent(mac, subtopic, parse_headphones(data))
        if subtopic == TOPIC_SETTINGS_APPLIED:
            return PushEvent(mac, subtopic, True)
        if subtopic == TOPIC_ALARM:
            return PushEvent(mac, subtopic, parse_alarm_ring(data))
        return None

    # ------------------------------------------------------------ commands

    async def async_command(self, mac: str, command: str, payload: dict[str, Any]) -> None:
        """Send one app-control command to a box."""
        client = self._client
        if client is None or not self._connected:
            raise CloudConnectionError("The push channel is not connected")
        try:
            await client.publish(
                f"{TOPIC_PREFIX}/{mac}/app-control/{command}", json.dumps(payload), qos=1
            )
        except aiomqtt.MqttError as err:
            raise CloudConnectionError(f"Command {command} not sent: {err}") from err

    async def async_play(self, mac: str) -> None:
        """Continue playing."""
        await self.async_command(mac, COMMAND_PLAYBACK, {"action": "start"})

    async def async_pause(self, mac: str) -> None:
        """Pause."""
        await self.async_command(mac, COMMAND_PLAYBACK, {"action": "pause"})

    async def async_set_position(self, mac: str, chapter: int, milliseconds: int = 0) -> None:
        """Jump to a position in a chapter (0-based chapter index)."""
        await self.async_command(
            mac,
            COMMAND_PLAYBACK,
            {"action": "setPosition", "chapter": max(0, chapter), "ms": max(0, milliseconds)},
        )

    async def async_set_volume(self, mac: str, level: int) -> None:
        """Set the volume level (0..13)."""
        await self.async_command(mac, COMMAND_VOLUME, {"level": max(0, min(VOLUME_LEVELS, level))})

    async def async_set_sleep_timer(self, mac: str, seconds: int) -> None:
        """Let the box fall asleep after the given seconds; a running timer is replaced."""
        await self.async_command(
            mac,
            COMMAND_SLEEP_TIMER,
            {"state": "on", "duration": max(1, min(SLEEP_TIMER_MAX_SECONDS, seconds))},
        )

    async def async_set_alarm(self, mac: str, seconds: int, alarm: Alarm) -> None:
        """Let the alarm ring once after the given seconds, the way the app arms it.

        The alarm is part of the sleep timer: it replaces a running timer, and
        a timer set afterwards replaces the alarm.
        """
        await self.async_command(mac, COMMAND_ALARM_PREVIEW, {"tone": None})
        await self.async_command(
            mac,
            COMMAND_SLEEP_TIMER,
            {
                "state": "on",
                "duration": max(1, min(SLEEP_TIMER_MAX_SECONDS, seconds)),
                "oneTimeAlarm": True,
                "alarm": {
                    "morningLight": alarm.morning_light,
                    "tone": alarm.tone,
                    "volume": alarm.volume,
                },
            },
        )

    async def async_clear_sleep_timer(self, mac: str) -> None:
        """Cancel the sleep timer."""
        await self.async_command(mac, COMMAND_SLEEP_TIMER, {"state": "off"})

    async def async_sleep(self, mac: str) -> None:
        """Put the box to sleep now, the way the app does: a short timer, then the sleep command.

        The box goes offline; the cloud cannot wake it again.
        """
        await self.async_set_sleep_timer(mac, SLEEP_NOW_SECONDS)
        await self.async_command(mac, COMMAND_SLEEP, {})
