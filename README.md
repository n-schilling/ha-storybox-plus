# Storybox Plus

[![Marketplace: custom](https://img.shields.io/badge/Marketplace-custom-41BDF5.svg)](#installation)
![Tested with cloud backend v2026.11.10](https://img.shields.io/badge/cloud%20backend-v2026.11.10-informational.svg)

A Home Assistant integration for the Toniebox. Every box becomes a device with the few entities automations need: is it online, how full is the battery, what plays, which figure was placed. The library of figures, their chapters, the listening times and how long a charge lasts live on a page in the sidebar, for administrators. The integration talks to the manufacturer's cloud, because the boxes have no local interface.

What it is for, for example:

- a sleep timer of 45 minutes as soon as the bedtime figure is placed;
- bedtimes with an alarm that rings on the chosen days: Home Assistant sets it on the box every evening, which the app does only once;
- the bedtime scene pauses the box in the children's room;
- a notification when the battery of the box runs low, or a dashboard card with what plays;
- favourite chapters: the box skips the chapters nobody wants to hear;
- chapters of a creative figure uploaded, rearranged and removed from Home Assistant, also from a video link;
- the settings of a box, such as its name, maximum volume, light ring and tapping, changed on the page;
- a night mode for the light ring: dimmed from evening to morning, back to its normal brightness afterwards;
- a volume of its own per figure, for the loud one and the quiet one; the box's level comes back when it is taken off;
- any chapter of the figure on the box played from the media browser of a dashboard;
- the notifications the app keeps, for example a chapter that could not be converted, passed on to Home Assistant, and marked as read there if wanted;
- new bought figures and discs locked to the household on their own, so nobody claims them into another one;
- bought Tunes laid on a figure that fits and taken off again;
- how much was listened to, per figure, per chapter and per day, and when: per weekday and hour;
- playing, pausing, skipping, the volume and the sleep timer of a Toniebox 2 right on its card, and its headphones shown;
- Tunes vouchers redeemed and ready-made content put on a creative figure from a code.

This project is not affiliated with or endorsed by tonies GmbH. "Toniebox" and "Tonie" are their trademarks and are used here only to name the devices.

## Screenshots

The boxes with their live state; the Toniebox 2 with its bedtimes, its battery and the charge history, made up for these pictures:

<img src="docs/screenshots/boxes.png" alt="Boxes tab with the header row of icon, name and tabs, the stamp, refresh and settings buttons: a Toniebox 2 playing chapter 3 of a figure, with volume, two bedtimes and the next alarm set on the box, and its battery; beside it a Toniebox 1 as a small card with its settings in a line, last seen two hours ago" width="700">

The dashboard card of a Toniebox 2, here seen by a user without administrator rights:

<img src="docs/screenshots/card.png" alt="The dashboard card of a Toniebox 2: name, online dot and battery in the head, volume, headphones and the next alarm, the figure that plays with its chapter and progress, and the buttons" width="450">

The settings of a Toniebox 2 being changed; a Toniebox 1 shows its own:

<img src="docs/screenshots/settings.png" alt="The settings form of a Toniebox 2: name, maximum volumes, light ring brightness, the limits at bedtime, skipping by tapping with its ear and winding by tilting" width="400">

The night mode of the light ring being set up:

<img src="docs/screenshots/night.png" alt="The night mode form: active, from 19:00 until 07:00, light ring at night 10 percent, otherwise 60 percent" width="400">

The settings tab of an account:

<img src="docs/screenshots/preferences.png" alt="Settings tab: the household with its members, lock new figures and discs, mark notifications as read in the cloud, and the cloud's backend version marked as tested" width="700">

A new bedtime with its days, times and alarm:

<img src="docs/screenshots/bedtime.png" alt="The bedtimes of a Toniebox 2 with the form for a new one: name, days of the wake-up, bedtime and wake-up time, switches for active, alarm and morning light, and the alarm volume" width="400">

The figures of the household; a bought figure opened, with its favourite chapters and the switch that steers the box:

<img src="docs/screenshots/figures.png" alt="Figures tab: a bought figure with eight chapters, four of them starred, and the favourites switch on" width="700">

A creative figure being renamed and rearranged, sorted by title or shuffled; the changes go to the cloud together when saved:

<img src="docs/screenshots/creative.png" alt="A creative figure in edit mode with its name, buttons to sort by title and shuffle, and buttons to move and remove chapters" width="700">

The listening times of the last 30 days, counted by Home Assistant:

<img src="docs/screenshots/listening.png" alt="Listening tab: note where the numbers come from, total, most played figures, chart per day and sums per box" width="700">

The boxes at phone width in dark mode:

<img src="docs/screenshots/boxes-phone-dark.png" alt="Boxes tab at phone width in dark mode, with the tabs at the bottom" width="300">

## Design

### Overview

```mermaid
flowchart LR
    admin(["Administrator"]) -->|"page, admin only"| ws["WebSocket commands"]
    subgraph cloud["Manufacturer's cloud"]
        rest["REST and GraphQL<br/>every 5 minutes"]
        push["Push channel<br/>MQTT over WebSocket"]
    end
    fetcher["Media Fetcher app<br/>(optional)"]
    subgraph sp["Storybox Plus"]
        coordinator["Coordinator<br/>boxes, figures, live state"]
        stores[("Stores<br/>listening, battery,<br/>chapters, favourites,<br/>night modes")]
        ws --> coordinator
        coordinator <--> stores
    end
    rest --> coordinator
    push --> coordinator
    coordinator -->|"favourites, sleep timer,<br/>alarm, player commands"| push
    coordinator -->|"chapters, box settings,<br/>night mode, bedtimes"| rest
    fetcher -->|"audio of a link"| coordinator
    coordinator --> entities["Entities per box<br/>connectivity, battery,<br/>media player, figure event"]
    entities --> automations["Your automations"]
```

The REST API is read every 5 minutes: households, boxes, figures and chapters, and when the Toniebox 1 was last seen. A Toniebox 2 reports live through the push channel: online state, battery, playback, volume, sleep timer. Everything to the right of the entities is up to your automations.

### Boxes

| Device | What Home Assistant gets |
|---|---|
| Toniebox 2 | online state, battery, charging, media player, figure event, listening times, battery cycles, favourite chapters |
| Toniebox 1 | no entities: the Toniebox 1 reports nothing live to the cloud, not even whether it is online; nothing is simulated or guessed. Its settings are on the page. |

Both generations can be mixed in one account. Figures (bought figures, creative figures, discs) belong to the household, not to a box; the page shows them that way.

Members of one household may each add their own account. Every account then gets its own device and entities of the shared boxes; the page shows a shared box or figure once, through the account added first, and only that account counts its listening time.

A single failed poll keeps the last values; after three failed polls in a row the entities become unavailable and recover with the next successful poll. The push channel is reconnected whenever the cloud drops it; a message it cannot read is logged and skipped. A box that is missing from the account for an hour of polls loses its device and entities; a box that comes back gets them anew.

### Figures and chapters

The cloud names the chapters of bought figures but not their lengths; the lengths are learned from a Toniebox 2 the first time the figure plays on it, and kept. A box that knows nothing yet is asked again an hour later or when the figure is placed anew. Creative figures are always shown as the cloud describes them.

The chapters of a creative figure are changed on the page: audio files are uploaded as new chapters, and in the edit mode chapters are moved and removed. All changes go to the cloud together when saved, because every change makes the cloud convert the figure anew and a box download it again. While the cloud converts, the page reads the figure again every 15 seconds; chapters the cloud dropped (unsupported format, more than 90 minutes in total) are named.

A chapter can also come from a video link: the page takes the link, the Media Fetcher app fetches the audio, and the integration uploads it as a chapter named after the video while the page shows the progress.

```mermaid
sequenceDiagram
    participant Page
    participant SP as Storybox Plus
    participant App as Media Fetcher app
    participant Cloud
    Page->>SP: chapters/add_link (figure, link)
    SP->>SP: http or https with a host?
    SP->>App: info
    App-->>SP: title, length
    SP->>SP: fits the figure's free time?
    SP->>App: job (audio, M4A, at most the free time)
    loop every second
        SP->>App: job state
        SP-->>Page: download / convert, with progress
    end
    SP->>App: file (at most 200 MB)
    SP->>Cloud: upload, add chapter
    SP->>App: forget the job
    SP-->>Page: done, the figure as the cloud has it
```

A link that is no web address, or a video longer than the figure's free time, is refused before anything is fetched; playlists are not taken, one video at a time. Closing the page gives up a running fetch; reloading the integration ends it and tells the page.

Each chapter is renamed in the edit mode too (the pencil on its row); a new name converts nothing. Creative figures are renamed in the same edit mode, where also the app's **live mode** lives: the newest chapter plays first when the figure is placed, made for greetings such as a good-night message from a grandparent. Neither makes the cloud convert anything, so they go first and the chapters only when they changed. Sorting by title and shuffling rearrange the list in the edit mode, saved like moving by hand. **Remove all chapters** asks twice before it empties the list: whether all of them should go, and whether the audio files are kept somewhere else, because the cloud keeps no copy once the change is saved. Until saved, cancelling brings them back. Bought figures and discs keep the names they came with.

#### Shuffle on swap

A creative figure with several chapters can be shuffled whenever another figure replaces it on a Toniebox 2: its switch on the figures tab. Only a replacement counts: taken off and put back, the figure keeps where it was. The box reports an empty spot between two figures; the integration keeps the last figure per box across it, also in its store, so a restart in between loses nothing. A figure that stands on another box by then, or that a Tune lies on, is left alone. Every shuffle makes the cloud convert the figure anew, as rearranging by hand does.

### Tunes

Tunes are audio plays bought in the app that can be laid on fitting figures: the bought figures the cloud names as compatible, and every creative figure when the Tune fits them all. The page lists them per figure: one that lies on it, with a button to take it off, or the bought ones that fit, to lay one on. While a Tune lies on a creative figure, the figure keeps its own chapters; taken off, they play again. How often a Tune may still be laid on, the cloud decides; the page shows it.

### Volume per figure

Every figure can carry a volume level of its own (1 to 13, the box's steps), set on its page entry. When it is placed on a Toniebox 2, the integration remembers the level the box had and sets the figure's; taken off or replaced, the box gets the remembered level back exactly, whatever was turned at the box in between. A figure placed right after another one with a level starts from the level before that one, so a chain of figures never drifts. A level changed while the figure stands on a box applies at once.

The remembered levels live in the store, so a restart in between still restores them. As long as the box has not reported its level (right after the push channel came up), a figure's level is not set, because it could not be undone. Like everything live, it goes through the cloud: the first second of the figure plays at the old level.

### Notifications of the cloud

The cloud keeps notifications for the account that only the app shows: a chapter of a creative figure that could not be converted, an invitation to a household, news. Storybox Plus reads them with every poll and fires each unread one once on an event entity of the account (`event.<account>_cloud_notification`); an automation decides where it goes. The cloud's broadcasts to all users count the same. Which ones were passed on is kept in the store, so a restart repeats none. On the settings tab, **Mark notifications as read in the cloud once passed on** (off by default) also tidies the app: a passed-on notification is marked as read there, a broadcast is dismissed. Switched off, nothing changes in the cloud.

### Version of the cloud

The cloud's API is not documented for third parties and may change. Storybox Plus reads the version of the cloud's backend once an hour (it is public, no sign-in) and names it on the settings tab. The cloud names its version as release and commit (`v2026.11.10/602b7aff2`); only the release counts. This version was tested with release **v2026.11.10**; when the cloud runs another release, the settings tab says so, and the diagnostics carry it. Another release is no error: the cloud is updated often, mostly without changes to what the integration uses.

### Favourite chapters

Bought figures and discs take favourite chapters: a star on each chapter, and a switch per figure. While the switch is on and the figure plays on a Toniebox 2, the integration steers the box:

```mermaid
stateDiagram-v2
    [*] --> Playing
    Playing --> Playing: a favourite begins
    Playing --> Jump: another chapter begins
    Jump --> Playing: to the next favourite,<br/>after a jump back at the box to the previous one
    Playing --> Paused: a chapter after the last favourite begins
    Paused --> Free: play pressed at the box
    Free --> Free: every chapter plays
    Free --> [*]: figure taken off
```

The box itself knows no selection; the integration sends it on through the cloud, so the start of a skipped chapter can be heard for a moment, and without the cloud or Home Assistant the box plays everything. Pressing play at the box after the pause behind the last favourite means the child wants to go on: the favourites stop steering that box for the figure, and every chapter plays, until the figure is taken off. Placed again, it is steered by its favourites again. The lists live in the integration's own store.

### Locking figures to the household

A bought figure or disc that is locked cannot be claimed into another household, for example when it is lent to a friend. Every one has a switch on its page entry. On the settings tab, **Lock new figures and discs to the household** (on by default) locks a figure once, the first time it shows up in the account; unlocked on the page or in the app, it stays unlocked, because a figure is looked at only once. The figures already in the account at the first start stay as they are. Switched off, new figures are only noted, so switching it on later touches only those that come after. A lock the cloud refused is tried again with the next poll.

### Settings of a box

The page shows the settings each box has, as the cloud names them, and changes them in a form; only what changed is sent. Which ones a box has depends on its generation and its feature flags:

| Setting | Toniebox 2 | Toniebox 1 |
|---|---|---|
| name, maximum volume and maximum headphone volume | yes, any percent | yes, 25, 50, 75 or 100 % |
| light ring brightness; at bedtime: light ring, maximum volume and maximum headphone volume (percent) | yes | |
| skipping chapters by tapping, the ear that skips forward, winding by tilting | yes | |
| tilt and tap, tap direction, LED (on, dimmed, off) | | yes |
| age mode, language | with the box's feature flag | with the box's feature flag |

A new name reaches the box's device in Home Assistant at once, also one given in the app; a name given to the device in Home Assistant stays. The card shows the box in its colour, with the picture the app uses.

The box takes new settings the next time it is online; until then the page says it waits for the box. Offline mode is shown, not changed: the cloud does not take it. Resetting a box to its factory settings is left to the app.

### Night mode of the light ring

A Toniebox 2 gets a night mode for its light ring: a span (from, until; across midnight when "until" comes first, in the box's time zone), a brightness for the span and one for the rest of the day. The integration sets the light ring when the span begins and when it ends; switched off during the span, the ring gets its normal brightness back at once.

It acts on the change only, not on every poll: a brightness set in the app in between stays until the next change. Which phase was set last is kept in the integration's store, so a change missed while Home Assistant was not running is made up at the next start, and one the cloud refused is sent again with the next poll. The box takes the new brightness the next time it is online.

### Bedtimes and the alarm

A Toniebox 2 knows bedtimes, as the app keeps them in the cloud: a name, the days, the time to sleep and the time to wake up, and whether an alarm rings then, with its volume and the morning light. The page lists them on the box's card with a switch each; they are added, changed and deleted there.

The box keeps one timer, and the alarm rings when that timer ends; the app sets it only once, so a bedtime alone makes no box ring again. Storybox Plus sets it itself:

```mermaid
flowchart LR
    poll["every poll, the box coming online,<br/>a changed bedtime"] --> next{"next wake-up of the<br/>active bedtimes with alarm<br/>within 18 hours?"}
    next -->|no| stale{"an alarm of ours<br/>nobody wants any more?"}
    stale -->|yes| clear["clear it"]
    next -->|yes| armed{"box reports this<br/>alarm already?"}
    armed -->|no| send["half a minute after the box came online:<br/>alarm preview, then timer with alarm"]
    send --> confirm["the box reports its timer"]
    confirm --> armed
```

- The days of a bedtime are the days of the wake-up; the times are the box's own time zone.
- The timer counts at most 18 hours (an unsigned 16-bit number of seconds), so the alarm is set from the afternoon before, as soon as the box is online. A box that stays off until the morning gets no alarm that night.
- What counts as set is what the box reports back, never what was sent. A box that does not confirm is asked three times, then again when it comes online anew; the log says so once.
- An alarm set by the integration for a wake-up no bedtime wants any more, because a bedtime was switched off, changed or deleted, is cleared. An alarm set in the app is left alone until a bedtime's alarm is due.
- While an alarm is due, the sleep timer actions and switching the box off are refused with the time of the alarm: each would replace the alarm.

### Listening times and battery

Home Assistant counts the listening time itself, from what a Toniebox 2 reports live: daily sums per figure and box, per chapter of a figure, per hour of the day per box, and how often each figure was placed; never single plays. The page ranks the most played figures and chapters and the figures placed most often, compares the period with the one of the same length before (once that one was counted in full), and shows when is listened to as a grid of weekdays and hours, for all boxes or one of them. They start with the setup; the Toniebox 1 and anything played while Home Assistant did not run are missing, and the page says so above the numbers. Counting is switched on the settings tab, on by default; switching it off deletes the sums and sets the account up anew.

How long a charge lasts from now shows on the card, by the past charges: the level times the average full charge.

How long a charge lasts: every discharge from leaving the charger to the next charge, with the hours the box was switched on (only while the push channel tells so), the percent used and the projection for a full charge. Discharges shorter than 10 minutes or 5 percent are left out; the last 60 are kept.

### Sign-in and privacy

- The password is used once for the sign-in; only the refresh token is stored, and the cloud rotates it with every refresh. A refused token asks for a new sign-in of the same account.
- No e-mail address, WLAN name or MAC address appears in a state or attribute. Diagnostics contain no tokens, names, addresses or listening data; the log never contains tokens or the password.
- Changes to the account (chapters, favourites) are offered only on the page, which is for administrators only; the WebSocket commands refuse everybody else. Uploaded files are deleted from Home Assistant as soon as they are in the cloud.
- A link is fetched by the Media Fetcher app inside your Home Assistant, which the integration finds through the Supervisor's list of apps and reaches in the app network without a token; only audio is taken from it, and the file is deleted from the app once it is in the cloud. Whether a video may be copied onto a figure is between you, its owner and the platform's terms; the integration does not check that.

### Chapters from text

A creative figure takes a chapter from text: the page takes a title (or the first words) and the text, Piper, the local voice of Home Assistant, speaks it, and the recording is uploaded as a chapter. The text never leaves the house. Like links, this is optional: without a Piper voice (the Wyoming integration with Piper) the button stays grey and says what is missing.

### The Media Fetcher app

Home Assistant's own container has no JavaScript runtime, which yt-dlp needs for most videos. So the fetching lives in the **Media Fetcher** app, a Home Assistant app of its own with yt-dlp, a runtime and ffmpeg. Install it under **Settings → Apps** and start it, and the page's link button comes alive; without it the button stays grey and says why. The app needs Home Assistant OS or a Supervised installation; without the Supervisor the integration works, only without links.

### Page

**Storybox Plus** in the sidebar, for administrators, built from Home Assistant's own elements, in four tabs:

- **Boxes**: every box with its live state; a Toniebox 2 with volume, headphones, sleep timer, the next alarm, what plays, buttons to play, pause, skip chapters, change the volume and set or cancel a sleep timer (left out while a bedtime's alarm is due), and the battery's level, which opens the charge history in an overlay. The sleep timer takes 30 or 60 minutes. The cog of a box opens its settings, the night mode of the light ring, its bedtimes and its firmware in an overlay. Its card shows online or offline as a coloured dot. A Toniebox 1 gets a small card: its settings in one line, when it was last seen and its cog; the cloud reports no connection state for it.
- **Figures**: the library with search over names and chapters, a filter by kind, which figure stands on a box, the chapters with their lengths, favourites for bought figures and the tools for creative ones. The cog of a figure opens its volume, lock, Tune and shuffling on swap in an overlay; adding a chapter from a link, a text or a code asks in an overlay too.
- **Settings**: per account, the household's name and its members (shown only: name, email and role as the cloud shows them to the account, read once an hour; managed in the app), redeeming a Tunes voucher, counting the listening time, locking new figures, marking notifications as read, and the cloud's version. A new household name also becomes the entry's title and the account device's name, as long as the title was still the household's name.
- **Listening**: the most played figures and chapters, when is listened to (weekday and hour), the total, a chart per day (per week over long spans) and the sums per box, for 7, 30 or 365 days or since the setup.

The header is one row: the integration's icon, its name and right after it the tabs. At its end it carries, as on every page of the shared standard, when the open tab's data came ("As of 14:53:23", left out on a phone), a refresh button that asks the integration again without reloading the page and spins while it waits, and a settings button to the integration's page under **Settings → Devices & services**. The boxes tab asks again every 10 seconds by itself, and the stamp follows.

At the bottom it shows the version of the integration. On a phone the tabs move to the bottom.

### Dashboard card

The card of a Toniebox 2 from the page, for any dashboard: `custom:storybox-plus-box-card`, offered in the card picker as **Storybox Plus · Toniebox**. It loads with the integration; there is no resource to add.

```yaml
type: custom:storybox-plus-box-card
entity: media_player.kids_room
```

It shows what the page's card shows (online or offline, the battery's level, volume, headphones, the sleep timer, the next alarm, the night mode at work, what plays) and has the same buttons: play, pause, skip chapters, louder and quieter, a sleep timer of 30 or 60 minutes. It leaves out what only administrators see: the settings, the bedtimes and the charge history.

Every user who may read the box's media player sees the card, not only administrators; the buttons are the media player's actions and `storybox_plus.set_sleep_timer`. The card asks the integration again when the media player changes and every 30 seconds.

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

## Known limitations

- The Toniebox 1 has no live data: no battery, no playback, no figure, not even whether it is online. It gets no device in Home Assistant; its settings are changed on the page.
- Everything goes through the manufacturer's cloud. Without internet, or when the cloud is down, the entities are unavailable; the boxes keep playing on their own.
- The box plays whatever figure stands on it; Home Assistant cannot choose a figure.
- The listening times count from the setup on; the cloud offers no history.
- Favourite chapters work only on a Toniebox 2 and only through the cloud.
- The alarm of a bedtime is set only while the box is online and Home Assistant runs; the box keeps one timer, so an alarm and a sleep timer exclude each other. The alarm tone is the one the app chose, or the app's first; the page does not choose tones.
- Uploads go through Home Assistant's own file upload and take at most 100 MB per file. Which formats the cloud converts is its decision.
- The cloud's API is not documented for third parties. If the manufacturer changes it, this integration needs an update.

## Troubleshooting

- **"The cloud cannot be reached" during setup**: check the internet connection of Home Assistant; the sign-in server is `login.tonies.com`.
- **The entities are unavailable**: the cloud did not answer three polls in a row; the log names the error. The diagnostics show whether the push channel is connected (`push_connected`).
- **The media player shows nothing although the box plays**: the push channel may be reconnecting; the cloud drops it every few minutes. If it stays silent, download the diagnostics and open an issue.
- **A new sign-in is asked for**: the refresh token was refused, for example after a password change. Sign in again with the same account.
- **The link button is grey**: the Media Fetcher app is not installed or not started.
- **The alarm stays "set as soon as the box is online"**: the box is off or did not confirm; the log says when it did not. Switch the box on.
- **"An alarm of a bedtime rings at …" from the sleep timer**: a bedtime's alarm is due; switch its alarm off on the page first.
- **The page looks old after an update**: the script's address carries a hash of its content, so a restart of Home Assistant brings the new page; the companion app may need its frontend cache reset.
- Debug logging: **Settings → Devices & services → Storybox Plus → ⋮ → Enable debug logging**.

## Interface

What automations and dashboards can build on. Before 1.0.0 it may still change between minor versions.

### Entities

IDs as created in English, for a box named "Kids room". Every unique ID starts with the config entry (`<entry>`), and a box's device is `(storybox_plus, <entry>_<box>)` with the box's ID from the cloud: members of one household who each add their own account get a device of the shared box per account instead of a collision.

| Entity | Unique ID | Boxes | State |
|---|---|---|---|
| `binary_sensor.kids_room_connectivity` | `<entry>_<box>_connectivity` | Toniebox 2 | connected to the cloud; unknown while nothing tells |
| `sensor.kids_room_battery` | `<entry>_<box>_battery` | Toniebox 2 | battery in percent; unavailable while the box is switched off |
| `binary_sensor.kids_room_charging` | `<entry>_<box>_charging` | Toniebox 2 | charging |
| `binary_sensor.<account>_live_channel` | `<entry>_live_channel` | the account's device, with a Toniebox 2 | the push channel is connected; live state and commands of every Toniebox 2 go through it |
| `media_player.kids_room` | `<entry>_<box>` | Toniebox 2 | `playing`, `paused`, `idle` (no figure), `off` (switched off) with figure, chapter, picture, position and length |
| `event.kids_room_figure` | `<entry>_<box>_figure` | Toniebox 2 | event types `placed`, `removed` with `tonie_id` and `tonie` (name) |
| `event.<account>_cloud_notification` | `<entry>_notification` | the account's device | event type `notification` with `kind` (the cloud's type, `system` for a broadcast), `text`, `time`, `tonie_id`, `tonie`, `reason` (why a conversion failed) |

The media player takes play, pause, volume (13 levels), next and previous chapter, seeking within the chapter, playing a chapter of the figure on the box picked from the media browser (`media_player.play_media` with `chapter:<figure>:<index from 0>`; a chapter of another figure is refused), and turning off, which puts the box to sleep as the app's sleep button does; the cloud cannot wake it again.

### Actions

| Action | Fields | Description |
|---|---|---|
| `storybox_plus.set_sleep_timer` | `minutes` (1 to 1092) | the box falls asleep on its own after that time; a running timer is replaced |
| `storybox_plus.clear_sleep_timer` | none | cancels the running timer |

Both target the media player of a Toniebox 2. While the alarm of a bedtime is due, they and turning the media player off are refused, because each would replace the alarm.

### WebSocket commands

For administrators only, but one; the page uses them. Their answers serve the page and are not part of this interface. `storybox_plus/box/card` (`entity_id` of a box's media player) serves the dashboard card: it answers every user who may read that entity, with the box's live state and nothing of its settings.

| Command | Parameters |
|---|---|
| `storybox_plus/overview` | none; boxes with their live state and the version |
| `storybox_plus/library` | none; households and figures with chapters and favourites, the bought Tunes, whether links can be fetched and whether Piper can speak |
| `storybox_plus/analytics` | `days` (or none for all), `limit` |
| `storybox_plus/chapters/arrange` | `tonie_id`, `chapters` (IDs in the new order; the rest is removed), optional `titles` (chapter ID → new name) |
| `storybox_plus/chapters/add_text` | `tonie_id`, `text` (up to 5000 characters), optional `title` (else the first words); Piper speaks it |
| `storybox_plus/chapters/add` | `tonie_id`, `file_id` (from `/api/file_upload`), optional `title` |
| `storybox_plus/chapters/add_link` | `tonie_id`, `url`; a subscription that reports the stages |
| `storybox_plus/favourites/set` | `tonie_id`, `chapters` (positions from 0), `active` |
| `storybox_plus/figure/refresh` | `tonie_id` |
| `storybox_plus/figure/update` | `tonie_id` (a creative figure) and `name` and/or `live` |
| `storybox_plus/figure/shuffle_on_swap` | `tonie_id` (a creative figure), `enabled` |
| `storybox_plus/household/rename` | `household_id`, `name`; answers with the entry's title |
| `storybox_plus/figure/tune` | `tonie_id`, `tune_id` (from the library's `tunes`, or null to take the Tune off); answers with the Tunes and the figure |
| `storybox_plus/box/command` | `box_id` (a Toniebox 2), `command` (`play`, `pause`, `next`, `previous`, `volume` with `value` 0 to 13, `sleep` with `value` in minutes, `sleep_clear`) |
| `storybox_plus/voucher/redeem` | `entry_id`, `code`; answers with how many Tunes it brought and the Tunes |
| `storybox_plus/figure/redeem_token` | `tonie_id` (a creative figure), `token`; answers with the figure |
| `storybox_plus/figure/lock` | `tonie_id` (a bought figure or disc), `locked` |
| `storybox_plus/preferences/set` | `entry_id` and any of `analytics`, `auto_lock`, `mark_read`; switching `analytics` sets the account up anew |
| `storybox_plus/figure/volume` | `tonie_id`, `level` (1 to 13, or null for the box's own volume) |
| `storybox_plus/bedtime/save` | `box_id`, optional `schedule_id` (none: a new bedtime, which needs `sleep_time`, `wakeup_time`, `days`), `name`, `sleep_time` and `wakeup_time` (`HH:MM`), `days` (`monday` … `sunday`), `enabled`, `alarm_enabled`, `alarm_volume` (0 to 100), `alarm_morning_light`; answers with the box |
| `storybox_plus/bedtime/delete` | `box_id`, `schedule_id`; answers with the box |
| `storybox_plus/night/set` | `box_id`, `enabled`, `start` and `end` (`HH:MM`, not the same), `night` and `day` (0 to 100); a Toniebox 2 only; answers with the box |
| `storybox_plus/box/settings` | `box_id` and any of `name`, `max_volume`, `max_headphone_volume` (1 to 100; a Toniebox 1 only 25, 50, 75, 100), `lightring_brightness`, `bedtime_lightring_brightness` (0 to 100), `bedtime_max_volume`, `bedtime_max_headphone_volume` (1 to 100), `skipping_enabled`, `skipping_direction` and `tap_direction` (`left`, `right`), `scrubbing_enabled`, `accelerometer_enabled`, `led_level` (`on`, `dimmed`, `off`), `age_mode`, `language`; a setting the box does not have is refused; answers with the box |

### Stores

`.storage/storybox_plus.<entry>.analytics` (daily sums per figure and box, per chapter, per hour), `.battery` (charges), `.chapters` (chapters learned from the boxes), `.favourites`, `.night` (night modes with the phase set last), `.volumes` (levels per figure and the levels to restore per box), `.notices` (the cloud's notifications passed on), `.settings` (the settings tab and the figures looked at for locking) and `.shuffle` (the figures shuffled on swap and the last figure per box), version 1 each. Deleting the entry deletes them.

## Installation

1. **Settings → Marketplace → Add from link** (top right), enter `https://github.com/n-schilling/ha-storybox-plus` as GitHub link and add it. Adding a repository by link asks you to connect GitHub once.
2. Install **Storybox Plus** in the Marketplace and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Storybox Plus** and sign in with the e-mail address and password of the app's account.
4. Optionally install the **Media Fetcher** app under **Settings → Apps** for chapters from links.

Requires Home Assistant 2026.11 or later. Without the Marketplace, copy `custom_components/storybox_plus` into the `custom_components` folder of your configuration directory and restart.

The integration has no options of its own; what can be chosen sits on the page's settings tab.

### Removal

**Settings → Devices & services → Storybox Plus → ⋮ → Delete** removes the devices, the entities, the stores and the page. The cloud account is not changed; the token Home Assistant held simply expires. Then remove the integration in the Marketplace and restart.

## Development

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
scripts/check.sh
```

`scripts/check.sh` runs what CI runs: ruff, the changelog and translation checks, mypy, the tests with their coverage threshold, the page checks and hassfest in Docker (`--no-page`, `--no-hassfest` leave them out). The page check is not part of CI: run `scripts/check.sh` before a release that changes the page.

The cloud access lives in `custom_components/storybox_plus/cloud/` and imports nothing from Home Assistant, so it can be tested on its own; its README collects what is known about the API. Endpoints and payloads were learned from the official app and from the community project [HA-Toniebox](https://github.com/git4sim/HA-Toniebox) (MIT); the code here is written from scratch.

The page checks start a throwaway Home Assistant, reachable from this machine only, whose integration talks to a made-up cloud (`scripts/panel/demo_cloud.py`: one household, a Toniebox 2 that plays and confirms its alarm, a Toniebox 1, invented figures, bedtimes, listening times and charges). They drive the page in a headless browser (boxes, their settings and renaming one, the night mode set up through its form with the light ring following, a volume per figure, a creative figure renamed and sorted, the settings tab with the household's members, a figure unlocked and locked, the box's picture, a Tune laid on and taken off, the player's buttons and the headphones on the card, a voucher and content from a code, the most played chapters and the weekday and hour grid, live mode and shuffling on swap switched on, removing all chapters with its two questions, the household renamed, bedtimes with the alarm set on the box, their switches and the form to add and delete one, charge history, the header row with icon, name and tabs, the header's stamp, refresh on every tab and settings button, search and filter, favourites and their switch, rearranging and uploading chapters, the link button without the app, listening times, phone width in dark mode, no page for non-administrators) and stop Home Assistant again. They need their own environment:

```bash
uv venv --python 3.14 .venv-panel && uv pip install --python .venv-panel/bin/python -r requirements_panel.txt
```

They use an installed Google Chrome, otherwise Playwright's Chromium (`.venv-panel/bin/python -m playwright install chromium`). The pictures in this README come from the same run:

```bash
.venv-panel/bin/python -I scripts/panel/check_panel.py --screenshots docs/screenshots
```

Releases: CI runs on `dev`; once it is green, push that commit to `main`. CI does not run again there: the release workflow checks that CI passed for the commit, then tags the version from `manifest.json` and publishes a GitHub release with its CHANGELOG section; the Marketplace offers it as an update. While the repository is private the workflow stops after that check: the first release is the public one.

For testing on a Home Assistant OS host before a release (copies the files, writes the deployed commit for the page and restarts Home Assistant):

```bash
scripts/deploy.sh <ssh-host>
```

The page shows the version and that commit at the bottom; `-dirty` marks files that differ from it.

## License

Apache License 2.0, see [LICENSE](LICENSE).
