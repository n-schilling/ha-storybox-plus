"""A made-up cloud for the page checks: no request leaves the machine.

run_hass.py calls install() before Home Assistant starts. It replaces the
integration's login, REST client and push channel by the classes below, which
answer with invented households, boxes and figures and report a box that plays.
Everything above the cloud layer (coordinator, stores, WebSocket commands, the
page) runs unchanged.

The pictures of the figures are SVG files that check_panel.py writes into the
config's www folder; Home Assistant serves them under /local/.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import os
import time
from typing import Any

USER_ID = "4f9b3c2e-0000-4000-8000-000000000001"
HOUSEHOLD = "home"
KIDS_BOX = "box-kids"
KIDS_MAC = "0A0B0C0D0E01"
LIVING_BOX = "box-living"

# id, name, series, chapter titles with seconds, language
BOUGHT = [
    (
        "fig-fox",
        "The Clever Fox",
        "Forest Tales",
        [
            ("The Den", 412),
            ("A Long Winter", 388),
            ("The Frozen River", 501),
            ("Owl's Advice", 296),
            ("Across the Hills", 445),
            ("The Old Mill", 367),
            ("Home Again", 334),
            ("Goodnight Song", 182),
        ],
        "en",
    ),
    (
        "fig-moon",
        "Moon Songs",
        "Lullabies",
        [(f"Song {n}", 150 + 13 * n) for n in range(1, 13)],
        "en",
    ),
    (
        "fig-dragon",
        "Little Dragon",
        "Dragon Days",
        [
            ("The Egg", 610),
            ("First Flight", 584),
            ("A Cold Nose", 547),
            ("The Big Storm", 702),
            ("Friends", 498),
            ("Sleepy Dragon", 255),
        ],
        "de",
    ),
    (
        "fig-sea",
        "Sea Stories",
        "Harbour Friends",
        [("The Lighthouse", 720), ("Fog", 655), ("The Whale", 801), ("Low Tide", 590)],
        "en",
    ),
    (
        "fig-garden",
        "In the Garden",
        "Forest Tales",
        [("Seeds", 333), ("Rain", 281), ("Snails", 302), ("Harvest", 377), ("Bees", 255)],
        "en",
    ),
]
CREATIVE = [
    (
        "fig-grandma",
        "Grandma's Stories",
        [
            ("The Red Bicycle", 734.0),
            ("When I Was Little", 921.5),
            ("Songs from the Kitchen", 402.0),
            ("The Night Train", 655.0),
        ],
    ),
    ("fig-empty", "Creative figure", []),
]
DISC = ("fig-disc", "Bedtime Disc", [("Side A", 1260), ("Side B", 1185)])
COLOURS = {
    "fig-fox": ("#E07A3F", "F"),
    "fig-moon": ("#5B6FB5", "M"),
    "fig-dragon": ("#4C9A6A", "D"),
    "fig-sea": ("#2F8FB0", "S"),
    "fig-garden": ("#9A8B3C", "G"),
    "fig-grandma": ("#B5577A", "G"),
    "fig-empty": ("#8A8A8A", "C"),
    "fig-disc": ("#6E5BB5", "B"),
}


def picture_svg(figure_id: str) -> str:
    """A made-up picture of a figure: a letter on a coloured round."""
    colour, letter = COLOURS[figure_id]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">'
        f'<circle cx="48" cy="48" r="44" fill="{colour}"/>'
        '<text x="48" y="64" font-family="sans-serif" font-size="46" font-weight="700" '
        f'fill="#fff" text-anchor="middle">{letter}</text></svg>'
    )


def install() -> None:
    """Put the made-up cloud in place of the real one."""
    from custom_components import storybox_plus as integration
    from custom_components.storybox_plus import config_flow
    from custom_components.storybox_plus.cloud import (
        TOPIC_BATTERY,
        TOPIC_ONLINE,
        TOPIC_PLAYBACK,
        TOPIC_SLEEP_TIMER,
        TOPIC_VOLUME,
        Auth,
        Battery,
        Box,
        Chapter,
        CloudClient,
        Generation,
        Household,
        Playback,
        PushClient,
        PushEvent,
        SleepTimer,
        TokenSet,
        Tonie,
        TonieDetails,
        TonieKind,
        Volume,
    )

    base = os.environ["STORYBOX_DEMO_BASE"]

    def picture(figure_id: str) -> str:
        return f"{base}/local/storybox-demo/{figure_id}.svg"

    def chapters(items: list[tuple[str, float]], prefix: str) -> tuple[Chapter, ...]:
        return tuple(
            Chapter(id=f"{prefix}-{i}", title=title, seconds=seconds, file=f"{prefix}-file-{i}")
            for i, (title, seconds) in enumerate(items)
        )

    def bought_chapters(items: list[tuple[str, float]]) -> tuple[Chapter, ...]:
        # Chapters of bought figures have their position as ID, as the box tells them
        return tuple(
            Chapter(id=str(i), title=title, seconds=seconds)
            for i, (title, seconds) in enumerate(items)
        )

    creative: dict[str, Tonie] = {
        figure_id: Tonie(
            id=figure_id,
            household_id=HOUSEHOLD,
            kind=TonieKind.CREATIVE,
            name=name,
            image_url=picture(figure_id),
            chapters=chapters(items, figure_id),
            seconds_remaining=5400 - sum(s for _, s in items),
            chapters_remaining=99 - len(items),
        )
        for figure_id, name, items in CREATIVE
    }
    bought = [
        Tonie(
            id=figure_id,
            household_id=HOUSEHOLD,
            kind=TonieKind.CONTENT,
            name=name,
            series=series,
            image_url=picture(figure_id),
            language=language,
            # The bought figures are locked to the household, as in the real cloud
            locked=True,
            chapters=bought_chapters(items),
        )
        for figure_id, name, series, items, language in BOUGHT
    ]
    disc = Tonie(
        id=DISC[0],
        household_id=HOUSEHOLD,
        kind=TonieKind.DISC,
        name=DISC[1],
        image_url=picture(DISC[0]),
        chapters=bought_chapters(DISC[2]),
    )
    uploads: dict[str, tuple[str, int]] = {}

    class DemoAuth(Auth):
        """Hands out tokens without a login server."""

        async def _async_token_request(self, form: dict[str, str]) -> TokenSet:
            tokens = TokenSet(
                access_token="demo-access",
                refresh_token="demo-refresh",
                expires_at=time.time() + 3600,
                refresh_expires_at=None,
            )
            changed = tokens.refresh_token != self._refresh_token
            self._tokens = tokens
            self._refresh_token = tokens.refresh_token
            if changed and self._on_tokens is not None:
                self._on_tokens(tokens)
            return tokens

    class DemoClient(CloudClient):
        """Answers with the made-up household."""

        async def async_user_id(self) -> str:
            return USER_ID

        async def async_households(self) -> list[Household]:
            return [Household(HOUSEHOLD, "Home")]

        async def async_boxes(self, household_id: str) -> list[Box]:
            now = datetime.now(UTC)
            return [
                Box(
                    id=KIDS_BOX,
                    household_id=HOUSEHOLD,
                    name="Kids room",
                    mac=KIDS_MAC,
                    generation=Generation.TONIEBOX_2,
                    firmware="1.6.30",
                    placed_tonie_id="fig-fox",
                    max_volume=75,
                ),
                Box(
                    id=LIVING_BOX,
                    household_id=HOUSEHOLD,
                    name="Living room",
                    mac=None,
                    generation=Generation.CLASSIC,
                    last_seen=now - timedelta(hours=2, minutes=14),
                ),
            ]

        async def async_creative_tonies(self, household_id: str) -> list[Tonie]:
            return list(creative.values())

        async def async_creative_tonie(self, household_id: str, tonie_id: str) -> Tonie | None:
            tonie = creative.get(tonie_id)
            if tonie is not None and tonie.transcoding:
                # The cloud is done converting by the time the page asks again
                tonie = creative[tonie_id] = replace(
                    tonie,
                    transcoding=False,
                    chapters=tuple(replace(c, transcoding=False) for c in tonie.chapters),
                )
            return tonie

        async def async_content_tonies(self) -> list[Tonie]:
            return list(bought)

        async def async_content_tonie(self, household_id: str, tonie_id: str) -> Tonie | None:
            return next((t for t in bought if t.id == tonie_id), None)

        async def async_discs(self) -> list[Tonie]:
            return [disc]

        async def async_playback_info(
            self, box_id: str, tonie_id: str, content_version: int = 0
        ) -> TonieDetails | None:
            return None

        async def async_set_chapters(
            self, household_id: str, tonie_id: str, chapters: list[Chapter]
        ) -> Tonie | None:
            tonie = creative[tonie_id] = replace(
                creative[tonie_id],
                chapters=tuple(chapters),
                seconds_remaining=5400 - sum(c.seconds or 0 for c in chapters),
                chapters_remaining=99 - len(chapters),
            )
            return tonie

        async def async_upload_file(self, data: bytes, filename: str, content_type: str) -> str:
            file_id = f"upload-{len(uploads) + 1}"
            uploads[file_id] = (filename, len(data))
            return file_id

        async def async_add_chapter(
            self, household_id: str, tonie_id: str, title: str, file_id: str
        ) -> Tonie | None:
            tonie = creative[tonie_id]
            added = Chapter(id=file_id, title=title, seconds=60.0, transcoding=True, file=file_id)
            tonie = creative[tonie_id] = replace(
                tonie,
                chapters=(*tonie.chapters, added),
                transcoding=True,
                seconds_remaining=(tonie.seconds_remaining or 0) - 60,
                chapters_remaining=(tonie.chapters_remaining or 1) - 1,
            )
            return tonie

    class DemoPush(PushClient):
        """Reports a Toniebox 2 that plays the fox, and takes commands without a broker."""

        async def async_run(self) -> None:
            self._set_connected(True)
            now = datetime.now(UTC)
            for topic, data in (
                (TOPIC_ONLINE, True),
                (TOPIC_BATTERY, Battery(percent=64, charging=False, status="discharging")),
                (TOPIC_VOLUME, Volume(level=9)),
                (TOPIC_SLEEP_TIMER, SleepTimer(state="active", until=now + timedelta(minutes=35))),
                (
                    TOPIC_PLAYBACK,
                    Playback(
                        tonie_id="fig-fox",
                        chapter=2,
                        paused=False,
                        duration=501,
                        position=187,
                        content_version=1,
                        received_at=now,
                    ),
                ),
            ):
                self._on_event(PushEvent(KIDS_MAC, topic, data))
            await asyncio.Event().wait()

        async def async_command(self, mac: str, command: str, payload: dict[str, Any]) -> None:
            return None

    integration.Auth = DemoAuth  # type: ignore[misc]
    integration.CloudClient = DemoClient  # type: ignore[misc]
    integration.PushClient = DemoPush  # type: ignore[misc]
    config_flow.Auth = DemoAuth  # type: ignore[misc]
    config_flow.CloudClient = DemoClient  # type: ignore[misc]
