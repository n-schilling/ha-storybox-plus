# Storybox Plus: automations and interface

Example automations, and what automations, dashboards and scripts may build on. Back to the [README](../README.md).

## Examples

Pause the box in the children's room with the bedtime scene:

```yaml
triggers:
  # A scene's state is the time it was last activated
  - trigger: state
    entity_id: scene.bedtime
    not_to: unavailable
actions:
  - action: media_player.media_pause
    target:
      entity_id: media_player.kids_room
```

A 45-minute sleep timer when the bedtime figure is placed, cancelled when a figure is taken off:

```yaml
triggers:
  - trigger: state
    entity_id: event.kids_room_figure
actions:
  - choose:
      - conditions:
          - "{{ trigger.to_state.attributes.event_type == 'placed' and trigger.to_state.attributes.tonie_id == 'ID OF THE FIGURE' }}"
        sequence:
          - action: storybox_plus.set_sleep_timer
            target:
              entity_id: media_player.kids_room
            data:
              minutes: 45
      - conditions:
          - "{{ trigger.to_state.attributes.event_type == 'removed' }}"
        sequence:
          - action: storybox_plus.clear_sleep_timer
            target:
              entity_id: media_player.kids_room
```

A notification when the battery runs low and the box is not on the charger:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.kids_room_battery
    below: 15
conditions:
  - condition: state
    entity_id: binary_sensor.kids_room_charging
    state: "off"
actions:
  - action: notify.notify
    data:
      message: "The box in the kids' room needs charging."
```

A greeting spoken onto a creative figure every evening, replacing yesterday's; with the figure's live mode on (on the page), it plays first when the figure is placed:

```yaml
triggers:
  - trigger: time
    at: "18:30:00"
actions:
  - action: storybox_plus.add_chapter
    data:
      figure: Grandma's greetings
      text: "Good night, sleep well. Tomorrow we go to the zoo!"
      title: Good night
      replace: true
```

A lower maximum volume while guests sleep over, back to normal afterwards:

```yaml
triggers:
  - trigger: state
    entity_id: input_boolean.guests
actions:
  - action: storybox_plus.set_box_settings
    target:
      entity_id: media_player.kids_room
    data:
      max_volume: "{{ 40 if trigger.to_state.state == 'on' else 75 }}"
