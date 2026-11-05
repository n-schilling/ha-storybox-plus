"""The REST and GraphQL client against a mocked API, without Home Assistant's integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from yarl import URL

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.storybox_plus.cloud import (
    Auth,
    Chapter,
    CloudAuthError,
    CloudClient,
    CloudConnectionError,
    CloudResponseError,
    TonieKind,
)
from custom_components.storybox_plus.cloud.auth import TOKEN_URL
from custom_components.storybox_plus.cloud.rest import API_BASE, PAGE_SIZE, _shape

from .conftest import (
    DISC_NAME,
    GRAPHQL_REFUSED,
    JSON_HEADERS,
    PLAYBACK_INFO_SERIES,
    TONIE_NAME,
    classic_box,
    connection_node,
    content_tonie,
    creative_tonie,
    disc,
    playback_info,
    tb2_box,
)

ME = f"{API_BASE}/me"
HOUSEHOLDS = f"{API_BASE}/households"
GRAPHQL = f"{API_BASE}/graphql"
PLAYBACK_INFO = f"{API_BASE}/playback-info/box1/t1"


def _token_answer(access: str) -> dict[str, Any]:
    return {
        "access_token": access,
        "expires_in": 300,
        "refresh_expires_in": 0,
        "refresh_token": "refresh-1",
    }


def _calls(aioclient_mock: AiohttpClientMocker, url: str) -> list[tuple[Any, ...]]:
    return [call for call in aioclient_mock.mock_calls if call[1] == URL(url)]


def _page(field: str, nodes: list[dict[str, Any]], cursor: str | None = None) -> dict[str, Any]:
    return {
        "data": {
            field: {
                "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor},
                "edges": [{"node": node} for node in nodes],
            }
        }
    }


def _households(*households: tuple[Any, Any]) -> dict[str, Any]:
    """Return the answer of the library query: figures under their households."""
    return {
        "data": {"households": [{"id": hid, "contentTonies": nodes} for hid, nodes in households]}
    }


@pytest.fixture
def client(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> CloudClient:
    """A client whose login server hands out one token after another."""
    counter = iter(range(1, 100))

    async def token(method: str, url: URL, data: dict[str, str]) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(
            method=method,
            url=url,
            json=_token_answer(f"access-{next(counter)}"),
            headers=JSON_HEADERS,
        )

    aioclient_mock.post(TOKEN_URL, side_effect=token)
    session = async_get_clientsession(hass)
    return CloudClient(session, Auth(session, "refresh-0"))


async def test_user_id(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """GET /me names the account; the request carries the access token."""
    aioclient_mock.get(ME, json={"uuid": "user-1", "email": "test@example.com"})
    assert await client.async_user_id() == "user-1"
    (call,) = _calls(aioclient_mock, ME)
    assert call[0] == "GET"
    assert call[3] == {"Authorization": "Bearer access-1"}


async def test_user_id_variants(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """An id field is accepted too; an answer without any is an error."""
    answers = iter([{"id": "user-2"}, {"email": "x"}, [1, 2]])

    async def me(method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(method=method, url=url, json=next(answers))

    aioclient_mock.get(ME, side_effect=me)
    assert await client.async_user_id() == "user-2"
    with pytest.raises(CloudResponseError, match="without a user ID"):
        await client.async_user_id()
    with pytest.raises(CloudResponseError, match="without a user ID"):
        await client.async_user_id()


async def test_rejected_token_is_refreshed_once(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """A 401 makes the client refresh the token and repeat the request once."""
    statuses = iter([401, 200])

    async def me(method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(
            method=method, url=url, status=next(statuses), json={"uuid": "user-1"}
        )

    aioclient_mock.get(ME, side_effect=me)
    assert await client.async_user_id() == "user-1"
    calls = _calls(aioclient_mock, ME)
    assert [c[3]["Authorization"] for c in calls] == ["Bearer access-1", "Bearer access-2"]
    assert len(_calls(aioclient_mock, TOKEN_URL)) == 2


async def test_rejected_token_twice_is_an_auth_error(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """When the fresh token is rejected as well, the account needs a new login."""
    aioclient_mock.get(ME, status=401, json={"message": "Unauthorized"})
    with pytest.raises(CloudAuthError):
        await client.async_user_id()
    assert len(_calls(aioclient_mock, ME)) == 2


@pytest.mark.parametrize("status", [400, 404, 500])
async def test_error_status(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, status: int
) -> None:
    """Other errors name the status and are not retried."""
    aioclient_mock.get(ME, status=status, json={"message": "no"})
    with pytest.raises(CloudResponseError) as err:
        await client.async_user_id()
    assert err.value.status == status
    assert str(status) in str(err.value)
    assert len(_calls(aioclient_mock, ME)) == 1


@pytest.mark.parametrize("exc", [TimeoutError(), aiohttp.ClientConnectionError("down")])
async def test_connection_errors(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, exc: Exception
) -> None:
    """Timeouts and network errors are connection errors."""
    aioclient_mock.get(ME, exc=exc)
    with pytest.raises(CloudConnectionError, match="GET /me"):
        await client.async_user_id()


async def test_no_json(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """A body that is no JSON is a response error."""
    aioclient_mock.get(ME, text="<html>maintenance</html>")
    with pytest.raises(CloudResponseError, match="no JSON"):
        await client.async_user_id()


@pytest.mark.parametrize(
    "body",
    [
        [{"id": "hh1", "name": "A"}, "junk", {"name": "no id"}, {"id": "hh2", "name": "B"}],
        {"households": [{"id": "hh1", "name": "A"}, {"id": "hh2", "name": "B"}]},
        {"results": [{"id": "hh1", "name": "A"}, {"id": "hh2", "name": "B"}], "total": 2},
    ],
)
async def test_households_list_shapes(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, body: Any
) -> None:
    """Lists come bare or wrapped in an object; items that are no objects are dropped."""
    aioclient_mock.get(HOUSEHOLDS, json=body)
    households = await client.async_households()
    assert [(h.id, h.name) for h in households] == [("hh1", "A"), ("hh2", "B")]


@pytest.mark.parametrize("body", [{"total": 0}, "text", 5, {"results": {"a": 1}}])
async def test_households_no_list(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, body: Any
) -> None:
    """An answer that holds no list is a response error."""
    aioclient_mock.get(HOUSEHOLDS, json=body)
    with pytest.raises(CloudResponseError, match="no list"):
        await client.async_households()


async def test_boxes_and_creative_tonies(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """Boxes and creative figures are read per household."""
    aioclient_mock.get(f"{HOUSEHOLDS}/hh1/tonieboxes", json=[tb2_box(), classic_box()])
    aioclient_mock.get(
        f"{HOUSEHOLDS}/hh1/creativetonies", json={"creativetonies": [creative_tonie()]}
    )
    boxes = await client.async_boxes("hh1")
    assert [(b.id, b.household_id, b.live) for b in boxes] == [
        ("box1", "hh1", True),
        ("box2", "hh1", False),
    ]
    tonies = await client.async_creative_tonies("hh1")
    assert [(t.id, t.kind, t.household_id) for t in tonies] == [("c1", TonieKind.CREATIVE, "hh1")]


async def test_graphql_pagination(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """Every page of a connection is read until hasNextPage is false."""
    pages = {
        None: _page("myDiscs", [disc("d1"), disc("d2")], cursor="c2"),
        "c2": _page("myDiscs", [disc("d3")]),
    }

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        assert f"myDiscs(first: {PAGE_SIZE}, after: $cursor)" in data["query"]
        return AiohttpClientMockResponse(
            method=method, url=url, json=pages[data["variables"]["cursor"]]
        )

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    discs = await client.async_discs()
    assert [d.id for d in discs] == ["d1", "d2", "d3"]
    assert all(d.kind is TonieKind.DISC for d in discs)
    calls = _calls(aioclient_mock, GRAPHQL)
    assert [c[2]["variables"] for c in calls] == [{"cursor": None}, {"cursor": "c2"}]


async def test_content_tonies_library_query(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """One query lists the bought figures under their households, with their chapter names."""

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        assert data["query"].startswith("query { households { id contentTonies {")
        assert "chapters { name }" in data["query"]
        assert data["variables"] == {}
        body = _households(
            ("hh1", [content_tonie("t1"), "junk", {"title": "no id"}]),
            ("hh2", [content_tonie("t2", household_id="hh9")]),
            (5, [content_tonie("t3")]),
            ("hh3", None),
        )
        body["data"]["households"] += ["junk", {"contentTonies": [content_tonie("t4")]}]
        return AiohttpClientMockResponse(method=method, url=url, json=body)

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    tonies = await client.async_content_tonies()
    assert [(t.id, t.household_id, t.kind) for t in tonies] == [
        ("t1", "hh1", TonieKind.CONTENT),
        ("t2", "hh2", TonieKind.CONTENT),
    ]
    assert [(c.id, c.title) for c in tonies[0].chapters] == [("0", "Kapitel 1"), ("1", "Kapitel 2")]
    assert tonies[0].seconds == 500
    assert len(_calls(aioclient_mock, GRAPHQL)) == 1


@pytest.mark.parametrize(
    "answer", [GRAPHQL_REFUSED, {"data": {"households": "junk"}}, {"data": {}}]
)
async def test_content_tonies_fall_back_to_the_connection(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, answer: dict[str, Any]
) -> None:
    """A refused library query is followed by the older connection query, without chapters."""
    pages = {
        None: _page("myContentTonies", [connection_node(content_tonie("t1"))], cursor="c2"),
        "c2": _page("myContentTonies", [connection_node(content_tonie("t2"))]),
    }

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        if "myContentTonies" not in data["query"]:
            return AiohttpClientMockResponse(method=method, url=url, json=answer)
        assert f"myContentTonies(first: {PAGE_SIZE}, after: $cursor)" in data["query"]
        assert "chapters" not in data["query"]
        return AiohttpClientMockResponse(
            method=method, url=url, json=pages[data["variables"]["cursor"]]
        )

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    tonies = await client.async_content_tonies()
    assert [(t.id, t.household_id, t.chapters, t.seconds) for t in tonies] == [
        ("t1", "hh1", (), 0),
        ("t2", "hh1", (), 0),
    ]
    assert tonies[0].language == "Deutsch"
    calls = _calls(aioclient_mock, GRAPHQL)
    assert [c[2]["variables"] for c in calls] == [{}, {"cursor": None}, {"cursor": "c2"}]


async def test_content_tonie_detail(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """The app's detail query reads one figure of a household; anything else is not found."""
    answers = iter(
        [
            _households(("hh1", [content_tonie("t1")])),
            _households(),
            _households(("hh1", [])),
            {"data": {"households": ["junk", {"contentTonies": ["junk", {"title": "no id"}]}]}},
        ]
    )

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        assert "households(id: $householdId)" in data["query"]
        assert "contentTonies(id: $contentTonieId)" in data["query"]
        assert data["variables"] == {"householdId": "hh1", "contentTonieId": "t1"}
        return AiohttpClientMockResponse(method=method, url=url, json=next(answers))

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    tonie = await client.async_content_tonie("hh1", "t1")
    assert tonie is not None
    assert (tonie.id, tonie.household_id, tonie.kind) == ("t1", "hh1", TonieKind.CONTENT)
    assert [c.title for c in tonie.chapters] == ["Kapitel 1", "Kapitel 2"]
    for _ in range(3):
        assert await client.async_content_tonie("hh1", "t1") is None
    assert len(_calls(aioclient_mock, GRAPHQL)) == 4


