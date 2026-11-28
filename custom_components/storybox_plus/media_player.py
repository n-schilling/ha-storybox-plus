"""The Toniebox 2 as a media player: play, pause, volume, chapters, seeking and sleep."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, time
from typing import Any

import probatio

from homeassistant.components.media_player import BrowseMedia, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import bedtime
from .cloud import SLEEP_TIMER_MAX_MINUTES, VOLUME_LEVELS, Alarm, CloudError, Playback, Tonie
from .const import (
    ATTR_CHAPTER,
    ATTR_DATETIME,
    ATTR_FAVOURITE,
    ATTR_MINUTES,
    ATTR_MORNING_LIGHT,
    ATTR_TIME,
    ATTR_TONE,
    ATTR_VOLUME,
    DOMAIN,
    SERVICE_CLEAR_SLEEP_TIMER,
    SERVICE_CLEAR_WAKE_UP_LIGHT,
    SERVICE_PLAY_FAVOURITE,
    SERVICE_SET_FAVOURITE,
    SERVICE_SET_SLEEP_TIMER,
    SERVICE_SET_WAKE_UP_LIGHT,
)
from .coordinator import BoxError, BoxState, ChapterError, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, async_follow_boxes

# Commands go one at a time to the cloud
PARALLEL_UPDATES = 1
# The media IDs of the chapters: chapter:<figure>:<index from 0>
CHAPTER_PREFIX = "chapter:"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media players of the boxes that have the push channel, and their actions."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        if not box_state.box.live:
            return []
        return [BoxPlayer(coordinator, box_state.box.id)]

    async_follow_boxes(entry, async_add_entities, _factory)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_SLEEP_TIMER,
        {
            probatio.Required(ATTR_MINUTES): probatio.All(
                probatio.Coerce(int), probatio.Range(min=1, max=SLEEP_TIMER_MAX_MINUTES)
            )
        },
        "async_set_sleep_timer",
    )
    platform.async_register_entity_service(
        SERVICE_CLEAR_SLEEP_TIMER, None, "async_clear_sleep_timer"
    )
    platform.async_register_entity_service(
        SERVICE_SET_FAVOURITE,
        {
            # The chapter counted from 1, as the media player counts its tracks
            probatio.Optional(ATTR_CHAPTER): probatio.All(
                probatio.Coerce(int), probatio.Range(min=1)
            ),
            probatio.Optional(ATTR_FAVOURITE): cv.boolean,
        },
        "async_set_favourite",
    )
    platform.async_register_entity_service(SERVICE_PLAY_FAVOURITE, None, "async_play_favourite")
    platform.async_register_entity_service(
        SERVICE_SET_WAKE_UP_LIGHT,
        probatio.All(
            cv.make_entity_service_schema(
                {
                    # Exactly one: a time of day (the next one) or a date with a time
                    probatio.Exclusive(ATTR_TIME, "when"): cv.time,
                    probatio.Exclusive(ATTR_DATETIME, "when"): cv.datetime,
                    probatio.Optional(ATTR_TONE, default=bedtime.TONE_NAMES[0]): probatio.In(
                        bedtime.TONE_NAMES
                    ),
                    probatio.Optional(ATTR_VOLUME, default=100): probatio.All(
                        probatio.Coerce(int), probatio.Range(min=0, max=100)
                    ),
                    probatio.Optional(ATTR_MORNING_LIGHT, default=True): cv.boolean,
                }
            ),
            cv.has_at_least_one_key(ATTR_TIME, ATTR_DATETIME),
        ),
        "async_set_wake_up_light",
    )
    platform.async_register_entity_service(
        SERVICE_CLEAR_WAKE_UP_LIGHT, None, "async_clear_wake_up_light"
    )


class BoxPlayer(BoxEntity, MediaPlayerEntity):
    """A Toniebox 2.

    The box plays whatever figure stands on it; Home Assistant cannot choose
    the figure, only pause, continue, change the volume, jump within it (also
    to a chapter picked from the media browser) and put the box to sleep.
    """

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_media_content_type = MediaType.MUSIC
    _attr_media_image_remotely_accessible = False
    _attr_name = None
    # The address of a picture is no history, nor are the names of the chapters
    _unrecorded_attributes = frozenset({"box_picture", "chapter_list"})
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, None)

    @property
    def _playback(self) -> Playback | None:
        return self.box_state.playback if self.box_state else None

    @property
    def _tonie(self) -> Tonie | None:
        """The figure on the box: the one the box reports, until then the one the cloud names."""
        box_state = self.box_state
        return self.coordinator.tonie(box_state.tonie_id) if box_state else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return what a dashboard shows beside the player: the box's picture, the chapters."""
        box_state = self.box_state
        tonie = self._tonie
        playback = self._playback
        favourite: bool | None = None
        # None while a Tune lies on the figure: the box plays the Tune then
        stars = self.coordinator.playing_stars(tonie)
        if stars is not None and playback is not None and playback.chapter is not None:
            favourite = playback.chapter in stars
        return {
            "box_picture": self.coordinator.box_picture(box_state.box) if box_state else None,
            "chapters": len(tonie.chapters) if tonie else None,
            # Whether the chapter that plays is a favourite; None while no chapter is known
            "favourite": favourite,
            # The figure on the box: its ID, as the media IDs of its chapters carry it
            # (chapter:<figure>:<index from 0>), and every chapter by name, length and star
            "tonie_id": tonie.id if tonie else None,
            "chapter_list": (
                [
                    {
                        "title": c.title or None,
                        "seconds": c.seconds,
                        "favourite": None if stars is None else i in stars,
                    }
                    for i, c in enumerate(tonie.chapters)
                ]
                if tonie
                else None
            ),
        }

    @property
    def state(self) -> MediaPlayerState | None:
        """Return what the box does."""
        box_state = self.box_state
        if box_state is None:
            return None
        if box_state.online is False:
            return MediaPlayerState.OFF
        playback = box_state.playback
        if playback is None or playback.tonie_id is None:
            return MediaPlayerState.IDLE if box_state.online else None
        if playback.playing:
            return MediaPlayerState.PLAYING
        if playback.paused:
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        """Return the volume as 0..1."""
        volume = self.box_state.volume if self.box_state else None
        return volume.fraction if volume else None

    @property
    def media_title(self) -> str | None:
        """Return the chapter that plays, or the figure if its chapters are unknown."""
        playback = self._playback
        tonie = self._tonie
        if tonie is None:
            return None
        if (
            playback
            and playback.chapter is not None
            and 0 <= playback.chapter < len(tonie.chapters)
        ):
            return tonie.chapters[playback.chapter].title or tonie.name
        return tonie.name

    @property
    def media_album_name(self) -> str | None:
        """Return the figure."""
        tonie = self._tonie
        return tonie.name if tonie else None

    @property
    def media_artist(self) -> str | None:
        """Return the series of the figure."""
        tonie = self._tonie
        return tonie.series if tonie else None

    @property
    def media_image_url(self) -> str | None:
        """Return the picture of the figure; Home Assistant serves it through its own proxy."""
        tonie = self._tonie
        return tonie.image_url if tonie else None

    @property
    def media_track(self) -> int | None:
        """Return the chapter number, counted from 1."""
        playback = self._playback
        return playback.chapter + 1 if playback and playback.chapter is not None else None

    @property
    def media_duration(self) -> int | None:
        """Return the length of the chapter."""
        playback = self._playback
        return int(playback.duration) if playback and playback.duration is not None else None

    @property
    def media_position(self) -> int | None:
        """Return the position in the chapter when the box last reported."""
        playback = self._playback
        return int(playback.position) if playback and playback.position is not None else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the position was reported."""
        playback = self._playback
        return playback.received_at if playback and playback.position is not None else None

    # ------------------------------------------------------------ commands

    async def _send(self, command: Callable[[str], Awaitable[None]]) -> None:
        box_state = self.box_state
        if box_state is None or box_state.box.mac is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="box_unknown")
        try:
            await command(box_state.box.mac)
        except CloudError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_media_play(self) -> None:
        """Continue playing the figure on the box."""
        await self._send(self.coordinator.push.async_play)

    async def async_media_pause(self) -> None:
        """Pause."""
        await self._send(self.coordinator.push.async_pause)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume; the box knows 13 levels."""
        level = round(max(0.0, min(1.0, volume)) * VOLUME_LEVELS)
        await self._send(lambda mac: self.coordinator.push.async_set_volume(mac, level))

    async def async_volume_up(self) -> None:
        """One level louder."""
        await self._step_volume(1)

    async def async_volume_down(self) -> None:
        """One level quieter."""
        await self._step_volume(-1)

    async def _step_volume(self, step: int) -> None:
        volume = self.box_state.volume if self.box_state else None
        if volume is None or volume.level is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="volume_unknown")
        level = max(0, min(VOLUME_LEVELS, volume.level + step))
        await self._send(lambda mac: self.coordinator.push.async_set_volume(mac, level))

    async def async_media_seek(self, position: float) -> None:
        """Jump to a position within the current chapter."""
        playback = self._playback
        if playback is None or playback.tonie_id is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="nothing_plays")
        chapter = playback.chapter or 0
        await self._send(
            lambda mac: self.coordinator.push.async_set_position(
                mac, chapter, int(max(0.0, position) * 1000)
            )
        )

    @property
    def repeat(self) -> RepeatMode:
        """The repeat of the figure on the box."""
        mode = self.coordinator.repeat_mode(self._box_id)
        return RepeatMode(mode) if mode else RepeatMode.OFF

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Let the figure repeat, or one chapter of it, or end the repeat."""
        try:
            self.coordinator.set_repeat(
                self._box_id,
                "all" if repeat is RepeatMode.ALL else "one" if repeat is RepeatMode.ONE else None,
            )
        except BoxError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="nothing_plays"
            ) from err

    async def async_media_next_track(self) -> None:
        """Jump to the next chapter."""
        await self._jump_chapter(1)

    async def async_media_previous_track(self) -> None:
        """Jump to the start of the previous chapter."""
        await self._jump_chapter(-1)

    async def _jump_chapter(self, step: int) -> None:
        box_state = self.box_state
        try:
            if box_state is None:
                raise BoxError("nothing_plays")
            chapter = self.coordinator.chapter_step(box_state, step)
        except BoxError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="nothing_plays"
            ) from err
        await self._send_to_chapter(box_state, chapter)

    async def _send_to_chapter(self, box_state: BoxState, chapter: int) -> None:
        """Send the box to the start of a chapter the favourites were told of."""
        try:
            await self._send(lambda mac: self.coordinator.push.async_set_position(mac, chapter, 0))
        except HomeAssistantError:
            # It did not reach the box: the chapter is not the chosen one any more
            self.coordinator.chapter_unchosen(box_state, chapter)
            raise

    def _refuse_if_alarm(self) -> None:
        """Refuse a command that would replace the alarm of a bedtime or the wake-up light.

        The box keeps one timer; the sleep timer and putting the box to sleep
        would cancel the alarm the integration arms for the next wake-up.
        """
        alarm = self.coordinator.due_alarm(self._box_id)
        if alarm is not None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_due",
                translation_placeholders={"time": alarm.at.strftime("%H:%M")},
            )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """List the chapters of the figure on the box; each can be played from its start."""
        tonie = self._tonie
        if tonie is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="nothing_plays")
        return BrowseMedia(
            media_class=MediaClass.ALBUM,
            media_content_id=f"{CHAPTER_PREFIX}{tonie.id}",
            media_content_type=MediaType.ALBUM,
            title=tonie.name,
            can_play=False,
            can_expand=True,
            thumbnail=tonie.image_url,
            children_media_class=MediaClass.TRACK,
            children=[
                BrowseMedia(
                    media_class=MediaClass.TRACK,
                    media_content_id=f"{CHAPTER_PREFIX}{tonie.id}:{index}",
                    media_content_type=MediaType.TRACK,
                    title=f"{index + 1}. {chapter.title}" if chapter.title else str(index + 1),
                    can_play=True,
                    can_expand=False,
                )
                for index, chapter in enumerate(tonie.chapters)
            ],
        )

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a chapter of the figure on the box from its start.

        The ID names the figure and the chapter (``chapter:<figure>:<index>``,
        as browsing hands it out), so a chapter of a figure that was taken off
        meanwhile is refused instead of playing another figure's chapter.
        """
        figure, _, index = media_id.removeprefix(CHAPTER_PREFIX).rpartition(":")
        if not media_id.startswith(CHAPTER_PREFIX) or not index.isdigit():
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_chapter"
            )
        # Before the box itself reports, the figure the cloud names counts
        box_state = self.box_state
        if box_state is None or box_state.tonie_id is None or box_state.tonie_id != figure:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="other_figure")
        chapter = int(index)
        tonie = self.coordinator.tonie(figure)
        if tonie is not None and tonie.chapters and chapter >= len(tonie.chapters):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_chapter"
            )
        self.coordinator.chapter_chosen(box_state, chapter)
        await self._send_to_chapter(box_state, chapter)

    async def async_turn_off(self) -> None:
        """Put the box to sleep; the cloud cannot wake it again."""
        self._refuse_if_alarm()
        await self._send(self.coordinator.push.async_sleep)

    async def async_set_sleep_timer(self, minutes: int) -> None:
        """Let the box fall asleep after the given minutes."""
        self._refuse_if_alarm()
        await self._send(lambda mac: self.coordinator.push.async_set_sleep_timer(mac, minutes * 60))

    async def async_set_favourite(
        self, chapter: int | None = None, favourite: bool | None = None
    ) -> None:
        """Mark a chapter of the figure on the box as a favourite, or take the star off.

        Without a chapter the one that plays; without ``favourite`` the star
        changes sides.
        """
        tonie = self._tonie
        playback = self._playback
        if tonie is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="nothing_plays")
        if self.coordinator.tune_on(tonie.id) is not None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="tune_plays")
        index = chapter - 1 if chapter is not None else playback.chapter if playback else None
        try:
            if index is None:
                raise ChapterError("unknown_chapter")
            await self.coordinator.async_star(tonie.id, index, favourite)
        except ChapterError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_chapter"
            ) from err

    async def async_play_favourite(self) -> None:
        """Play the next favourite chapter of the figure on the box; after the last, the first."""
        try:
            await self.coordinator.async_play_favourite(self._box_id)
        except BoxError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=(
                    err.code if err.code in ("no_favourites", "tune_plays") else "nothing_plays"
                ),
            ) from err
        except CloudError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_set_wake_up_light(
        self,
        tone: str,
        volume: int,
        morning_light: bool,
        time: time | None = None,
        datetime: datetime | None = None,
    ) -> None:
        """Set the wake-up light: one alarm at that time, in the box's own time zone."""
        box_state = self.box_state
        if box_state is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="box_unknown")
        now = self.coordinator.now_at(box_state.box)
        if time is not None:
            at = bedtime.next_at(time, now)
        elif datetime is not None:
            at = datetime if datetime.tzinfo else datetime.replace(tzinfo=now.tzinfo)
        else:  # pragma: no cover - the schema asks for one of them
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="alarm_past")
        alarm = Alarm(bedtime.TONE_BY_NAME[tone], volume, morning_light)
        try:
            await self.coordinator.async_set_wake_up_light(self._box_id, at, alarm)
        except BoxError as err:
            if err.code != "alarm_past":
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="no_alarm"
                ) from err
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_past",
                translation_placeholders={"time": at.strftime("%Y-%m-%d %H:%M")},
            ) from err

    async def async_clear_wake_up_light(self) -> None:
        """Drop the wake-up light, and its alarm on the box if armed."""
        try:
            await self.coordinator.async_clear_wake_up_light(self._box_id)
        except BoxError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_alarm"
            ) from err

    async def async_clear_sleep_timer(self) -> None:
        """Cancel the sleep timer."""
        self._refuse_if_alarm()
        await self._send(self.coordinator.push.async_clear_sleep_timer)
