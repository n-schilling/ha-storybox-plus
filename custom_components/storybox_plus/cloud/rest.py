"""The REST and GraphQL API of the cloud.

Endpoints and payloads were learned from the official app and from the
community project HA-Toniebox (MIT); the code is our own.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .auth import Auth
from .errors import CloudAuthError, CloudConnectionError, CloudResponseError
from .models import (
    BedtimeSchedule,
    Box,
    Chapter,
    CloudNotice,
    Household,
    Library,
    Tonie,
    TonieDetails,
    TonieKind,
    Tune,
    parse_bedtime_schedule,
    parse_box,
    parse_content_tonie,
    parse_creative_tonie,
    parse_disc,
    parse_household,
    parse_notice,
    parse_playback_info,
    parse_tune,
)

_LOGGER = logging.getLogger(__name__)

# api.tonie.cloud is a CDN in front of this host and lacks some of the endpoints
API_BASE = "https://api.prod.tcs.toys/v2"
TIMEOUT = aiohttp.ClientTimeout(total=30)
# An audio file of up to 90 minutes goes to the storage in one request
UPLOAD_TIMEOUT = aiohttp.ClientTimeout(total=600)
PAGE_SIZE = 100
# The cloud cuts longer chapter titles off with an error
CHAPTER_TITLE_MAX = 128

# The library of bought figures, with the chapter names the app shows
_CONTENT_TONIE_FIELDS = "id title lock imageUrl coverUrl languageUnicode series { name } chapters { name } secondsPresent"
# The older connection query, without chapters; used when the library query is refused
_CONTENT_TONIE_NODE_FIELDS = (
    "id householdId title imageUrl coverUrl lock languageName salesId series { name }"
)
# The Tunes the account bought, as the web app's audio library asks for them
_TUNE_FIELDS = (
    "id title thumbnail series { name } contentInfo { seconds } allCreativeTonies "
    "myTune { id assignCountRemaining assignedTonies { id tonieType householdId } "
    "suitableTonies { id tonieType householdId } }"
)
_DISC_FIELDS = "id householdId title coverImageUrl discImageUrl lock language salesId"


def _color_key(value: Any) -> str | None:
    """A box colour as the models keep it: the number as text."""
    if isinstance(value, bool) or not isinstance(value, int | str):
        return None
    return str(value) or None


def _shape(node: dict[str, Any]) -> dict[str, Any]:
    """Describe a node for the debug log: types and sizes, no titles or IDs."""
    shape: dict[str, Any] = {}
    for key, value in node.items():
        if value is None or isinstance(value, bool | int | float):
            shape[key] = value
        elif isinstance(value, list):
            shape[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            shape[key] = f"dict{sorted(value)}"
        elif key in ("lock", "languageName", "language"):
            shape[key] = value
        else:
            shape[key] = f"{type(value).__name__}[{len(str(value))}]"
    return shape


async def _error_detail(resp: aiohttp.ClientResponse) -> str:
    """Name what the cloud objected to, from the codes of its error body.

    Only the machine-readable codes are taken, never a free text: the message
    ends up in the log and in the page.
    """
    try:
        body = await resp.json(content_type=None)
    except ValueError, aiohttp.ClientError:
        return ""
    if not isinstance(body, dict):
        return ""
    if isinstance(body.get("retryInSeconds"), int):
        return f" (retry in {body['retryInSeconds']} s)"
    errors = body.get("errors")
    if isinstance(errors, list) and errors and isinstance(errors[0], dict):
        codes = [
            str(errors[0][key])
            for key in ("code", "errorCode")
            if isinstance(errors[0].get(key), str)
        ]
        if codes:
            return f" ({'/'.join(codes)})"
    return ""


class CloudClient:
    """Reads and writes the account's households, boxes and figures."""

    def __init__(
        self, session: aiohttp.ClientSession, auth: Auth, base_url: str = API_BASE
    ) -> None:
        """Use Home Assistant's shared session and the account's tokens."""
        self._session = session
        self._auth = auth
        self._base = base_url.rstrip("/")

    # ------------------------------------------------------------ requests

    async def _request(
        self, method: str, path: str, json: Any = None, *, retry: bool = True
    ) -> Any:
        """Send one request; a rejected token is refreshed once and the request repeated."""
        token = await self._auth.async_access_token()
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=json,
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status == 401 and retry:
                    await self._auth.async_refresh()
                    return await self._request(method, path, json, retry=False)
                if resp.status == 401:
                    raise CloudAuthError("The cloud rejected the token")
                if resp.status >= 400:
                    detail = await _error_detail(resp)
                    raise CloudResponseError(
                        f"{method} {path} answered {resp.status}{detail}", resp.status
                    )
                if resp.status == 204 or resp.content_length == 0:
                    return None
                try:
                    return await resp.json(content_type=None)
                except ValueError as err:
                    raise CloudResponseError(
                        f"{method} {path} answered no JSON", resp.status
                    ) from err
        except TimeoutError as err:
            raise CloudConnectionError(f"Timeout for {method} {path}") from err
        except aiohttp.ClientError as err:
            raise CloudConnectionError(
                f"Cannot reach the cloud for {method} {path}: {type(err).__name__}"
            ) from err

    async def _get_list(self, path: str, *keys: str) -> list[dict[str, Any]]:
        """GET a list; the API wraps some lists in an object."""
        data = await self._request("GET", path)
        if isinstance(data, dict):
            for key in keys:
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            raise CloudResponseError(f"GET {path} answered no list", 200)
        return [item for item in data if isinstance(item, dict)]

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run one GraphQL query and return its data; errors without data raise."""
        response = await self._request(
            "POST", "/graphql", {"query": query, "variables": variables or {}}
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, dict):
            errors = response.get("errors") if isinstance(response, dict) else None
            _LOGGER.debug("GraphQL without data: %s", errors)
            raise CloudResponseError("GraphQL answered no data", 200)
        return data

    async def _graphql_nodes(
        self, field: str, selection: str, arguments: str = ""
    ) -> list[dict[str, Any]]:
        """Read every node of a paginated GraphQL connection; arguments filter it."""
        nodes: list[dict[str, Any]] = []
        cursor: str | None = None
        extra = f"{arguments}, " if arguments else ""
        query = (
            f"query($cursor: String) {{ {field}({extra}first: {PAGE_SIZE}, after: $cursor) "
            f"{{ pageInfo {{ hasNextPage endCursor }} edges {{ node {{ {selection} }} }} }} }}"
        )
        while True:
            response = await self._request(
                "POST", "/graphql", {"query": query, "variables": {"cursor": cursor}}
            )
            data = response.get("data") if isinstance(response, dict) else None
            connection = data.get(field) if isinstance(data, dict) else None
            if not isinstance(connection, dict):
                errors = response.get("errors") if isinstance(response, dict) else None
                _LOGGER.debug("GraphQL %s without data: %s", field, errors)
                raise CloudResponseError(f"GraphQL {field} answered no data", 200)
            for edge in connection.get("edges") or []:
                if isinstance(edge, dict) and isinstance(edge.get("node"), dict):
                    nodes.append(edge["node"])
            if cursor is None and nodes and _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("GraphQL %s: shape of the first node: %s", field, _shape(nodes[0]))
            page = connection.get("pageInfo") or {}
            cursor = page.get("endCursor") if isinstance(page, dict) else None
            if not (isinstance(page, dict) and page.get("hasNextPage") and cursor):
                return nodes

    # ------------------------------------------------------------ reading

    async def async_user_id(self) -> str:
        """Return the account's UUID; the push channel logs in with it."""
        me = await self._request("GET", "/me")
        user_id = me.get("uuid") or me.get("id") if isinstance(me, dict) else None
        if not isinstance(user_id, str) or not user_id:
            raise CloudResponseError("GET /me answered without a user ID", 200)
        return user_id

    async def async_households(self) -> list[Household]:
        """Return the households the account belongs to."""
        items = await self._get_list("/households", "households", "results")
        return [h for item in items if (h := parse_household(item))]

    async def async_rename_household(self, household_id: str, name: str) -> None:
        """Give a household a new name."""
        await self._request("PATCH", f"/households/{household_id}", {"name": name})

    async def async_boxes(self, household_id: str) -> list[Box]:
        """Return the boxes of a household."""
        items = await self._get_list(f"/households/{household_id}/tonieboxes", "results")
        return [b for item in items if (b := parse_box(item, household_id))]

    async def async_tunes(self) -> list[Tune]:
        """Return the Tunes the account bought, with the figures they lie on and fit."""
        nodes = await self._graphql_nodes("tunesItems", _TUNE_FIELDS, 'myTuneStatus: "owned"')
        return [t for node in nodes if (t := parse_tune(node))]

    async def async_assign_tune(self, tonie: Tonie, tune_id: str) -> None:
        """Lay a bought Tune on a figure; a creative figure keeps its chapters for later."""
        await self._request(
            "PUT", f"/households/{tonie.household_id}/tonie/{tonie.id}/tune/{tune_id}", {}
        )

    async def async_redeem_voucher(self, code: str) -> int:
        """Redeem a Tunes voucher; return how many Tunes it brought."""
        data = await self._request("POST", f"/tunes-vouchers/{quote(code, safe='')}", {})
        tunes = data.get("tunes") if isinstance(data, dict) else None
        return len(tunes) if isinstance(tunes, list) else 0

    async def async_redeem_token(self, tonie: Tonie, token: str) -> None:
        """Put ready-made content (a content token) on a creative figure; the cloud converts it."""
        await self._request(
            "POST",
            f"/households/{tonie.household_id}/creativetonies/{tonie.id}/redeem-token",
            {"token": token},
        )

    async def async_remove_tune(self, tonie: Tonie) -> None:
        """Take the Tune off a figure; it plays what it had before again."""
        await self._request("DELETE", f"/households/{tonie.household_id}/tonie/{tonie.id}/tune")

    async def async_mark_notice_read(self, notice: CloudNotice) -> None:
        """Mark a notification as read; a broadcast, which has no read state, is dismissed."""
        if notice.kind == "system":
            await self._request("DELETE", f"/system-notifications/{notice.cloud_id}")
        else:
            await self._request("PATCH", f"/notifications/{notice.cloud_id}", {"read": True})

    async def async_lock(self, tonie: Tonie, locked: bool) -> None:
        """Lock a bought figure or a disc to the household, or unlock it.

        A locked one cannot be claimed into another household.
        """
        kind = "discs" if tonie.kind is TonieKind.DISC else "contenttonies"
        await self._request(
            "PATCH", f"/households/{tonie.household_id}/{kind}/{tonie.id}", {"lock": locked}
        )

    async def async_box_pictures(self) -> dict[str, str]:
        """Return the pictures of the boxes by colour, as the app shows them."""
        items = await self._get_list("/box-item-previews", "results")
        return {
            color: thumbnail
            for item in items
            if (color := _color_key(item.get("bleColorId"))) is not None
            and isinstance(thumbnail := item.get("thumbnail"), str)
            and thumbnail.startswith("https://")
        }

    async def async_backend_version(self) -> str:
        """Return the version of the cloud's backend; it answers without a sign-in."""
        try:
            async with self._session.get(f"{self._base}/version", timeout=TIMEOUT) as resp:
                if resp.status >= 400:
                    raise CloudResponseError(f"GET /version answered {resp.status}", resp.status)
                text = (await resp.text()).strip().strip('"')
        except TimeoutError as err:
            raise CloudConnectionError("Timeout for GET /version") from err
        except aiohttp.ClientError as err:
            raise CloudConnectionError(
                f"Cannot reach the cloud for GET /version: {type(err).__name__}"
            ) from err
        if not text or len(text) > 100:
            raise CloudResponseError("GET /version answered no version", 200)
        return text

    async def async_notices(self) -> list[CloudNotice]:
        """Return the account's notifications and the cloud's broadcasts to all users."""
        own = await self._get_list("/notifications", "results", "notifications")
        system = await self._get_list("/system-notifications", "results", "notifications")
        if own:
            _LOGGER.debug("Notification: shape of the answer: %s", _shape(own[0]))
        return [n for item in own if (n := parse_notice(item))] + [
            n for item in system if (n := parse_notice(item, system=True))
        ]

    def _schedules_path(self, box: Box) -> str:
        return f"/households/{box.household_id}/tonieboxes/{box.id}/bedtime-schedules"

    async def async_bedtime_schedules(self, box: Box) -> list[BedtimeSchedule]:
        """Return the bedtime schedules of a Toniebox 2 that rings alarms."""
        items = await self._get_list(self._schedules_path(box), "results", "bedtimeSchedules")
        if items:
            _LOGGER.debug("Bedtime schedule: shape of the answer: %s", _shape(items[0]))
        return [s for item in items if (s := parse_bedtime_schedule(item))]

    async def async_save_bedtime_schedule(
        self, box: Box, schedule_id: str | None, fields: dict[str, Any]
    ) -> None:
        """Create a bedtime schedule, or change the given fields of an existing one.

        The fields carry the cloud's names (sleepTime, wakeupTime, days,
        enabled, alarmEnabled, alarmTone, alarmVolume, alarmMorningLight, name).
        """
        if schedule_id is None:
            await self._request("POST", self._schedules_path(box), fields)
        else:
            await self._request("PATCH", f"{self._schedules_path(box)}/{schedule_id}", fields)

    async def async_update_box(self, box: Box, fields: dict[str, Any]) -> Box | None:
        """Change settings of a box (the API's names) and return the box as the cloud answers."""
        data = await self._request(
            "PATCH", f"/households/{box.household_id}/tonieboxes/{box.id}", fields
        )
        return parse_box(data, box.household_id) if isinstance(data, dict) else None

    async def async_box(self, box: Box) -> Box | None:
        """Read one box again."""
        data = await self._request("GET", f"/households/{box.household_id}/tonieboxes/{box.id}")
        return parse_box(data, box.household_id) if isinstance(data, dict) else None

    async def async_delete_bedtime_schedule(self, box: Box, schedule_id: str) -> None:
        """Delete a bedtime schedule."""
        await self._request("DELETE", f"{self._schedules_path(box)}/{schedule_id}")

    async def async_creative_tonies(self, household_id: str) -> list[Tonie]:
        """Return the creative figures of a household, with their chapters."""
        items = await self._get_list(
            f"/households/{household_id}/creativetonies", "creativetonies", "results"
        )
        return [t for item in items if (t := parse_creative_tonie(item, household_id))]

    async def async_creative_tonie(self, household_id: str, tonie_id: str) -> Tonie | None:
        """Return one creative figure with its chapters; None when the cloud knows none."""
        try:
            data = await self._request(
                "GET", f"/households/{household_id}/creativetonies/{tonie_id}"
            )
        except CloudResponseError as err:
            if err.status == 404:
                return None
            raise
        return parse_creative_tonie(data, household_id) if isinstance(data, dict) else None

    async def async_content_tonies(self) -> list[Tonie]:
        """Return the bought figures of all households, with their chapter names.

        The app reads them per household; that query carries the chapters.
        Should the cloud refuse it, the older connection query serves the
        figures without chapters.
        """
        try:
            data = await self._graphql(
                f"query {{ households {{ id contentTonies {{ {_CONTENT_TONIE_FIELDS} }} }} }}"
            )
            households = data.get("households")
            if not isinstance(households, list):
                raise CloudResponseError("GraphQL households answered no list", 200)
        except CloudResponseError as err:
            _LOGGER.debug("Library with chapters not read (%s), asking without", err)
            nodes = await self._graphql_nodes("myContentTonies", _CONTENT_TONIE_NODE_FIELDS)
            return [t for node in nodes if (t := parse_content_tonie(node))]
        tonies: list[Tonie] = []
        for household in households:
            if not isinstance(household, dict) or not isinstance(household.get("id"), str):
                continue
            for node in household.get("contentTonies") or []:
                if isinstance(node, dict) and (t := parse_content_tonie(node, household["id"])):
                    tonies.append(t)
        return tonies

    async def async_content_tonie(self, household_id: str, tonie_id: str) -> Tonie | None:
        """Return one bought figure with its chapter names, as the app's detail page reads it."""
        data = await self._graphql(
            "query($householdId: String, $contentTonieId: String) { households(id: $householdId) "
            f"{{ id contentTonies(id: $contentTonieId) {{ {_CONTENT_TONIE_FIELDS} }} }} }}",
            {"householdId": household_id, "contentTonieId": tonie_id},
        )
        for household in data.get("households") or []:
            if not isinstance(household, dict):
                continue
            for node in household.get("contentTonies") or []:
                if isinstance(node, dict) and (t := parse_content_tonie(node, household_id)):
                    return t
        return None

    async def async_discs(self) -> list[Tonie]:
        """Return the discs of all households."""
        nodes = await self._graphql_nodes("myDiscs", _DISC_FIELDS)
        return [t for node in nodes if (t := parse_disc(node))]

    async def async_playback_info(
        self, box_id: str, tonie_id: str, content_version: int = 0
    ) -> TonieDetails | None:
        """Return the chapters of the figure that stands on a box.

        The cloud tells the chapters of a bought figure only this way, for the
        figure a box has in front of it, and wants the version of the content
        the box holds (from the push channel; 0 while unknown). None when the
        cloud knows nothing.
        """
        try:
            data = await self._request(
                "GET", f"/playback-info/{box_id}/{tonie_id}?contentVersion={int(content_version)}"
            )
        except CloudResponseError as err:
            if err.status in (400, 404):
                _LOGGER.debug("Playback info: the cloud answered %s", err.status)
                return None
            raise
        if not isinstance(data, dict):
            _LOGGER.debug("Playback info: no object in the answer")
            return None
        _LOGGER.debug("Playback info: shape of the answer: %s", _shape(data))
        return parse_playback_info(data)

    async def async_library(self) -> Library:
        """Return households, boxes and figures in one go."""
        households = await self.async_households()
        boxes: list[Box] = []
        tonies: list[Tonie] = []
        for household in households:
            boxes.extend(await self.async_boxes(household.id))
            tonies.extend(await self.async_creative_tonies(household.id))
        tonies.extend(await self.async_content_tonies())
        try:
            tonies.extend(await self.async_discs())
        except CloudResponseError as err:
            # Accounts without discs have answered with an error here
            _LOGGER.debug("Discs not read: %s", err)
        return Library(households=tuple(households), boxes=tuple(boxes), tonies=tuple(tonies))

    # ------------------------------------------------------------ writing

    async def async_set_chapters(
        self, household_id: str, tonie_id: str, chapters: list[Chapter]
    ) -> Tonie | None:
        """Replace the chapter list of a creative figure (order, deletions)."""
        payload = {
            "chapters": [
                {
                    "id": c.id,
                    "title": c.title,
                    "file": c.file or c.id,
                    "seconds": c.seconds or 0,
                    "transcoding": c.transcoding,
                }
                for c in chapters
            ]
        }
        data = await self._request(
            "PATCH", f"/households/{household_id}/creativetonies/{tonie_id}", payload
        )
        return parse_creative_tonie(data, household_id) if isinstance(data, dict) else None

    async def async_update_creative(
        self, household_id: str, tonie_id: str, fields: dict[str, Any]
    ) -> Tonie | None:
        """Change name or live mode of a creative figure; neither makes the cloud convert it."""
        data = await self._request(
            "PATCH", f"/households/{household_id}/creativetonies/{tonie_id}", fields
        )
        return parse_creative_tonie(data, household_id) if isinstance(data, dict) else None

    async def async_upload_file(self, data: bytes, filename: str, content_type: str) -> str:
        """Put an audio file into the cloud's storage and return its file ID.

        The API hands out a ticket (POST /file): a file ID and a pre-signed
        form for the storage. The audio goes there, with the ticket's fields
        first and without the bearer token, which the storage would refuse.
        The ID then names the file in a chapter.
        """
        ticket = await self._request("POST", "/file", {})
        request = ticket.get("request") if isinstance(ticket, dict) else None
        file_id = ticket.get("fileId") if isinstance(ticket, dict) else None
        url = request.get("url") if isinstance(request, dict) else None
        if not isinstance(file_id, str) or not file_id or not isinstance(url, str) or not url:
            raise CloudResponseError("POST /file answered without an upload ticket", 200)
        form = aiohttp.FormData()
        fields = request.get("fields") if isinstance(request, dict) else None
        for key, value in (fields or {}).items():
            form.add_field(str(key), str(value))
        form.add_field("file", data, filename=filename, content_type=content_type)
        try:
            async with self._session.post(url, data=form, timeout=UPLOAD_TIMEOUT) as resp:
                if resp.status >= 300:
                    raise CloudResponseError(
                        f"The storage refused the file with {resp.status}", resp.status
                    )
        except TimeoutError as err:
            raise CloudConnectionError("Timeout while uploading the file") from err
        except aiohttp.ClientError as err:
            raise CloudConnectionError(
                f"Cannot reach the storage for the upload: {type(err).__name__}"
            ) from err
        return file_id

    async def async_add_chapter(
        self, household_id: str, tonie_id: str, title: str, file_id: str
    ) -> Tonie | None:
        """Append an uploaded file as a chapter of a creative figure."""
        data = await self._request(
            "POST",
            f"/households/{household_id}/creativetonies/{tonie_id}/chapters",
            {"title": title[:CHAPTER_TITLE_MAX], "file": file_id, "type": "file"},
        )
        return parse_creative_tonie(data, household_id) if isinstance(data, dict) else None