async def test_content_tonie_detail_errors(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """A refused detail query is a response error, a lost connection a connection error."""
    aioclient_mock.post(GRAPHQL, json=GRAPHQL_REFUSED)
    with pytest.raises(CloudResponseError, match="GraphQL answered no data"):
        await client.async_content_tonie("hh1", "t1")
    aioclient_mock.clear_requests()
    aioclient_mock.post(GRAPHQL, exc=aiohttp.ClientConnectionError("down"))
    with pytest.raises(CloudConnectionError):
        await client.async_content_tonie("hh1", "t1")


async def test_graphql_tolerates_odd_pages(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """Broken edges are skipped; a page without pageInfo ends the reading."""
    aioclient_mock.post(
        GRAPHQL,
        json={
            "data": {
                "myDiscs": {
                    "edges": [{"node": disc("d1")}, "junk", {"node": "junk"}, {"node": disc("d2")}]
                }
            }
        },
    )
    discs = await client.async_discs()
    assert [(d.id, d.kind) for d in discs] == [("d1", TonieKind.DISC), ("d2", TonieKind.DISC)]
    assert len(_calls(aioclient_mock, GRAPHQL)) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"errors": [{"message": "Cannot query field"}], "data": None},
        {"data": {"myContentTonies": None}},
        {"data": "x"},
        [],
    ],
)
async def test_graphql_without_data(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, body: Any
) -> None:
    """An answer without the connection is a response error."""
    aioclient_mock.post(GRAPHQL, json=body)
    with pytest.raises(CloudResponseError, match="myContentTonies answered no data"):
        await client.async_content_tonies()