```

## Interface

What automations and dashboards can build on. `tests/test_contract.py` pins it: the entities with their IDs and keys, the attributes, the events with their data, the actions, the names of the commands and the stores.

### Entities

IDs as created in English, for a box named "Kids room". Every unique ID starts with the config entry (`<entry>`), and a box's device is `(storybox_plus, <entry>_<box>)` with the box's ID from the cloud: members of one household who each add their own account get a device of the shared box per account instead of a collision.

| Entity | Unique ID | Boxes | State |
|---|---|---|---|
| `binary_sensor.kids_room_connectivity` | `<entry>_<box>_connectivity` | Toniebox 2 | connected to the cloud; unknown while nothing tells |
| `sensor.kids_room_battery` | `<entry>_<box>_battery` | Toniebox 2 | battery in percent; unavailable while the box is switched off |
| `binary_sensor.kids_room_charging` | `<entry>_<box>_charging` | Toniebox 2 | charging |
| `binary_sensor.kids_room_headphones` | `<entry>_<box>_headphones` | Toniebox 2 | headphones are connected, with the attributes `kind` (as the box names it, `bluetooth` for example) and `battery` (percent, of wireless ones); unknown until the box says, unavailable while the box is switched off |
| `binary_sensor.kids_room_night_mode` | `<entry>_<box>_night_mode` | Toniebox 2 | the [night mode of the light ring](features.md#night-mode-of-the-light-ring) is at work: switched on and within its span |
| `sensor.kids_room_sleep_timer` | `<entry>_<box>_sleep_timer` | Toniebox 2 | when the running sleep timer ends (a timestamp); unknown while none runs. The timer that carries a bedtime's alarm is not one |
| `sensor.kids_room_next_alarm` | `<entry>_<box>_next_alarm` | Toniebox 2 that rings alarms | when the next alarm of the [bedtimes](features.md#bedtimes-and-the-alarm) rings (a timestamp); unknown without one. The attribute `due` is true while the alarm is close enough for the box's timer to carry it: a sleep timer is refused then |
| `sensor.<account>_tonieboxes_2` | `<entry>_boxes` | the account's device | how many Tonieboxes 2 the account has; the attribute `boxes` lists them for dashboards, each with `name` (as in Home Assistant), `entity_id` (its media player) and `picture`. The attribute is not recorded |
| `binary_sensor.<account>_live_channel` | `<entry>_live_channel` | the account's device, with a Toniebox 2 | the push channel is connected; live state and commands of every Toniebox 2 go through it |
| `media_player.kids_room` | `<entry>_<box>` | Toniebox 2 | `playing`, `paused`, `idle` (no figure), `off` (switched off) with figure, chapter, picture, position and length, and the attributes `chapters` (how many the figure has), `favourite` (whether the chapter that plays is a favourite), `tonie_id` and `chapter_list` (the figure on the box and its chapters by name, length and star; not recorded) and `box_picture` (the address of the box's picture) |
| `event.kids_room_figure` | `<entry>_<box>_figure` | Toniebox 2 | event types `placed`, `removed` with `tonie_id` and `tonie` (name) |
| `event.<account>_cloud_notification` | `<entry>_notification` | the account's device | event type `notification` with `kind` (the cloud's type, `system` for a broadcast), `text`, `time`, `tonie_id`, `tonie`, `reason` (why a conversion failed) |

The media player takes play, pause, volume (13 levels), next and previous chapter, repeat (the whole figure or one chapter, see [Repeat](features.md#repeat)), seeking within the chapter, playing a chapter of the figure on the box picked from the media browser (`media_player.play_media` with `chapter:<figure>:<index from 0>`; a chapter of another figure is refused), and turning off, which puts the box to sleep as the app's sleep button does; the cloud cannot wake it again.

### Actions

| Action | Fields | Description |
|---|---|---|
| `storybox_plus.set_sleep_timer` | `minutes` (1 to 1092) | the box falls asleep on its own after that time; a running timer is replaced |
| `storybox_plus.clear_sleep_timer` | none | cancels the running timer |
| `storybox_plus.set_favourite` | optional `chapter` (counted from 1; none: the one that plays), optional `favourite` (none: the star changes sides) | marks a chapter of the figure on the box as a favourite, or takes its star off |
| `storybox_plus.play_favourite` | none | plays the next favourite of the figure on the box; after the last one, the first |

All target the media player of a Toniebox 2 and may be called by every user. While the alarm of a bedtime is due, the two of the sleep timer and turning the media player off are refused, because each would replace the alarm.

#### Actions for automations

> [!NOTE]
> These four actions are meant for **automations and scripts** only: for what should happen on its own, at a time or on an event. To change chapters or settings by hand, the **Storybox Plus page** in the sidebar is the easy way: it shows the figure, says what will happen, asks before anything is lost and gathers several changes into one. Everything the actions do, the page does too.

They are for administrators; automations and scripts may call them. Figures have no entities, so the three chapter actions name a creative figure by its **name** as the page shows it (any case) or by its **ID**; a name two creative figures share is refused, use the ID then. Each answers, when asked for a response, with the figure: `figure` (its name), `id`, `chapters` (the titles in their order) and `minutes_free`. Every change of chapters makes the cloud convert the figure anew, as on the page; a box downloads it again the next time the figure is placed.

| Action | Fields | Description |
|---|---|---|
| `storybox_plus.add_chapter` | `figure`; exactly one source: `media` (from the media selector: a file of a media folder, a text spoken by a speech entity, or another media source that gives a web address; up to 200 MB), `text` (up to 5000 characters, spoken by the voice chosen on the page) or `url` (a video link, fetched by the Media Fetcher app); optional `title` (else the file name, the first words of the text or the video's title), optional `replace` (default off) | appends a chapter to a creative figure. With `replace`, the chapters with the same title are removed afterwards, so a daily greeting does not pile up; for a moment the figure needs room for both. A link waits until the video is fetched, which can take minutes |
| `storybox_plus.remove_chapters` | `figure`; either `title` (every chapter with this title, any case) or `keep_last` (keeps that many chapters at the end of the list, 0 removes all) | removes chapters of a creative figure. The audio is gone: the cloud keeps no copy. Nothing to remove asks the cloud nothing |
| `storybox_plus.shuffle_chapters` | `figure` | puts the chapters of a creative figure (at least two) into a new random order |
| `storybox_plus.set_box_settings` | target: the media player of one or more Tonieboxes 2; any of `max_volume`, `max_headphone_volume`, `bedtime_max_volume`, `bedtime_max_headphone_volume` (1 to 100), `lightring_brightness`, `bedtime_lightring_brightness` (0 to 100), `skipping_enabled`, `skipping_direction` (`left`, `right`), `scrubbing_enabled` | changes the settings given, as the save button on the page does; the others stay. The box takes them when it is online; the page's note that the box waits ends as soon as it reports them taken |

The page offers these as ready-made snippets: a figure and a Toniebox 2 have a view **Automations** with automations that already carry the figure's ID and the boxes' entities (a figure placed starts a sleep timer, repeats, pauses late in the evening or writes a note; for a creative figure also a greeting every evening, shuffling every morning and tidying up every week; for a box quieter evenings, a sleep timer every evening and a note when the battery runs low). Each is copied with one button; **New automation** opens Home Assistant's editor, where it is pasted with **Edit in YAML**. Home Assistant gives an integration no way to open its editor with content, so the snippet goes through the clipboard, and nothing runs before the automation is saved.

A refused call says why: an unknown or ambiguous figure, a figure that is no creative one, a Tune lying on it, a text without a voice, a link without the Media Fetcher app, media that cannot be read, a setting the box does not have.

### WebSocket commands

For administrators only; the page uses them. Their answers serve the page and are not part of this interface. The dashboard card uses none of them: it reads entities.

| Command | Parameters |
|---|---|
| `storybox_plus/overview` | none; boxes with their live state, the version, and per account the Piper entity that speaks while none is chosen (`speech_auto`) |
| `storybox_plus/library` | none; households and figures with chapters and favourites, the bought Tunes, whether links can be fetched and whether a voice can speak |
| `storybox_plus/analytics` | `days` (or none for all), `limit` |
| `storybox_plus/chapters/arrange` | `tonie_id`, `chapters` (IDs in the new order; the rest is removed), optional `titles` (chapter ID → new name) |
| `storybox_plus/chapters/add_text` | `tonie_id`, `text` (up to 5000 characters), optional `title` (else the first words); the account's voice speaks it |
| `storybox_plus/chapters/add` | `tonie_id`, `file_id` (from `/api/file_upload`), optional `title` |
| `storybox_plus/chapters/add_link` | `tonie_id`, `url`; a subscription that reports the stages |
| `storybox_plus/favourites/set` | `tonie_id`, optional `chapters` (positions from 0; without them the stars stay and only the mode changes), `mode` (`first`, `random`, `only`, `bedtime`, `off`, or null for the account's mode) |
| `storybox_plus/favourites/star` | `tonie_id`, `chapter` (position from 0), optional `favourite` (none: the star changes sides) |
| `storybox_plus/box/favourites` | `box_id` (a Toniebox 2 with a figure on it), `suspended` (true: every chapter plays until the figure is taken off); answers with the box |
| `storybox_plus/figure/refresh` | `tonie_id` |
| `storybox_plus/figure/update` | `tonie_id` (a creative figure) and `name` and/or `live` |
| `storybox_plus/figure/shuffle_on_swap` | `tonie_id` (a creative figure), `enabled` |
| `storybox_plus/household/rename` | `household_id`, `name`; answers with the entry's title |
| `storybox_plus/figure/tune` | `tonie_id`, `tune_id` (from the library's `tunes`, or null to take the Tune off); answers with the Tunes and the figure |
| `storybox_plus/box/command` | `box_id` (a Toniebox 2), `command` (`play`, `pause`, `next`, `previous`, `chapter` with `value` as its index from 0 and optionally `tonie_id`, the figure it is meant for, `volume` with `value` 0 to 13, `sleep` with `value` in minutes, `sleep_clear`) |
| `storybox_plus/box/repeat` | `box_id` (a Toniebox 2 with a figure on it), `mode` (`all`, `one` or null for off); answers with the box |
| `storybox_plus/voucher/redeem` | `entry_id`, `code`; answers with how many Tunes it brought and the Tunes |
| `storybox_plus/figure/redeem_token` | `tonie_id` (a creative figure), `token`; answers with the figure |
| `storybox_plus/figure/lock` | `tonie_id` (a bought figure or disc), `locked` |
| `storybox_plus/cloud/check` | `entry_id`; reads everything the integration reads and answers with what differs from the fields it relies on (per request `ok`, `changed`, `failed`, `empty`, `unseen`) |
| `storybox_plus/preferences/set` | `entry_id` and any of `analytics`, `auto_lock`, `mark_read`, `analytics_days` (365, 730, 1825 or 0 for always), `speech_engine` (a `tts` entity; null: Piper), `voice` with `voice_language` (null: the engine's default), `fetch_max_mb` (10–2000), `favourites_mode` (`first`, `random`, `only`, `bedtime`, `off`); switching `analytics` sets the account up anew |
| `storybox_plus/log` | optional `limit`; the log level, the days kept and the latest lines, newest first (without a limit, all lines kept) |
| `storybox_plus/log/set` | any of `level` (`debug`, `info`, `warning`, `error`), `days` (0–90) |
| `storybox_plus/figure/volume` | `tonie_id`, `level` (1 to 13, or null for the box's own volume) |
| `storybox_plus/bedtime/save` | `box_id`, optional `schedule_id` (none: a new bedtime, which needs `sleep_time`, `wakeup_time`, `days`), `name`, `sleep_time` and `wakeup_time` (`HH:MM`), `days` (`monday` … `sunday`), `enabled`, `alarm_enabled`, `alarm_volume` (0 to 100), `alarm_morning_light`; answers with the box |
| `storybox_plus/bedtime/delete` | `box_id`, `schedule_id`; answers with the box |
| `storybox_plus/night/set` | `box_id`, `enabled`, `start` and `end` (`HH:MM`, not the same), `night` and `day` (0 to 100); a Toniebox 2 only; answers with the box |
| `storybox_plus/box/settings` | `box_id` and any of `name`, `max_volume`, `max_headphone_volume` (1 to 100; a Toniebox 1 only 25, 50, 75, 100), `lightring_brightness`, `bedtime_lightring_brightness` (0 to 100), `bedtime_max_volume`, `bedtime_max_headphone_volume` (1 to 100), `skipping_enabled`, `skipping_direction` and `tap_direction` (`left`, `right`), `scrubbing_enabled`, `accelerometer_enabled`, `led_level` (`on`, `dimmed`, `off`), `age_mode`, `language`; a setting the box does not have is refused; answers with the box; for a Toniebox 1 also `presence_entity` (a `device_tracker` or `binary_sensor` entity, or null) and `presence_lag` (minutes, 0 to 120), both kept in Home Assistant only |

### Stores

`.storage/storybox_plus.<entry>.analytics` (daily sums per figure and box, per chapter, per hour), `.battery` (charges), `.chapters` (chapters learned from the boxes), `.favourites` (the stars and own mode per figure, and what each box plays of its figure), `.night` (night modes with the phase set last), `.volumes` (levels per figure and the levels to restore per box), `.notices` (the cloud's notifications passed on), `.settings` (the preferences and the figures looked at for locking) and `.shuffle` (the figures shuffled on swap and the last figure per box), version 1 each. Deleting the entry deletes them.
