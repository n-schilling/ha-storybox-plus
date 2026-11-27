"""The check of the cloud's interface: what is expected of each read request, and what it reports."""

from __future__ import annotations

from datetime import timedelta
import json
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud import contract
from custom_components.storybox_plus.cloud.contract import Result, check_topics, compare, endpoint
from custom_components.storybox_plus.cloud.push import PushClient
from custom_components.storybox_plus.const import DOMAIN, TESTED_BACKEND_RELEASE

from .conftest import BOX_ID, HOUSEHOLD_ID, MAC, TONIE_ID, FakeCloud, PushChannels, playback_info

# What a Toniebox 2 and a classic box name beside what the fixtures give them
TB2_SETTINGS: dict[str, Any] = {
    "maxVolume": 74,
    "maxHeadphoneVolume": 60,
    "lightringBrightness": 80,
    "bedtimeLightringBrightness": 49,
    "bedtimeMaxVolume": 51,
    "bedtimeMaxHeadphoneVolume": 75,
    "skippingEnabled": False,
    "skippingDirection": "left",
    "scrubbingEnabled": False,
}
CLASSIC_SETTINGS: dict[str, Any] = {
    "maxVolume": 75,
    "maxHeadphoneVolume": 50,
    "accelerometerEnabled": False,
    "tapDirection": "left",
    "ledLevel": "dimmed",
}


@pytest.fixture
def complete(cloud: FakeCloud) -> FakeCloud:
    """An account whose answers carry everything the integration uses."""
    account = cloud.main
    tb2, classic = account.boxes[HOUSEHOLD_ID]
    tb2.update(TB2_SETTINGS)
    classic.update(CLASSIC_SETTINGS)
    account.creative_tonies[HOUSEHOLD_ID][0].update({"transcoding": False, "live": False})
    account.members[HOUSEHOLD_ID] = [
        {"id": "m1", "displayName": "Sam", "mtype": "owner", "isSelf": True, "email": "s@x.org"}
    ]
    account.notices = [{"id": "n1", "text": "Hello", "read": False, "ntype": "news"}]
    account.playback_info[(BOX_ID, TONIE_ID)] = playback_info()
    return cloud


def by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["name"]: r for r in report["results"]}


# ---------------------------------------------------------------- the parts


@pytest.mark.parametrize(
    ("method", "path", "body", "name"),
    [
        ("GET", "/me", None, "GET /me"),
        ("get", "/households", None, "GET /households"),
        (
            "GET",
            "/households/f0fef117-51dc/tonieboxes/UCPACRSG/bedtime-schedules",
            None,
            "GET /households/{id}/tonieboxes/{id}/bedtime-schedules",
        ),
        (
            "GET",
            "/playback-info/UCPACRSG/8D383525500304E0?contentVersion=17",
            None,
            "GET /playback-info/{id}/{id}",
        ),
        ("POST", "/graphql", {"query": "query { households { id } }"}, "GraphQL households"),
        (
            "POST",
            "/graphql",
            {
                "query": "query($cursor: String) { tunesItems(first: 100) { edges { node { id } } } }"
            },
            "GraphQL tunesItems",
        ),
        ("POST", "/graphql", {"query": 7}, "GraphQL"),
        ("POST", "/graphql", None, "GraphQL"),
    ],
)
def test_requests_are_named_by_their_shape(method: str, path: str, body: Any, name: str) -> None:
    """IDs and the query string are gone; a GraphQL request is named by its field."""
    assert endpoint(method, path, body) == name


def test_compare_names_fields_and_kinds_only() -> None:
    """What is missing or of another kind is named; values never show."""
    spec = {
        "id": contract.S,
        "count": contract.I,
        "length": contract.N,
        "note": contract.S + contract.NULL,
        "chapters": contract.L,
        "chapters[].title": contract.S,
        "series.name": contract.S,
        "owner.id": contract.S,
    }
    good = {
        "id": "secret-id",
        "count": 3,
        "length": 2.5,
        "note": None,
        "chapters": [{"title": "One"}, {"title": "Two"}, "odd"],
        "series": {"name": "S"},
        "owner": None,
    }
    assert compare(good, spec) == []
    # An empty list and an object that is null hold nothing to compare
    assert compare({**good, "chapters": []}, spec) == []
    bad = {
        "id": 7,
        "count": True,
        "length": "long",
        "chapters": [{"title": "One"}, {"name": "Two"}],
        "series": {"name": None},
        "owner": {"id": 1.5},
    }
    assert compare(bad, spec) == [
        "id is int, expected str",
        "count is bool, expected int",
        "length is str, expected int/float",
        "note is missing",
        "chapters[].title is missing",
        "series.name is null, expected str",
        "owner.id is float, expected str",
    ]
    assert compare({**good, "chapters": {"a": 1}}, spec) == [
        "chapters is dict, expected list",
        "chapters[].title is dict, expected str",
    ]
    assert compare(["no object"], spec) == ["answer is list, expected an object"]
    assert compare({"x": object()}, {"x": contract.S}) == ["x is object, expected str"]
    assert compare({"a": "text"}, {"a.b": contract.S}) == ["a.b is missing"]