def test_shape_names_types_and_sizes_only() -> None:
    """The debug dump of a node keeps numbers, flags and the lock, never titles or IDs."""
    assert _shape(content_tonie()) == {
        "id": "str[2]",
        "householdId": "str[3]",
        "title": "str[15]",
        "lock": False,
        "imageUrl": "str[30]",
        "coverUrl": None,
        "languageName": "Deutsch",
        "languageUnicode": "str[5]",
        "salesId": "str[3]",
        "series": "dict['name']",
        "chapters": "list[2]",
        "secondsPresent": 500,
    }
    assert _shape({"count": 3, "ratio": 1.5, "language": "de", "lock": True, "b": {}}) == {
        "count": 3,
        "ratio": 1.5,
        "language": "de",
        "lock": True,
        "b": "dict[]",
    }


async def test_graphql_debug_log_holds_only_the_shape(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, caplog: pytest.LogCaptureFixture
) -> None:
    """With debug logging on, the first node's shape is logged once per query, without names."""
    caplog.set_level(logging.DEBUG, logger="custom_components.storybox_plus.cloud.rest")
    pages = {
        None: _page("myDiscs", [disc("d1"), disc("d2")], cursor="c2"),
        "c2": _page("myDiscs", [disc("d3")]),
    }

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(
            method=method, url=url, json=pages[data["variables"]["cursor"]]
        )

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    await client.async_discs()
    shapes = [r.message for r in caplog.records if "shape of the first node" in r.message]
    assert len(shapes) == 1
    assert "'title': 'str[9]'" in shapes[0]
    assert "'coverImageUrl': 'str[30]'" in shapes[0]
    assert DISC_NAME not in shapes[0]
    assert "'d1'" not in shapes[0]


