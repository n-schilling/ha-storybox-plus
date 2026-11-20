"""Fixtures: the cloud of the boxes simulated in memory.

``FakeCloud`` answers the login server and the REST/GraphQL API through
``aioclient_mock`` from a few dicts per account; ``FakePush`` stands in for
the push channel, so tests inject messages and read the commands sent.
Nothing here reaches the network.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiohasupervisor.models import AddonState
import aiohttp
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker, AiohttpClientMockResponse
from yarl import URL

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.storybox_plus import log as log_module
from custom_components.storybox_plus.cloud import (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    CloudConnectionError,
    Playback,
    PushClient,
    PushEvent,
    SleepTimer,
    Volume,
)
from custom_components.storybox_plus.cloud.auth import TOKEN_URL
from custom_components.storybox_plus.cloud.models import parse_battery
from custom_components.storybox_plus.cloud.push import PushData
from custom_components.storybox_plus.cloud.rest import API_BASE
from custom_components.storybox_plus.const import (
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    DOMAIN,
    TESTED_BACKEND_RELEASE,
)
from custom_components.storybox_plus.ids import box_identifier

# The account, the household and what is in it
USER_ID = "0f3c5f2a-1111-4d2e-9c3b-000000000001"
EMAIL = "test@example.com"
PASSWORD = "correct-horse"
HOUSEHOLD_ID = "hh1"
HOUSEHOLD_NAME = "Familie Muster"
# A Toniebox 2 with the push channel
BOX_ID = "box1"
BOX_NAME = "Kinderzimmer"
MAC = "A1B2C3D4E5F6"
# A classic box: the cloud knows only when it was last seen
CLASSIC_BOX_ID = "box2"
CLASSIC_BOX_NAME = "Flur"
# The figures
TONIE_ID = "t1"
TONIE_NAME = "Schlummerjaguar"
TONIE_SERIES = "Schlummerbande"
CREATIVE_ID = "c1"
CREATIVE_NAME = "Kreativ"
DISC_ID = "d1"
DISC_NAME = "Disc Eins"
# The storage the cloud hands out upload tickets for
S3_URL = "https://uploads.example.com/bucket"

JSON_HEADERS = {"Content-Type": "application/json"}
# What GET /version answers: the version this release was tested with
BACKEND_VERSION = f"{TESTED_BACKEND_RELEASE}/602b7aff2"


# The mocked response lacks aiohttp's content_length, which the client reads
def _content_length(self: AiohttpClientMockResponse) -> int:
    return len(self._response)


if not hasattr(AiohttpClientMockResponse, "content_length"):
    AiohttpClientMockResponse.content_length = property(_content_length)  # type: ignore[attr-defined]


# ---------------------------------------------------------------- payloads


def tb2_box(
    box_id: str = BOX_ID,
    name: str = BOX_NAME,
    mac: str | None = MAC,
    online: str | None = "online",
    placed: str | None = TONIE_ID,
) -> dict[str, Any]:
    """Return a Toniebox 2 as GET /households/{id}/tonieboxes describes it."""
    box: dict[str, Any] = {
        "id": box_id,
        "name": name,
        "generation": "tb2g2",
        "features": ["tngSettings", "bedtime", "volumeLimit", "sleepTimerAlarm"],
        "timezone": "Europe/Berlin",
        "lastSeen": "2026-11-04T10:00:00Z",
        "firmware": {"version": "1.2.3"},
        "bleColorId": "red",
        "maxVolume": 10,
        "placement": {"tonie": {"id": placed}} if placed else None,
    }
    if mac is not None:
        box["macAddress"] = mac
    if online is not None:
        box["onlineState"] = online
    return box


def classic_box(
    box_id: str = CLASSIC_BOX_ID, name: str = CLASSIC_BOX_NAME, last_seen: str | None = ""
) -> dict[str, Any]:
    """Return a classic box; by default it was seen five minutes ago."""
    if last_seen == "":
        last_seen = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    box: dict[str, Any] = {
        "id": box_id,
        "name": name,
        "generation": "classic",
        "features": ["volumeLimit"],
        "firmware": {"version": "3.1.0"},
        "maxVolume": 8,
    }
    if last_seen is not None:
        box["lastSeen"] = last_seen
    return box


def content_tonie(
    tonie_id: str = TONIE_ID,
    name: str = TONIE_NAME,
    household_id: str = HOUSEHOLD_ID,
    chapters: list[dict[str, Any]] | None = None,
    seconds_present: float | None = 500,
) -> dict[str, Any]:
    """Return a bought figure as the library query lists it under its household.

    The chapters there carry names only. ``householdId`` is not part of that
    answer: the fake groups by it, and the older connection query (the
    fallback) carries it. Both language fields are present, as each of the two
    queries asks for one of them.
    """
    if chapters is None:
        chapters = [{"name": "Kapitel 1"}, {"name": "Kapitel 2"}]
    return {
        "id": tonie_id,
        "householdId": household_id,
        "title": name,
        "lock": False,
        "imageUrl": f"https://img.example.com/{tonie_id}.png",
        "coverUrl": None,
        "languageName": "Deutsch",
        "languageUnicode": "de-de",
        "salesId": "123",
        "series": {"name": TONIE_SERIES},
        "chapters": chapters,
        "secondsPresent": seconds_present,
    }


def connection_node(node: dict[str, Any]) -> dict[str, Any]:
    """Return a figure as the older connection query myContentTonies lists it: no chapters."""
    return {
        k: v for k, v in node.items() if k not in ("chapters", "secondsPresent", "languageUnicode")
    }


# What a refused GraphQL query answers: errors, no data
GRAPHQL_REFUSED: dict[str, Any] = {
    "errors": [{"message": 'Cannot query field "households" on type "Query"'}],
    "data": None,
}


def creative_tonie(tonie_id: str = CREATIVE_ID, name: str = CREATIVE_NAME) -> dict[str, Any]:
    """Return a figure of GET /households/{id}/creativetonies."""
    return {
        "id": tonie_id,
        "name": name,
        "imageUrl": f"https://img.example.com/{tonie_id}.png",
        "lock": False,
        "chapters": [
            {"id": "ch1", "title": "Song", "file": "f1", "seconds": 120.5, "transcoding": False}
        ],
        "secondsRemaining": 5000,
        "chaptersRemaining": 80,
    }


def tune(
    tune_id: str = "my-tune-1",
    title: str = "Bakabu",
    suitable: tuple[str, ...] = (CREATIVE_ID,),
    assigned: tuple[str, ...] = (),
    remaining: int = 2,
) -> dict[str, Any]:
    """Return a node of the GraphQL field tunesItems for a bought Tune."""
    return {
        "id": f"item-{tune_id}",
        "title": title,
        "thumbnail": "https://img.example.com/tune.png",
        "series": {"name": "Bakabu"},
        "contentInfo": {"seconds": 3138},
        "allCreativeTonies": True,
        "myTune": {
            "id": tune_id,
            "assignCountRemaining": remaining,
            "assignedTonies": [
                {"id": i, "tonieType": "creative", "householdId": HOUSEHOLD_ID} for i in assigned
            ],
            "suitableTonies": [
                {"id": i, "tonieType": "creative", "householdId": HOUSEHOLD_ID} for i in suitable
            ],
        },
    }


def disc(disc_id: str = DISC_ID, name: str = DISC_NAME) -> dict[str, Any]:
    """Return a node of the GraphQL field myDiscs."""
    return {
        "id": disc_id,
        "householdId": HOUSEHOLD_ID,
        "title": name,
        "coverImageUrl": f"https://img.example.com/{disc_id}.png",
        "discImageUrl": None,
        "lock": False,
        "language": "de",
        "salesId": "456",
    }


# What the box tells about the figure on it; these chapters carry no IDs
PLAYBACK_INFO_SERIES = "Box-Serie"
PLAYBACK_INFO_IMAGE = "https://img.example.com/box-t1.png"
PLAYBACK_INFO_CHAPTERS: list[dict[str, Any]] = [
    {"title": "Box-Kapitel 1", "seconds": 180, "tuneTitle": "Lied 1", "coverUrl": None},
    {"title": "Box-Kapitel 2", "seconds": 240, "tuneTitle": "Lied 2", "coverUrl": None},
    {"title": "Box-Kapitel 3", "seconds": 60, "tuneTitle": "Lied 3", "coverUrl": None},
]
CONTENT_VERSION = 1730000000


def playback_info(
    name: str = TONIE_NAME,
    series: str | None = PLAYBACK_INFO_SERIES,
    image_url: str | None = PLAYBACK_INFO_IMAGE,
    chapters: list[dict[str, Any]] | None = None,
    status: str | None = "available",
) -> dict[str, Any]:
    """Return GET /playback-info/{box}/{tonie}: the figure as the box sees it."""
    return {
        "title": name,
        "series": series,
        "tonieImageUrl": image_url,
        "status": status,
        "chapters": PLAYBACK_INFO_CHAPTERS if chapters is None else chapters,
    }


# ---------------------------------------------------------------- the cloud


@dataclass
class Account:
    """One account of the cloud with its tokens and what it owns."""

    name: str
    user_id: str
    email: str
    password: str = PASSWORD
    # Whether the login server grants offline tokens (scope offline_access)
    offline_tokens: bool = True
    # The stored refresh token is refused: the account needs a new login
    refresh_refused: bool = False
    # Every REST/GraphQL call answers this status
    rest_status: int | None = None
    # Every REST/GraphQL call fails with a connection error
    rest_unreachable: bool = False
    # The GraphQL field myDiscs answers with errors instead of data
    discs_error: bool = False
    # Every playback-info call answers this status instead of a figure
    playback_info_status: int | None = None
    # Every playback-info call waits for this event before it answers
    playback_info_gate: asyncio.Event | None = None
    # The app's library query (households with their contentTonies) is refused:
    # the client falls back to the older connection query, which has no chapters
    library_query_refused: bool = False
    # The app's detail query (one contentTonie of a household) is refused
    detail_query_refused: bool = False
    # Changing chapters (PATCH of a figure, POST of a chapter) answers this status and body
    chapters_error: tuple[int, dict[str, Any]] | None = None
    # The cloud answers an added chapter without keeping it
    chapters_dropped: bool = False
    # Changing chapters answers without a body
    chapters_no_body: bool = False
    # Reading the bedtime schedules answers this status
    schedules_status: int | None = None
    # Changing a box answers without a body
    box_patch_no_body: bool = False
    # The account's notifications and the broadcasts, as the cloud lists them
    notices: list[dict[str, Any]] = field(default_factory=list)
    system_notices: list[dict[str, Any]] = field(default_factory=list)
    # Reading the notifications answers this status
    notices_status: int | None = None
    # Locking a figure answers this status
    lock_status: int | None = None
    # The Tunes the account bought, as nodes of tunesItems; reading them answers this status
    tunes: list[dict[str, Any]] = field(default_factory=list)
    tunes_status: int | None = None
    # Taking a Tune off shows only after this many reads of the Tunes (None: never)
    tune_off_after_reads: int | None = 0
    tune_off_pending: list[str] = field(default_factory=list)
    page_size: int = 100
    households: list[dict[str, Any]] = field(default_factory=list)
    boxes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    creative_tonies: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    content_tonies: list[dict[str, Any]] = field(default_factory=list)
    discs: list[dict[str, Any]] = field(default_factory=list)
    # GET /households/{id}/memberships per household; reading them answers this status
    members: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    members_status: int | None = None
    # What GET /playback-info/{box}/{tonie} answers; a pair not listed is a 404
    playback_info: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    # What the detail query answers per figure; a figure not listed answers with its
    # node from content_tonies, None means the cloud does not find it
    content_tonie_details: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    # The bedtime schedules per box, as the cloud answers them
    schedules: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    tokens_issued: int = 0
    refresh_token: str = ""
    access_tokens: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.refresh_token = f"refresh-{self.name}-0"

    def issue(self) -> dict[str, Any]:
        """Rotate the tokens, as the login server does, and return the answer."""
        self.tokens_issued += 1
        self.refresh_token = f"refresh-{self.name}-{self.tokens_issued}"
        access = f"access-{self.name}-{self.tokens_issued}"
        self.access_tokens.add(access)
        return {
            "access_token": access,
            "expires_in": 300,
            "refresh_expires_in": 0 if self.offline_tokens else 1800,
            "refresh_token": self.refresh_token,
            "token_type": "Bearer",
            "scope": "openid offline_access" if self.offline_tokens else "openid",
        }

    def box(self, box_id: str) -> dict[str, Any]:
        """Return the raw box, to change it in a test."""
        return next(b for boxes in self.boxes.values() for b in boxes if b["id"] == box_id)

    def remove_box(self, box_id: str) -> None:
        """Take a box out of the account."""
        for boxes in self.boxes.values():
            boxes[:] = [b for b in boxes if b["id"] != box_id]


def _json(method: str, url: URL, status: int, body: Any) -> AiohttpClientMockResponse:
    return AiohttpClientMockResponse(
        method=method, url=url, status=status, json=body, headers=JSON_HEADERS
    )


class FakeCloud:
    """Answers the login server and the API from the accounts' dicts."""

    def __init__(self, mocker: AiohttpClientMocker) -> None:
        self.mocker = mocker
        self.accounts: dict[str, Account] = {}
        # Nothing answers at all: login server and API
        self.unreachable = False
        self.token_calls: list[dict[str, str]] = []
        self.graphql_calls: list[tuple[str, str | None]] = []
        self.playback_info_calls: list[tuple[str, str]] = []
        # The contentVersion each playback-info call carried
        self.playback_info_versions: list[int] = []
        # The (household, figure) pairs the detail query was asked for
        self.detail_calls: list[tuple[str | None, str | None]] = []
        # Chapter changes: (household, figure, payload) of every PATCH and every added chapter
        self.chapter_patches: list[tuple[str, str, Any]] = []
        self.chapter_adds: list[tuple[str, str, Any]] = []
        # Renamed creative figures: (figure, payload)
        self.renames: list[tuple[str, Any]] = []
        # What GET /version answers (None: an error), the box pictures by colour
        self.version: str | None = BACKEND_VERSION
        self.box_pictures: list[dict[str, Any]] = [
            {"bleColorId": "red", "thumbnail": "https://img.example.com/box-red.png"},
            {"bleColorId": 9, "thumbnail": "http://insecure.example.com/x.png"},
        ]
        self.version_calls = 0
        # Vouchers redeemed (their codes) and content tokens put on figures (figure, payload)
        self.vouchers: list[str] = []
        self.tokens: list[tuple[str, Any]] = []
        # Renamed households: (household, payload)
        self.household_patches: list[tuple[str, Any]] = []
        # Tunes laid on and taken off: (method, figure, tune or None)
        self.tune_changes: list[tuple[str, str, str | None]] = []
        # Locks of bought figures and discs: (kind, figure, payload)
        self.lock_patches: list[tuple[str, str, Any]] = []
        # Notifications marked as read: (method, path, payload)
        self.notice_changes: list[tuple[str, str, Any]] = []
        # Changes of a box's settings: (box, payload)
        self.box_patches: list[tuple[str, Any]] = []
        # Changes of bedtime schedules: (method, box, schedule or None, payload)
        self.schedule_changes: list[tuple[str, str, str | None, Any]] = []
        # Upload tickets handed out, and what reached the storage: per upload the form's
        # fields as (name, filename, content type, size) and whether a bearer token came along
        self.upload_tickets = 0
        self.s3_uploads: list[dict[str, Any]] = []
        # The storage refuses uploads with this status
        self.s3_status: int | None = None
        mocker.post(TOKEN_URL, side_effect=self._token)
        mocker.get(re.compile(rf"^{re.escape(API_BASE)}/"), side_effect=self._rest)
        mocker.post(f"{API_BASE}/graphql", side_effect=self._graphql)
        mocker.post(re.compile(rf"^{re.escape(API_BASE)}/"), side_effect=self._rest)
        mocker.patch(re.compile(rf"^{re.escape(API_BASE)}/"), side_effect=self._rest)
        mocker.delete(re.compile(rf"^{re.escape(API_BASE)}/"), side_effect=self._rest)
        mocker.put(re.compile(rf"^{re.escape(API_BASE)}/"), side_effect=self._rest)
        mocker.post(S3_URL, side_effect=self._s3)

    def add_account(self, name: str, **kwargs: Any) -> Account:
        """Add an account; tokens are named after it."""
        kwargs.setdefault("user_id", f"user-{name}")
        kwargs.setdefault("email", f"{name}@example.com")
        account = Account(name=name, **kwargs)
        self.accounts[name] = account
        return account

    @property
    def main(self) -> Account:
        """Return the account of the default config entry."""
        return self.accounts["main"]

    def account_by_access_token(self, token: str | None) -> Account | None:
        """Return the account an access token belongs to."""
        return next((a for a in self.accounts.values() if token in a.access_tokens), None)

    def expire_access_tokens(self) -> None:
        """Make the API reject every access token given out so far."""
        for account in self.accounts.values():
            account.access_tokens.clear()

    # -- the login server --

    async def _token(
        self, method: str, url: URL, form: dict[str, str]
    ) -> AiohttpClientMockResponse:
        self.token_calls.append(dict(form))
        if self.unreachable:
            raise aiohttp.ClientConnectionError("login server down")
        grant = form.get("grant_type")
        if grant == "password":
            account = next(
                (a for a in self.accounts.values() if a.email == form.get("username")), None
            )
            if account is None or account.password != form.get("password"):
                return _json(
                    method,
                    url,
                    401,
                    {"error": "invalid_grant", "error_description": "Invalid user credentials"},
                )
            if "offline_access" in form.get("scope", "") and not account.offline_tokens:
                return _json(method, url, 400, {"error": "invalid_scope"})
            return _json(method, url, 200, account.issue())
        if grant == "refresh_token":
            account = next(
                (a for a in self.accounts.values() if a.refresh_token == form.get("refresh_token")),
                None,
            )
            if account is None or account.refresh_refused:
                return _json(method, url, 400, {"error": "invalid_grant"})
            return _json(method, url, 200, account.issue())
        return _json(method, url, 400, {"error": "unsupported_grant_type"})

    # -- the API --

    def _authorize(self, method: str, url: URL) -> Account | AiohttpClientMockResponse:
        if self.unreachable:
            raise aiohttp.ClientConnectionError("api down")
        headers = self.mocker.mock_calls[-1][3] or {}
        token = str(headers.get("Authorization", "")).removeprefix("Bearer ")
        account = self.account_by_access_token(token)
        if account is None:
            return _json(method, url, 401, {"message": "Unauthorized"})
        if account.rest_unreachable:
            raise aiohttp.ClientConnectionError("api down")
        if account.rest_status is not None:
            return _json(method, url, account.rest_status, {"message": "error"})
        return account

    async def _rest(self, method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        if url.path == "/v2/version":
            # Answered without a sign-in, as plain text
            self.version_calls += 1
            if self.unreachable:
                raise aiohttp.ClientConnectionError("api down")
            if self.version is None:
                return _json(method, url, 500, {"message": "error"})
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                status=200,
                text=self.version,
                headers={"Content-Type": "text/plain"},
            )
        account = self._authorize(method, url)
        if isinstance(account, AiohttpClientMockResponse):
            return account
        path = url.path.removeprefix("/v2")
        if path == "/me":
            return _json(method, url, 200, {"uuid": account.user_id, "email": account.email})
        if path == "/households":
            return _json(method, url, 200, account.households)
        if match := re.fullmatch(r"/households/([^/]+)/memberships", path):
            if account.members_status is not None:
                return _json(method, url, account.members_status, {})
            return _json(method, url, 200, account.members.get(match[1], []))
        if (match := re.fullmatch(r"/households/([^/]+)", path)) and method.upper() == "PATCH":
            household = next((h for h in account.households if h["id"] == match[1]), None)
            if household is None:
                return _json(method, url, 404, {"message": "not found"})
            self.household_patches.append((match[1], data))
            household.update(data)
            return _json(method, url, 200, household)
        if match := re.fullmatch(r"/tunes-vouchers/(.+)", path):
            self.vouchers.append(match[1])
            if match[1] != "GOOD-CODE":
                return _json(method, url, 404, {"errors": [{"code": "voucher_not_found"}]})
            new = tune("my-tune-new", "New Tune", remaining=1)
            account.tunes.append(new)
            return _json(method, url, 200, {"tunes": [new["myTune"]]})
        if match := re.fullmatch(r"/households/([^/]+)/creativetonies/([^/]+)/redeem-token", path):
            self.tokens.append((match[2], data))
            if (data or {}).get("token") != "toniesong":
                return _json(method, url, 400, {"errors": [{"code": "invalid_token"}]})
            return _json(method, url, 200, {})
        if path == "/box-item-previews":
            return _json(method, url, 200, self.box_pictures)
        if match := re.fullmatch(r"/households/([^/]+)/(contenttonies|discs)/([^/]+)", path):
            if account.lock_status is not None:
                return _json(method, url, account.lock_status, {"message": "error"})
            self.lock_patches.append((match[2], match[3], data))
            return _json(method, url, 200, {"id": match[3], **(data or {})})
        if match := re.fullmatch(r"/households/([^/]+)/tonie/([^/]+)/tune(?:/([^/]+))?", path):
            return self._tune(account, method, url, *match.groups())
        if match := re.fullmatch(r"/(notifications|system-notifications)/([^/]+)", path):
            self.notice_changes.append((method.upper(), path, data))
            return AiohttpClientMockResponse(method=method, url=url, status=204)
        if path in ("/notifications", "/system-notifications"):
            if account.notices_status is not None:
                return _json(method, url, account.notices_status, {"message": "error"})
            items = account.notices if path == "/notifications" else account.system_notices
            return _json(method, url, 200, items)
        if match := re.fullmatch(r"/households/([^/]+)/tonieboxes/([^/]+)", path):
            box = next((b for b in account.boxes.get(match[1], []) if b["id"] == match[2]), None)
            if box is None:
                return _json(method, url, 404, {"message": "not found"})
            if method.upper() == "PATCH":
                self.box_patches.append((match[2], data))
                box.update(data)
                if account.box_patch_no_body:
                    return AiohttpClientMockResponse(method=method, url=url, status=204)
            return _json(method, url, 200, box)
        if match := re.fullmatch(
            r"/households/([^/]+)/tonieboxes/([^/]+)/bedtime-schedules(?:/([^/]+))?", path
        ):
            return self._schedules(account, method, url, data, *match.groups())
        if match := re.fullmatch(r"/households/([^/]+)/(tonieboxes|creativetonies)", path):
            household, kind = match.groups()
            items = account.boxes if kind == "tonieboxes" else account.creative_tonies
            return _json(method, url, 200, items.get(household, []))
        if path == "/file" and method.upper() == "POST":
            self.upload_tickets += 1
            file_id = f"file-{self.upload_tickets}"
            ticket = {"url": S3_URL, "fields": {"key": f"uploads/{file_id}", "policy": "signed"}}
            return _json(method, url, 200, {"fileId": file_id, "request": ticket})
        if match := re.fullmatch(r"/households/([^/]+)/creativetonies/([^/]+)(/chapters)?", path):
            return self._creative(account, method, url, data, *match.groups())
        if match := re.fullmatch(r"/playback-info/([^/]+)/([^/]+)", path):
            box_id, tonie_id = match.groups()
            self.playback_info_calls.append((box_id, tonie_id))
            # The cloud insists on the version of the content the box holds
            version = url.query.get("contentVersion")
            if version is None or not version.isdigit():
                return _json(method, url, 400, {"message": "contentVersion is required"})
            self.playback_info_versions.append(int(version))
            if account.playback_info_gate is not None:
                await account.playback_info_gate.wait()
            if account.playback_info_status is not None:
                return _json(method, url, account.playback_info_status, {"message": "error"})
            if (info := account.playback_info.get((box_id, tonie_id))) is None:
                return _json(method, url, 404, {"message": "not found"})
            return _json(method, url, 200, info)
        return _json(method, url, 404, {"message": "not found"})

    def _tune(
        self,
        account: Account,
        method: str,
        url: URL,
        household: str,
        tonie_id: str,
        tune_id: str | None,
    ) -> AiohttpClientMockResponse:
        """Lay a Tune on a figure (PUT …/tune/{id}) or take it off (DELETE …/tune)."""
        method = method.upper()
        self.tune_changes.append((method, tonie_id, tune_id))
        for node in account.tunes:
            mine = node["myTune"]
            assigned = mine["assignedTonies"]
            if method == "DELETE" and account.tune_off_after_reads != 0:
                account.tune_off_pending.append(tonie_id)
            elif method == "DELETE":
                mine["assignedTonies"] = [a for a in assigned if a["id"] != tonie_id]
            elif mine["id"] == tune_id:
                if mine["assignCountRemaining"] < 1:
                    return _json(method, url, 400, {"message": "no assignments left"})
                assigned.append({"id": tonie_id, "tonieType": "content", "householdId": household})
                mine["assignCountRemaining"] -= 1
        return AiohttpClientMockResponse(method=method, url=url, status=204)

    def _schedules(
        self,
        account: Account,
        method: str,
        url: URL,
        data: Any,
        household: str,
        box_id: str,
        schedule_id: str | None,
    ) -> AiohttpClientMockResponse:
        method = method.upper()
        if account.schedules_status is not None and method == "GET":
            return _json(method, url, account.schedules_status, {"message": "error"})
        schedules = account.schedules.setdefault(box_id, [])
        if method == "GET" and schedule_id is None:
            return _json(method, url, 200, schedules)
        if method == "POST" and schedule_id is None:
            self.schedule_changes.append((method, box_id, None, data))
            created = {"id": f"s{len(self.schedule_changes)}", **data}
            schedules.append(created)
            return _json(method, url, 201, created)
        found = next((s for s in schedules if s["id"] == schedule_id), None)
        if found is None:
            return _json(method, url, 404, {"message": "not found"})
        self.schedule_changes.append((method, box_id, schedule_id, data))
        if method == "PATCH":
            found.update(data)
            return _json(method, url, 200, found)
        if method == "DELETE":
            schedules.remove(found)
            return AiohttpClientMockResponse(method=method, url=url, status=204)
        return _json(method, url, 405, {"message": "method not allowed"})

    def _creative(
        self,
        account: Account,
        method: str,
        url: URL,
        data: Any,
        household: str,
        tonie_id: str,
        chapters_path: str | None,
    ) -> AiohttpClientMockResponse:
        """One creative figure: read, its chapters replaced (PATCH) or one appended (POST).

        A change marks the figure as converting, as the cloud does.
        """
        tonie = next(
            (t for t in account.creative_tonies.get(household, []) if t["id"] == tonie_id), None
        )
        if tonie is None:
            return _json(method, url, 404, {"message": "not found"})
        if method.upper() == "GET" and not chapters_path:
            return _json(method, url, 200, tonie)
        if account.chapters_error is not None:
            status, body = account.chapters_error
            return _json(method, url, status, body)
        if chapters_path and method.upper() == "POST":
            self.chapter_adds.append((household, tonie_id, data))
            if account.chapters_dropped:
                return _json(method, url, 200, tonie)
            tonie["chapters"].append(
                {
                    "id": f"ch-{data['file']}",
                    "title": data["title"],
                    "file": data["file"],
                    "seconds": 0,
                    "transcoding": True,
                }
            )
        elif not chapters_path and method.upper() == "PATCH" and "chapters" not in data:
            # A new name: the cloud does not convert the figure for it
            self.renames.append((tonie_id, data))
            tonie.update(data)
            return _json(method, url, 200, tonie)
        elif not chapters_path and method.upper() == "PATCH":
            self.chapter_patches.append((household, tonie_id, data))
            tonie["chapters"] = [dict(c) for c in data["chapters"]]
        else:
            return _json(method, url, 405, {"message": "method not allowed"})
        tonie["transcoding"] = True
        if account.chapters_no_body:
            return AiohttpClientMockResponse(method=method, url=url, status=204)
        return _json(method, url, 200, tonie)

    async def _s3(self, method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        """The storage: records the form and refuses nothing unless told."""
        headers = self.mocker.mock_calls[-1][3] or {}
        fields = []
        for options, part_headers, value in getattr(data, "_fields", []):
            size = len(value) if isinstance(value, bytes | bytearray) else len(str(value))
            fields.append(
                (
                    options.get("name"),
                    options.get("filename"),
                    part_headers.get("Content-Type"),
                    size,
                )
            )
        self.s3_uploads.append({"fields": fields, "bearer": "Authorization" in headers})
        if self.s3_status is not None:
            return AiohttpClientMockResponse(
                method=method, url=url, status=self.s3_status, text="<Error/>"
            )
        return AiohttpClientMockResponse(method=method, url=url, status=204)

    async def _graphql(
        self, method: str, url: URL, data: dict[str, Any]
    ) -> AiohttpClientMockResponse:
        account = self._authorize(method, url)
        if isinstance(account, AiohttpClientMockResponse):
            return account
        query: str = data["query"]
        variables: dict[str, Any] = data.get("variables") or {}
        if "contentTonies(id:" in query:
            # The app's detail query: one figure of one household
            household_id, tonie_id = variables.get("householdId"), variables.get("contentTonieId")
            self.detail_calls.append((household_id, tonie_id))
            if account.detail_query_refused:
                return _json(method, url, 200, GRAPHQL_REFUSED)
            if tonie_id in account.content_tonie_details:
                node = account.content_tonie_details[tonie_id]
            else:
                node = next(
                    (
                        t
                        for t in account.content_tonies
                        if t["id"] == tonie_id and t["householdId"] == household_id
                    ),
                    None,
                )
            household = {"id": household_id, "contentTonies": [node] if node else []}
            return _json(method, url, 200, {"data": {"households": [household]}})
        if "households {" in query:
            # The app's library query: every household with its figures and their chapter names
            self.graphql_calls.append(("households", None))
            if account.library_query_refused:
                return _json(method, url, 200, GRAPHQL_REFUSED)
            households = [
                {
                    "id": h["id"],
                    "contentTonies": [
                        t for t in account.content_tonies if t["householdId"] == h["id"]
                    ],
                }
                for h in account.households
            ]
            return _json(method, url, 200, {"data": {"households": households}})
        cursor: str | None = variables.get("cursor")
        if "myContentTonies" in query:
            fld = "myContentTonies"
            nodes = [connection_node(t) for t in account.content_tonies]
        elif "myDiscs" in query:
            fld, nodes = "myDiscs", account.discs
        elif "tunesItems" in query:
            if account.tunes_status is not None:
                return _json(method, url, account.tunes_status, {"message": "error"})
            if account.tune_off_pending and account.tune_off_after_reads is not None:
                if account.tune_off_after_reads <= 0:
                    for node in account.tunes:
                        mine = node["myTune"]
                        mine["assignedTonies"] = [
                            a
                            for a in mine["assignedTonies"]
                            if a["id"] not in account.tune_off_pending
                        ]
                    account.tune_off_pending.clear()
                else:
                    account.tune_off_after_reads -= 1
            fld, nodes = "tunesItems", account.tunes
        else:
            return _json(method, url, 400, {"errors": [{"message": "unknown field"}]})
        self.graphql_calls.append((fld, cursor))
        if fld == "myDiscs" and account.discs_error:
            return _json(
                method, url, 200, {"errors": [{"message": "discs unavailable"}], "data": None}
            )
        start = int(cursor) if cursor else 0
        page = nodes[start : start + account.page_size]
        end = start + len(page)
        has_next = end < len(nodes)
        connection = {
            "pageInfo": {"hasNextPage": has_next, "endCursor": str(end) if has_next else None},
            "edges": [{"node": node} for node in page],
        }
        return _json(method, url, 200, {"data": {fld: connection}})


# ---------------------------------------------------------------- the push channel


class FakePush(PushClient):
    """The push channel without a broker: messages are injected, commands recorded."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.commands: list[tuple[str, str, dict[str, Any]]] = []
        self.command_error: Exception | None = None
        self.runs = 0
        self._stop = asyncio.Event()
        self._error: Exception | None = None

    @property
    def macs(self) -> set[str]:
        """Return the boxes the channel was told to listen to."""
        return set(self._macs)

    async def async_run(self) -> None:
        """Wait until the test ends the loop, then return or raise as told."""
        self.runs += 1
        await self._stop.wait()
        if self._error is not None:
            raise self._error

    def end(self, error: Exception | None = None) -> None:
        """Let async_run return, or raise the error, as the real loop would."""
        self._error = error
        self._stop.set()

    def connect(self, connected: bool = True) -> None:
        """Tell the integration the channel came up or went down."""
        self._set_connected(connected)

    def send(self, topic: str, data: PushData, mac: str = MAC) -> None:
        """Deliver one parsed message of a box."""
        self._on_event(PushEvent(mac, topic, data))

    def battery(
        self, percent: int | None = 80, status: str | None = "charging", mac: str = MAC
    ) -> None:
        """Deliver metrics/battery."""
        self.send(TOPIC_BATTERY, parse_battery({"percent": percent, "status": status}), mac)

    def online(self, state: bool | None, mac: str = MAC) -> None:
        """Deliver online-state."""
        self.send(TOPIC_ONLINE, state, mac)

    def playback(
        self,
        tonie_id: str | None = TONIE_ID,
        chapter: int | None = 1,
        paused: bool | None = False,
        duration: float | None = 200.0,
        position: float | None = 50.0,
        ended: bool | None = False,
        downloading: bool | None = False,
        content_version: int | None = None,
        mac: str = MAC,
    ) -> None:
        """Deliver playback/state."""
        self.send(
            TOPIC_PLAYBACK,
            Playback(
                tonie_id=tonie_id,
                chapter=chapter,
                paused=paused,
                ended=ended,
                downloading=downloading,
                duration=duration,
                position=position,
                content_version=content_version,
            ),
            mac,
        )

    def removed(self, mac: str = MAC) -> None:
        """Deliver the empty playback/state the box sends when the figure is taken off."""
        self.send(TOPIC_PLAYBACK, Playback(tonie_id=None), mac)

    def volume(self, level: int | None, mac: str = MAC) -> None:
        """Deliver volume/state."""
        self.send(TOPIC_VOLUME, Volume(level=level), mac)

    def sleep_timer(
        self,
        state: str | None = "on",
        until: datetime | None = None,
        alarm: bool = False,
        mac: str = MAC,
    ) -> None:
        """Deliver app-reply/bedtime-state."""
        self.send(
            TOPIC_SLEEP_TIMER, SleepTimer(state=state, duration=600, until=until, alarm=alarm), mac
        )

    async def async_command(self, mac: str, command: str, payload: dict[str, Any]) -> None:
        """Record the command instead of publishing it."""
        if not self._connected:
            raise CloudConnectionError("The push channel is not connected")
        if self.command_error is not None:
            raise self.command_error
        self.commands.append((mac, command, payload))


class PushChannels:
    """The push channels created by the integration, one per entry."""

    def __init__(self) -> None:
        self.instances: list[FakePush] = []

    def create(self, *args: Any, **kwargs: Any) -> FakePush:
        """Stand in for the PushClient constructor."""
        push = FakePush(*args, **kwargs)
        self.instances.append(push)
        return push

    @property
    def last(self) -> FakePush:
        """Return the channel created last."""
        return self.instances[-1]


# ---------------------------------------------------------------- the Media Fetcher app

FETCHER_SLUG = "local_media_fetcher"
FETCHER_HOST = "local-media-fetcher"
FETCHER_PORT = 8099
FETCHER_URL = f"http://{FETCHER_HOST}:{FETCHER_PORT}/api/v1"
VIDEO_ID = "jNQXAC9IVRw"
VIDEO_URL = f"https://youtu.be/{VIDEO_ID}"


class FakeFetcher:
    """The Media Fetcher app: answers its API from canned data and keeps what it was asked."""

    def __init__(self, mocker: AiohttpClientMocker) -> None:
        self.mocker = mocker
        # The Supervisor lists the app, and it is started
        self.installed = True
        self.started = True
        # Every request fails with a connection error
        self.unreachable = False
        self.info: dict[str, Any] = {
            "id": VIDEO_ID,
            "title": "Me at the zoo",
            "duration": 19,
            "uploader": "jawed",
            "extractor": "youtube",
            "webpage_url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
            "thumbnail": None,
            "is_live": False,
        }
        # (status, code, message) answered instead of the info or the job
        self.info_error: tuple[int, str, str] | None = None
        self.start_error: tuple[int, str, str] | None = None
        # What a job answers poll by poll; the last answer stays
        self.states: list[dict[str, Any]] = [
            {"state": "downloading", "done_bytes": 10, "total_bytes": 20},
            {"state": "converting", "done_bytes": 20, "total_bytes": 20},
            {"state": "done", "done_bytes": 20, "total_bytes": 20, "size": 3},
        ]
        # The job stays "downloading" until it is deleted
        self.hold = False
        self.file = b"aac"
        self.content_type = "audio/mp4"
        self.calls: list[tuple[str, str, Any]] = []
        self.jobs: dict[str, dict[str, Any]] = {}
        pattern = re.compile(rf"^{re.escape(FETCHER_URL)}/")
        mocker.get(pattern, side_effect=self._handle)
        mocker.post(pattern, side_effect=self._handle)
        mocker.delete(pattern, side_effect=self._handle)

    def addons(self) -> list[Any]:
        """What the Supervisor lists as installed apps."""
        others = [SimpleNamespace(slug="core_mosquitto", state=AddonState.STARTED)]
        if not self.installed:
            return others
        state = AddonState.STARTED if self.started else AddonState.STOPPED
        return [*others, SimpleNamespace(slug=FETCHER_SLUG, state=state)]

    async def _handle(self, method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        if self.unreachable:
            raise aiohttp.ClientConnectionError("the app is down")
        path = url.path.removeprefix("/api/v1")
        self.calls.append((method.upper(), path, data))
        if method.upper() == "POST" and path == "/info":
            if self.info_error is not None:
                return self._error(method, url, *self.info_error)
            return _json(method, url, 200, self.info)
        if method.upper() == "POST" and path == "/jobs":
            if self.start_error is not None:
                return self._error(method, url, *self.start_error)
            job_id = f"job-{len(self.jobs) + 1}"
            self.jobs[job_id] = {"polls": 0, "deleted": False, "url": data["url"]}
            return _json(method, url, 201, {"id": job_id, "state": "queued"})
        parts = path.split("/")
        job = self.jobs.get(parts[2]) if len(parts) >= 3 and parts[1] == "jobs" else None
        if job is None:
            return self._error(method, url, 404, "not_found", "No such job")
        if method.upper() == "DELETE":
            job["deleted"] = True
            return AiohttpClientMockResponse(method=method, url=url, status=204)
        if len(parts) == 4 and parts[3] == "file":
            if self._state(job)["state"] != "done":
                return self._error(method, url, 409, "not_ready", "The job is not done")
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                status=200,
                response=self.file,
                headers={"Content-Type": self.content_type},
            )
        job["polls"] += 1
        return _json(method, url, 200, {"id": parts[2], "url": job["url"], **self._state(job)})

    def _state(self, job: dict[str, Any]) -> dict[str, Any]:
        if job["deleted"]:
            return {"state": "cancelled"}
        if self.hold:
            return {"state": "downloading", "done_bytes": 5, "total_bytes": None}
        return self.states[min(max(job["polls"], 1), len(self.states)) - 1]

    @staticmethod
    def _error(
        method: str, url: URL, status: int, code: str, message: str
    ) -> AiohttpClientMockResponse:
        return _json(method, url, status, {"error": {"code": code, "message": message}})


# ---------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def integration_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None]:
    """Let the integration's logger pass everything, as caplog expects, and reset it after.

    The level and the handler live on a process-wide logger; a test must not
    leave them to the next one. Tests of the level itself set it explicitly.
    """
    monkeypatch.setattr(log_module, "DEFAULT_LEVEL", "debug")
    # The files of the log go to the test's own folder, not the shared test config
    monkeypatch.setattr(log_module, "log_dir", lambda hass: tmp_path / "log")
    yield
    logger = logging.getLogger(log_module.LOGGER_NAME)
    logger.setLevel(logging.NOTSET)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


@pytest.fixture
def cloud(aioclient_mock: AiohttpClientMocker) -> FakeCloud:
    """The cloud with one account: a household with two boxes and three figures."""
    fake = FakeCloud(aioclient_mock)
    fake.add_account(
        "main",
        user_id=USER_ID,
        email=EMAIL,
        households=[{"id": HOUSEHOLD_ID, "name": HOUSEHOLD_NAME}],
        boxes={HOUSEHOLD_ID: [tb2_box(), classic_box()]},
        creative_tonies={HOUSEHOLD_ID: [creative_tonie()]},
        content_tonies=[content_tonie()],
        discs=[disc()],
    )
    return fake


@pytest.fixture
def fetcher_app(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> Generator[FakeFetcher]:
    """The Media Fetcher app, listed by the Supervisor and answering its API."""
    fake = FakeFetcher(aioclient_mock)
    hass.config.components.add("hassio")
    supervisor = MagicMock()
    supervisor.addons.list = AsyncMock(side_effect=lambda: fake.addons())
    with patch("homeassistant.components.hassio.get_supervisor_client", return_value=supervisor):
        yield fake


@pytest.fixture
def push() -> Generator[PushChannels]:
    """Replace the push channel by the fake."""
    channels = PushChannels()
    with patch("custom_components.storybox_plus.PushClient", side_effect=channels.create):
        yield channels


def entry_for(account: Account) -> MockConfigEntry:
    """Return a config entry as the config flow would have created it."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=HOUSEHOLD_NAME,
        unique_id=account.user_id,
        data={CONF_REFRESH_TOKEN: account.refresh_token, CONF_USER_ID: account.user_id},
    )


def counting_off(hass_storage: dict[str, Any], entry: MockConfigEntry) -> None:
    """Switch counting the listening time off, as the settings tab would, before the setup."""
    key = f"{DOMAIN}.{entry.entry_id}.settings"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {"analytics": False}}


@pytest.fixture
def config_entry(cloud: FakeCloud) -> MockConfigEntry:
    """The entry of the main account, not yet set up."""
    return entry_for(cloud.main)


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the integration with the simulated cloud."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def entity_id(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    """Return the entity ID of one of our entities.

    The unique ID is given without the entry in front (box-1_battery); the
    one entry that has the entity is looked up.
    """
    registry = er.async_get(hass)
    found = [
        e
        for entry in hass.config_entries.async_entries(DOMAIN)
        if (e := registry.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{unique_id}"))
    ]
    assert len(found) == 1, f"no single {domain} entity with unique_id {unique_id}: {found}"
    return found[0]


def device(hass: HomeAssistant, entry: MockConfigEntry, box_id: str) -> dr.DeviceEntry | None:
    """Return the device of a box, if the entry has one."""
    return dr.async_get(hass).async_get_device_by_identifier(
        box_identifier(entry, box_id), entry.entry_id
    )