def test_topics_of_the_push_channel() -> None:
    """The keys of the last message per topic; a topic nothing came on is unseen."""
    seen = {
        "metrics/battery": frozenset({"percent", "raw", "status"}),
        "online-state": frozenset({"state"}),
        "playback/state": frozenset(
            {"tonie", "chapter", "paused", "ended", "downloading", "chapterDuration", "blocked"}
        ),
        "volume/state": frozenset({"level", "hardwarePercentage"}),
    }
    assert check_topics(seen) == [
        Result("Push metrics/battery", "ok"),
        Result("Push online-state", "changed", ("onlineState is missing",)),
        Result("Push playback/state", "changed", ("none of chapterPositionMs, chapterUntilMs",)),
        Result("Push volume/state", "ok"),
        Result("Push app-reply/bedtime-state", "unseen"),
        Result("Push metrics/headphones", "unseen"),
    ]
    assert Result("x", "changed", ("a is missing",)).as_dict() == {
        "name": "x",
        "status": "changed",
        "detail": ["a is missing"],
    }
    assert contract.passed([Result("a", "ok"), Result("b", "empty"), Result("c", "unseen")])
    assert not contract.passed([Result("a", "ok"), Result("b", "failed", ("answered 500",))])


def test_the_push_channel_keeps_the_keys_it_saw() -> None:
    """Every message leaves its keys; the one that says a figure was taken off does not."""
    push = PushClient.__new__(PushClient)
    push.seen_keys = {}
    topic = f"external/toniebox/{MAC}/"
    assert push._parse(topic + "playback/state", b'{"tonie": "t1", "chapter": 0, "paused": false}')
    assert push._parse(topic + "playback/state", b'{"tonie": null}')
    assert push._parse(topic + "playback/state", b"")
    assert push._parse(topic + "volume/state", b'{"level": 3}')
    assert push.seen_keys == {
        "playback/state": frozenset({"tonie", "chapter", "paused"}),
        "volume/state": frozenset({"level"}),
    }


# ---------------------------------------------------------------- the check