def _playback_info_calls(aioclient_mock: AiohttpClientMocker) -> list[tuple[Any, ...]]:
    """Return the playback-info calls, whatever content version they carried."""
    return [c for c in aioclient_mock.mock_calls if c[1].with_query(None) == URL(PLAYBACK_INFO)]


async def test_playback_info(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """The figure on a box is read with its chapters; the content version is 0 while unknown."""
    aioclient_mock.get(PLAYBACK_INFO, json=playback_info())
    details = await client.async_playback_info("box1", "t1")
    assert details is not None
    assert details.title == TONIE_NAME
    assert details.series == PLAYBACK_INFO_SERIES
    assert details.status == "available"
    assert [c.id for c in details.chapters] == ["0", "1", "2"]
    (call,) = _playback_info_calls(aioclient_mock)
    assert call[0] == "GET"
    assert call[1].query == {"contentVersion": "0"}
    assert call[3] == {"Authorization": "Bearer access-1"}


async def test_playback_info_sends_the_content_version(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """The version of the content the box holds goes along, as the cloud insists on it."""
    aioclient_mock.get(PLAYBACK_INFO, json=playback_info())
    assert await client.async_playback_info("box1", "t1", 1730000000) is not None
    (call,) = _playback_info_calls(aioclient_mock)
    assert str(call[1]) == f"{PLAYBACK_INFO}?contentVersion=1730000000"


@pytest.mark.parametrize("status", [400, 404])
async def test_playback_info_unknown_figure(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, status: int
) -> None:
    """A figure the cloud knows nothing about is no error, just nothing."""
    aioclient_mock.get(PLAYBACK_INFO, status=status, json={"message": "no"})
    assert await client.async_playback_info("box1", "t1") is None
    assert len(_playback_info_calls(aioclient_mock)) == 1


async def test_playback_info_errors(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """Other errors and lost connections are passed on."""
    aioclient_mock.get(PLAYBACK_INFO, status=500, json={"message": "no"})
    with pytest.raises(CloudResponseError) as err:
        await client.async_playback_info("box1", "t1")
    assert err.value.status == 500
    aioclient_mock.clear_requests()
    aioclient_mock.get(PLAYBACK_INFO, exc=aiohttp.ClientConnectionError("down"))
    with pytest.raises(CloudConnectionError):
        await client.async_playback_info("box1", "t1")


@pytest.mark.parametrize("body", [[], "text", 5, None])
async def test_playback_info_without_figure(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, body: Any
) -> None:
    """An answer that is no object, or no body at all, is nothing."""
    aioclient_mock.get(PLAYBACK_INFO, json=body)
    assert await client.async_playback_info("box1", "t1") is None


async def test_library(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """The library gathers households, boxes and all three kinds of figures."""
    aioclient_mock.get(HOUSEHOLDS, json=[{"id": "hh1", "name": "A"}, {"id": "hh2", "name": "B"}])
    aioclient_mock.get(f"{HOUSEHOLDS}/hh1/tonieboxes", json=[tb2_box()])
    aioclient_mock.get(f"{HOUSEHOLDS}/hh1/creativetonies", json=[creative_tonie()])
    aioclient_mock.get(f"{HOUSEHOLDS}/hh2/tonieboxes", json=[classic_box()])
    aioclient_mock.get(f"{HOUSEHOLDS}/hh2/creativetonies", json=[])

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        if "myDiscs" in data["query"]:
            body = _page("myDiscs", [disc()])
        else:
            body = _households(("hh1", []), ("hh2", [content_tonie()]))
        return AiohttpClientMockResponse(method=method, url=url, json=body)

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    library = await client.async_library()
    assert [h.id for h in library.households] == ["hh1", "hh2"]
    assert [(b.id, b.household_id) for b in library.boxes] == [("box1", "hh1"), ("box2", "hh2")]
    assert [(t.id, t.kind, t.household_id) for t in library.tonies] == [
        ("c1", TonieKind.CREATIVE, "hh1"),
        ("t1", TonieKind.CONTENT, "hh2"),
        ("d1", TonieKind.DISC, "hh1"),
    ]
    assert [c.title for c in library.tonies[1].chapters] == ["Kapitel 1", "Kapitel 2"]


async def test_library_without_discs(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """An account whose discs cannot be read still gets its other figures."""
    aioclient_mock.get(HOUSEHOLDS, json=[])

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        if "myDiscs" in data["query"]:
            body: Any = {"errors": [{"message": "no discs"}]}
        else:
            body = _households(("hh1", [content_tonie()]))
        return AiohttpClientMockResponse(method=method, url=url, json=body)

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    library = await client.async_library()
    assert library.households == ()
    assert [t.id for t in library.tonies] == ["t1"]


async def test_library_passes_on_connection_errors(
    aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """Only a refused disc query is tolerated, not a lost connection."""
    aioclient_mock.get(HOUSEHOLDS, json=[])

    async def graphql(method: str, url: URL, data: dict[str, Any]) -> AiohttpClientMockResponse:
        if "myDiscs" in data["query"]:
            raise aiohttp.ClientConnectionError("down")
        return AiohttpClientMockResponse(method=method, url=url, json=_households())

    aioclient_mock.post(GRAPHQL, side_effect=graphql)
    with pytest.raises(CloudConnectionError):
        await client.async_library()


async def test_set_chapters(aioclient_mock: AiohttpClientMocker, client: CloudClient) -> None:
    """The chapter list is sent whole; missing file names and lengths get defaults."""
    url = f"{HOUSEHOLDS}/hh1/creativetonies/c1"
    aioclient_mock.patch(url, json=creative_tonie())
    tonie = await client.async_set_chapters(
        "hh1",
        "c1",
        [Chapter("ch1", "Song", 120.5, False, "f1"), Chapter("ch2", "Jingle", None, True, None)],
    )
    assert tonie is not None
    assert tonie.id == "c1"
    (call,) = _calls(aioclient_mock, url)
    assert call[0] == "PATCH"
    assert call[2] == {
        "chapters": [
            {"id": "ch1", "title": "Song", "file": "f1", "seconds": 120.5, "transcoding": False},
            {"id": "ch2", "title": "Jingle", "file": "ch2", "seconds": 0, "transcoding": True},
        ]
    }


@pytest.mark.parametrize(("status", "text"), [(204, None), (200, "")])
async def test_set_chapters_without_body(
    aioclient_mock: AiohttpClientMocker, client: CloudClient, status: int, text: str | None
) -> None:
    """An empty answer yields no figure, without an error."""
    url = f"{HOUSEHOLDS}/hh1/creativetonies/c1"
    aioclient_mock.patch(url, status=status, text=text)
    assert await client.async_set_chapters("hh1", "c1", []) is None


async def test_base_url_without_trailing_slash(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, client: CloudClient
) -> None:
    """A base URL with a trailing slash is normalized."""
    aioclient_mock.get("https://api.example.com/v9/me", json={"uuid": "u"})
    session = async_get_clientsession(hass)
    other = CloudClient(session, Auth(session, "refresh-0"), "https://api.example.com/v9/")
    assert await other.async_user_id() == "u"
