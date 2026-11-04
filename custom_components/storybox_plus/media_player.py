"""The Toniebox 2 as a media player: play, pause, volume, chapters and seeking."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerDeviceClass,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .cloud import VOLUME_LEVELS, CloudError, Playback
from .const import DOMAIN
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, async_follow_boxes

# Commands go one at a time to the cloud
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media players of the boxes that have the push channel."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        if not box_state.box.live:
            return []
        return [BoxPlayer(coordinator, box_state.box.id)]

    async_follow_boxes(entry, async_add_entities, _factory)


class BoxPlayer(BoxEntity, MediaPlayerEntity):
    """A Toniebox 2.

    The box plays whatever figure stands on it; Home Assistant cannot choose
    the figure, only pause, continue, change the volume and jump within it.
    """

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_media_content_type = MediaType.MUSIC
    _attr_media_image_remotely_accessible = False
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, None)

    @property
    def _playback(self) -> Playback | None:
        return self.box_state.playback if self.box_state else None

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
        tonie = self.coordinator.tonie(playback.tonie_id) if playback else None
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
        playback = self._playback
        tonie = self.coordinator.tonie(playback.tonie_id) if playback else None
        return tonie.name if tonie else None

    @property
    def media_artist(self) -> str | None:
        """Return the series of the figure."""
        playback = self._playback
        tonie = self.coordinator.tonie(playback.tonie_id) if playback else None
        return tonie.series if tonie else None

    @property
    def media_image_url(self) -> str | None:
        """Return the picture of the figure; Home Assistant serves it through its own proxy."""
        playback = self._playback
        tonie = self.coordinator.tonie(playback.tonie_id) if playback else None
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

    async def async_media_next_track(self) -> None:
        """Jump to the next chapter."""
        await self._jump_chapter(1)

    async def async_media_previous_track(self) -> None:
        """Jump to the start of the previous chapter."""
        await self._jump_chapter(-1)

    async def _jump_chapter(self, step: int) -> None:
        playback = self._playback
        if playback is None or playback.tonie_id is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="nothing_plays")
        chapter = max(0, (playback.chapter or 0) + step)
        tonie = self.coordinator.tonie(playback.tonie_id)
        if tonie is not None and tonie.chapters:
            chapter = min(chapter, len(tonie.chapters) - 1)
        await self._send(lambda mac: self.coordinator.push.async_set_position(mac, chapter, 0))
