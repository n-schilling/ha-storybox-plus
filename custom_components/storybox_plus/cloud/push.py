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
    Battery,
    Playback,
    SleepTimer,
    Volume,
    parse_battery,
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
SUBSCRIBED = (TOPIC_BATTERY, TOPIC_ONLINE, TOPIC_PLAYBACK, TOPIC_VOLUME, TOPIC_SLEEP_TIMER)

COMMAND_PLAYBACK = "playback"
COMMAND_VOLUME = "volume"
COMMAND_SLEEP_TIMER = "stl"
COMMAND_SLEEP = "sleep"
# The box keeps the timer as an unsigned 16-bit number of seconds; more wraps around
SLEEP_TIMER_MAX_SECONDS = 65_535
SLEEP_TIMER_MAX_MINUTES = SLEEP_TIMER_MAX_SECONDS // 60
# The app arms this timer right before it tells the box to sleep
SLEEP_NOW_SECONDS = 300

BACKOFF_FIRST = 5
BACKOFF_MAX = 300
KEEPALIVE = 60
# Seconds the broker should keep the session (and queue messages) between reconnects
SESSION_EXPIRY = 600

type PushData = Battery | Playback | Volume | SleepTimer | bool | None


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
        self._auth = auth
        self._user_id = user_id
        self._ssl = ssl_context
        self._on_event = on_event
        self._on_connected = on_connected
        self._host = host
        self._port = port
        self._macs: set[str] = set()
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

    async def async_run(self) -> None:
        """Keep the channel open until cancelled.

        A refused token ends the loop with CloudAuthError: the account needs a
        new login, which the caller asks the user for. Any other failure,
        expected or not, closes the connection and opens a new one.
        """
        backoff = BACKOFF_FIRST
        while True:
            try:
                token = (await self._auth.async_refresh()).access_token
            except CloudAuthError:
                raise
            except CloudError as err:
                _LOGGER.debug("Push channel: no token (%s), retry in %ss", err, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
                continue
            started = time.monotonic()
            try:
                await self._async_session(token)
            except aiomqtt.MqttError as err:
                lasted = time.monotonic() - started
                if lasted > 60:
                    backoff = BACKOFF_FIRST
                level = logging.DEBUG if lasted > 60 else logging.INFO
                _LOGGER.log(level, "Push channel closed (%s), reconnecting in %ss", err, backoff)
            except Exception:
                _LOGGER.exception("Push channel failed, reconnecting in %ss", backoff)
            finally:
                self._set_connected(False)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    async def _async_session(self, token: str) -> None:
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
            subscribed: set[str] = set()
            await self._async_subscribe(client, subscribed)
            self._set_connected(True)
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
                event = self._parse(str(message.topic), message.payload)
                if event is not None:
                    self._on_event(event)
            except Exception:
                _LOGGER.exception("Push message on %s not handled", message.topic)

    async def _async_follow_boxes(self, client: aiomqtt.Client, subscribed: set[str]) -> None:
        while True:
            await self._resubscribe.wait()
            self._resubscribe.clear()
            await self._async_subscribe(client, subscribed)

    async def _async_subscribe(self, client: aiomqtt.Client, subscribed: set[str]) -> None:
        for mac in self._macs - subscribed:
            for topic in SUBSCRIBED:
                await client.subscribe(f"{TOPIC_PREFIX}/{mac}/{topic}", qos=1)
            subscribed.add(mac)
        for mac in subscribed - self._macs:
            for topic in SUBSCRIBED:
                await client.unsubscribe(f"{TOPIC_PREFIX}/{mac}/{topic}")
            subscribed.discard(mac)

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

    async def async_clear_sleep_timer(self, mac: str) -> None:
        """Cancel the sleep timer."""
        await self.async_command(mac, COMMAND_SLEEP_TIMER, {"state": "off"})

    async def async_sleep(self, mac: str) -> None:
        """Put the box to sleep now, the way the app does: a short timer, then the sleep command.

        The box goes offline; the cloud cannot wake it again.
        """
        await self.async_set_sleep_timer(mac, SLEEP_NOW_SECONDS)
        await self.async_command(mac, COMMAND_SLEEP, {})