async def test_an_account_that_answers_as_expected(
    hass: HomeAssistant,
    complete: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Every request is compared; the report carries nothing of the account."""
    channel = push.last
    channel.connect()
    channel.playback(chapter=0, content_version=3)
    channel.seen_keys["volume/state"] = frozenset({"level", "hardwarePercentage"})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cloud/check", "entry_id": setup_entry.entry_id}
    )
    answer = await client.receive_json()
    assert answer["success"], answer
    report = answer["result"]
    assert report["ok"] is True
    assert (report["release"], report["tested"]) == (TESTED_BACKEND_RELEASE, TESTED_BACKEND_RELEASE)
    assert {r["name"]: r["status"] for r in report["results"]} == {
        "GET /me": "ok",
        "GET /households": "ok",
        "GET /households/{id}/tonieboxes": "ok",
        "GET /households/{id}/creativetonies": "ok",
        "GET /households/{id}/memberships": "ok",
        "GET /households/{id}/tonieboxes/{id}/bedtime-schedules": "empty",
        "GET /notifications": "ok",
        "GET /system-notifications": "empty",
        "GET /box-item-previews": "ok",
        "GET /playback-info/{id}/{id}": "ok",
        "GraphQL households": "ok",
        "GraphQL myDiscs": "ok",
        "GraphQL tunesItems": "empty",
        "GET /version": "ok",
        "Push metrics/battery": "unseen",
        "Push online-state": "unseen",
        "Push playback/state": "unseen",
        "Push volume/state": "ok",
        "Push app-reply/bedtime-state": "unseen",
        "Push metrics/headphones": "unseen",
    }
    assert all(r["detail"] == [] for r in report["results"])
    # Nothing of the account: no ID, no name, no address
    text = json.dumps(report)
    for secret in (HOUSEHOLD_ID, BOX_ID, TONIE_ID, MAC, "Sam", "s@x.org"):
        assert secret not in text
    # The page reads the report with the overview, and it is kept across a restart
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    overview = (await client.receive_json())["result"]
    assert overview["entries"][0]["cloud"]["check"] == report
    # The client listens to nothing once the check is over
    assert setup_entry.runtime_data.coordinator.client.watch is None


async def test_what_changed_and_what_failed(
    hass: HomeAssistant,
    complete: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Fields that are gone and requests that are refused are named, without values."""
    account = complete.main
    tb2 = account.boxes[HOUSEHOLD_ID][0]
    del tb2["macAddress"]
    tb2["maxVolume"] = "loud"
    account.creative_tonies[HOUSEHOLD_ID][0]["chapters"][0].pop("file")
    account.schedules_status = 500
    account.discs_error = True
    account.playback_info[(BOX_ID, TONIE_ID)] = {"status": "available", "chapters": [{"name": "x"}]}
    push.last.connect()
    push.last.playback(chapter=0)
    report = await setup_entry.runtime_data.coordinator.async_check_cloud()
    found = by_name(report)
    assert report["ok"] is False
    assert found["GET /households/{id}/tonieboxes"] == {
        "name": "GET /households/{id}/tonieboxes",
        "status": "changed",
        "detail": ["macAddress is missing", "maxVolume is str, expected int"],
    }
    assert found["GET /households/{id}/creativetonies"]["detail"] == ["chapters[].file is missing"]
    assert found["GET /households/{id}/tonieboxes/{id}/bedtime-schedules"] == {
        "name": "GET /households/{id}/tonieboxes/{id}/bedtime-schedules",
        "status": "failed",
        "detail": ["answered 500"],
    }
    assert found["GET /playback-info/{id}/{id}"]["detail"] == [
        "chapters[].title is missing",
        "chapters[].seconds is missing",
    ]
    # An account without discs has always got an error for an answer: nothing to compare
    assert found["GraphQL myDiscs"]["status"] == "empty"
    assert "answers differently than expected" in caplog.text
    assert "GET /households/{id}/tonieboxes" in caplog.text
    assert setup_entry.runtime_data.preferences.cloud_check == report


async def test_a_library_query_the_cloud_refuses(
    hass: HomeAssistant,
    complete: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """The older query answers in its place, so nothing fails; the check says so."""
    complete.main.library_query_refused = True
    report = await setup_entry.runtime_data.coordinator.async_check_cloud()
    assert by_name(report)["GraphQL households"] == {
        "name": "GraphQL households",
        "status": "changed",
        "detail": ["answer is dict, not the list it was"],
    }


async def test_the_cloud_cannot_be_reached(
    hass: HomeAssistant,
    complete: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """Requests that get no answer are failed, the version among them."""
    complete.version = None
    complete.main.rest_status = 503
    report = await setup_entry.runtime_data.coordinator.async_check_cloud()
    found = by_name(report)
    assert found["GET /households"] == {
        "name": "GET /households",
        "status": "failed",
        "detail": ["answered 503"],
    }
    # Without the households nothing below them is asked
    assert found["GET /households/{id}/tonieboxes"]["status"] == "unseen"
    assert found["GraphQL tunesItems"]["status"] == "failed"
    assert found["GET /version"]["status"] == "failed"
    assert report["ok"] is False
    complete.main.rest_status = None
    complete.main.rest_unreachable = True
    report = await setup_entry.runtime_data.coordinator.async_check_cloud()
    assert by_name(report)["GET /me"]["detail"] == ["CloudConnectionError"]


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"entry_id": "nope"}, "unknown_entry"),
        ({}, "invalid_format"),
    ],
)
async def test_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """An account that is not loaded has nothing to check."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/cloud/check", **message})
    answer = await client.receive_json()
    assert not answer["success"]
    assert answer["error"]["code"] == code


async def test_the_check_needs_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """The check is a command of the page, which is for administrators."""
    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cloud/check", "entry_id": setup_entry.entry_id}
    )
    answer = await client.receive_json()
    assert answer["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------- by itself


async def test_a_release_not_tested_with_is_checked_once(
    hass: HomeAssistant,
    complete: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The cloud reports another release: the check runs by itself, once per release."""
    complete.version = "v2099.01.01/abc"
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=False)
    for _ in range(20):
        await hass.async_block_till_done()
    preferences = config_entry.runtime_data.preferences
    first = preferences.cloud_check
    assert first is not None
    assert (first["release"], first["ok"]) == ("v2099.01.01", True)
    # An hour later, the same release: not again
    freezer.tick(timedelta(hours=1, minutes=6))
    async_fire_time_changed(hass)
    for _ in range(20):
        await hass.async_block_till_done()
    assert preferences.cloud_check == first
    # The next release: once more
    complete.version = "v2099.02.02/def"
    freezer.tick(timedelta(hours=1, minutes=6))
    async_fire_time_changed(hass)
    for _ in range(20):
        await hass.async_block_till_done()
    assert preferences.cloud_check["release"] == "v2099.02.02"


async def test_the_tested_release_is_not_checked_by_itself(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """Nothing runs while the cloud runs the release this version was tested with."""
    for _ in range(10):
        await hass.async_block_till_done()
    assert setup_entry.runtime_data.preferences.cloud_check is None
