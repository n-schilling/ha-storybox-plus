"""Bought Tunes: read from the cloud, laid on a figure and taken off again."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud.models import parse_tune
from custom_components.storybox_plus.const import DOMAIN

from .conftest import CREATIVE_ID, DISC_ID, TONIE_ID, FakeCloud, PushChannels, tune


def test_parse_tune() -> None:
    """The account's copy names the Tune; one without it is none the account owns."""
    parsed = parse_tune(tune(assigned=(TONIE_ID,)))
    assert parsed is not None
    assert parsed.id == "my-tune-1"
    assert parsed.title == "Bakabu"
    assert parsed.series == "Bakabu"
    assert parsed.seconds == 3138
    assert parsed.remaining == 2
    assert parsed.assigned == (TONIE_ID,)
    assert parsed.suitable == (CREATIVE_ID,)
    assert parse_tune({"id": "x", "title": "Not mine", "myTune": None}) is None
    bare = parse_tune({"myTune": {"id": "t", "assignedTonies": "x"}})
    assert bare is not None
    assert (bare.title, bare.assigned, bare.remaining) == ("Tune", (), None)


async def _setup(hass: HomeAssistant, cloud: FakeCloud, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


async def test_tune_laid_on_and_taken_off(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The library lists the Tunes; laid on a creative figure, it is read anew; taken off again."""
    cloud.main.tunes = [tune()]
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    library = await _call(client, {"type": f"{DOMAIN}/library"})
    assert library["result"]["tunes"] == [
        {
            "id": "my-tune-1",
            "title": "Bakabu",
            "image_url": "https://img.example.com/tune.png",
            "series": "Bakabu",
            "seconds": 3138,
            "remaining": 2,
            "assigned": [],
            "suitable": [CREATIVE_ID],
        }
    ]
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": "my-tune-1"}
    )
    assert result["success"], result
    assert cloud.tune_changes == [("PUT", CREATIVE_ID, "my-tune-1")]
    assert result["result"]["tunes"][0]["assigned"] == [CREATIVE_ID]
    assert result["result"]["tunes"][0]["remaining"] == 1
    assert result["result"]["figure"]["id"] == CREATIVE_ID
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.tune_on(CREATIVE_ID) is not None
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": None}
    )
    assert result["success"], result
    assert cloud.tune_changes[-1] == ("DELETE", CREATIVE_ID, None)
    assert result["result"]["tunes"][0]["assigned"] == []


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"tonie_id": "nope", "tune_id": "my-tune-1"}, "unknown_figure"),
        ({"tonie_id": CREATIVE_ID, "tune_id": "other"}, "unknown_tune"),
        ({"tonie_id": DISC_ID, "tune_id": "my-tune-1"}, "unsuitable_tune"),
        ({"tonie_id": TONIE_ID, "tune_id": None}, "no_tune"),
    ],
)
async def test_tune_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Unknown figures and Tunes, a figure the Tune does not fit, and nothing to take off."""
    cloud.main.tunes = [tune()]
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": f"{DOMAIN}/figure/tune", **message})
    assert result["error"]["code"] == code
    assert cloud.tune_changes == []


async def test_tune_cloud_error_and_failed_read(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A refused Tune comes back as cloud_error; a failed read keeps the last Tunes."""
    cloud.main.tunes = [tune(remaining=0)]
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": "my-tune-1"}
    )
    assert result["error"]["code"] == "cloud_error"
    coordinator = config_entry.runtime_data.coordinator
    cloud.main.tunes_status = 500
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.tunes is not None
    assert len(coordinator.tunes) == 1
