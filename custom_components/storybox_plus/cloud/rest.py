"""The REST and GraphQL API of the cloud.

Endpoints and payloads were learned from the official app and from the
community project HA-Toniebox (MIT); the code is our own.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .auth import Auth
from .errors import CloudAuthError, CloudConnectionError, CloudResponseError
from .models import (
    Box,
    Chapter,
    Household,
    Library,
    Tonie,
    parse_box,
    parse_content_tonie,
    parse_creative_tonie,
    parse_disc,
    parse_household,
)

_LOGGER = logging.getLogger(__name__)

# api.tonie.cloud is a CDN in front of this host and lacks some of the endpoints
API_BASE = "https://api.prod.tcs.toys/v2"
TIMEOUT = aiohttp.ClientTimeout(total=30)
PAGE_SIZE = 100

_CONTENT_TONIE_FIELDS = (
    "id householdId title imageUrl coverUrl lock languageName salesId "
    "series { name } chapters { id title seconds transcoding }"
)
_DISC_FIELDS = "id householdId title coverImageUrl discImageUrl lock language salesId"


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
                    raise CloudResponseError(f"{method} {path} answered {resp.status}", resp.status)
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

    async def _graphql_nodes(self, field: str, selection: str) -> list[dict[str, Any]]:
        """Read every node of a paginated GraphQL connection."""
        nodes: list[dict[str, Any]] = []
        cursor: str | None = None
        query = (
            f"query($cursor: String) {{ {field}(first: {PAGE_SIZE}, after: $cursor) "
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

    async def async_boxes(self, household_id: str) -> list[Box]:
        """Return the boxes of a household."""
        items = await self._get_list(f"/households/{household_id}/tonieboxes", "results")
        return [b for item in items if (b := parse_box(item, household_id))]

    async def async_creative_tonies(self, household_id: str) -> list[Tonie]:
        """Return the creative figures of a household, with their chapters."""
        items = await self._get_list(
            f"/households/{household_id}/creativetonies", "creativetonies", "results"
        )
        return [t for item in items if (t := parse_creative_tonie(item, household_id))]

    async def async_content_tonies(self) -> list[Tonie]:
        """Return the bought figures of all households, with their chapters."""
        nodes = await self._graphql_nodes("myContentTonies", _CONTENT_TONIE_FIELDS)
        return [t for node in nodes if (t := parse_content_tonie(node))]

    async def async_discs(self) -> list[Tonie]:
        """Return the discs of all households."""
        nodes = await self._graphql_nodes("myDiscs", _DISC_FIELDS)
        return [t for node in nodes if (t := parse_disc(node))]

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
