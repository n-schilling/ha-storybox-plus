# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.4.0] - 2026-11-27

### Changed

- The sleep timer of a Toniebox 2 is one button in the row of the others, on the page and on the dashboard card. It opens a small dialog with 15, 30, 45 and 60 minutes and a field for any other duration.
- The volume sits in the head of a box beside the battery, and both look alike; the row below is left to what is out of the ordinary (headphones, a running sleep timer, the next alarm, the night mode).
- The account's sensor that counts and lists the boxes with a media player is named "Tonieboxes 2" instead of "Boxes", because it leaves a Toniebox 1 out. An installed sensor keeps its entity ID; a new installation names it `sensor.<account>_tonieboxes_2`.

## [1.3.1] - 2026-11-27

### Added

- More ready-made automations in the view Automations: for every figure, placed on a Toniebox 2, repeat it, pause it late in the evening, or write a note; for every Toniebox 2 a sleep timer each evening and a note when the battery runs low.

### Changed

- The README is short: what the integration is for, three pictures, the installation, limitations and troubleshooting. The rest moved into four documents under `docs/` (what it does, the page and the dashboard card, automations and interface, development), and a check makes sure the links between them lead somewhere.
- The cloud under Setup → Preferences reads one line: it fits this version, it was updated and is not tested yet, or it answers differently than expected. The versions and the time of the last test moved behind the (i); what a test found goes into the issue on GitHub instead of onto the page.

## [1.3.0] - 2026-11-27

### Added

- The page, the dashboard card and Home Assistant's texts of the integration speak French, Spanish, Italian, Dutch, Polish and Brazilian Portuguese besides English and German: the languages tonies offers figures in. A language other than English and German is fetched by the page when it is first needed. A check in CI makes sure every language has every text with its placeholders.

- Actions for automations (the page stays the easy way by hand): `storybox_plus.add_chapter` adds a chapter to a creative figure from a media source, a text spoken by the account's voice or a video link, and with `replace` removes the older chapters of the same title; `storybox_plus.remove_chapters` removes the chapters of a title or all but the last ones; `storybox_plus.shuffle_chapters` shuffles a creative figure; `storybox_plus.set_box_settings` changes settings of a Toniebox 2. The chapter actions name the figure by its name or ID and answer with the figure. They are for administrators and automations.

- A check of the cloud's interface: when the cloud reports a release this version was not tested with, the integration reads once everything it reads from the cloud and compares the answers with the fields it relies on. The result stands under Setup → Preferences beside the cloud's version; the button "Test the cloud interface" runs the check again, and "Report on GitHub" opens an issue with the requests that answer differently. The check only reads and names nothing of the account.

- The page has a view **Automations** for every figure and every Toniebox 2: ready-made automations with the figure's ID and the boxes' entities filled in, valid YAML, copied with one button and pasted into a new automation; a button opens Home Assistant's editor.

### Changed

- On the page, the picture and the name of the figure that plays on a box open the figure's own page.
- Tested with the cloud's release v2026.11.27: the check of the interface compared 16 of its 20 requests and messages on a real account and found them as expected; the other four (bedtimes, notifications, broadcasts, discs) had nothing to compare there.
- A Toniebox 2 that has taken new settings says so through the push channel; the page's note that the box waits for them goes at once instead of with the next poll.
- The volume of a figure explains, on the page and in the README, that its 13 levels are shares of the box's maximum volume: level 13 is that maximum, so a figure never plays louder than the maximum allows.

## [1.2.2] - 2026-11-27

### Fixed

- Right after a figure is placed, a Toniebox 2 reports that it loads the content, and plays meanwhile; the flag stays until the next chapter begins. Home Assistant took that as not playing: the media player showed idle, the listening time of that chapter was not counted, and the favourites began only with the next chapter. A box that loads and names the end of the chapter now counts as playing.

## [1.2.1] - 2026-11-27

### Fixed

- A figure placed on a Toniebox 2 that was switched off did not begin with its favourites: the box woke with the figure and Home Assistant took it as playing already. A box that was offline for two minutes or more and wakes with a figure on it now counts as placed.

## [1.2.0] - 2026-11-27

### Added

- Favourites play by a mode, set for the account under Setup → Preferences and, where a figure should differ, in the figure's settings: favourites first (placed on a Toniebox 2, the figure starts with its favourites and plays the other chapters after them), a random favourite first, only the favourites, only the favourites within a bedtime of the box, or as the box plays.
- Creative figures take favourites too. Their stars are kept by chapter, so they stay with their chapters when these are arranged anew or shuffled.
- A star beside the chapter that plays, on the page and on the dashboard card, sets or takes off the favourite at once; the list of chapters of a box has a star per chapter. The media player has the attribute `favourite` and the actions `storybox_plus.set_favourite` and `storybox_plus.play_favourite` (the next favourite of the figure on the box), which every user may call.
- The dashboard card has the button for the list of chapters, as the page has: the chapters of the figure on the box open in a dialog, a chapter chosen there plays from its start and a star marks it. The media player carries the list for it in the attributes `tonie_id` and `chapter_list` (not recorded).
- The page **Favourites** under Figures lists every chapter with a star; one whose figure stands on a Toniebox 2 plays with a tap.
- The button **Everything today** on a box's card lets the figure play every chapter until it is taken off, and ends that again.
- The listening summary shows the favourites: their share of the listening time, also per figure, the chapters heard most that have no star yet, and the stars that were hardly heard, each with its star to set or take off.

### Changed

- **Breaking:** the switch "Steer the Toniebox 2 by the favourites" of a figure is gone. A figure whose switch was on now has the mode "Only the favourites", one whose switch was off "As the box plays"; every other figure follows the account's mode, which starts as "Favourites first". The WebSocket command `storybox_plus/favourites/set` takes `mode` instead of `active`.
- The order of the favourites begins when the figure is placed. The same figure taken off for less than two minutes plays on where it was.
- With only the favourites playing, a figure placed behind its last favourite begins with the first one instead of pausing at once.
- Repeat of the whole figure, while favourites steer it, plays their order to its end and begins it again.

### Fixed

- A chapter chosen in Home Assistant (the list of chapters on the page, the media browser, the next and previous buttons) was left again at once when it was no favourite. It plays now; next and previous lead to the chapters the order wants.
- A chapter first reported while the box was paused or still loading was never left afterwards, although it was no favourite.
- A command of the favourites that did not reach the box was not sent again: the chapter played to its end. It is sent again with the next report of the box, three times in a row at most.
- While a Tune lies on a figure, the box is no longer steered by the favourites of the figure's own chapters.
- Two accounts of one household both steered the box they share; now the account that speaks for the box does, with the stars kept in one place.
- A chapter chosen in Home Assistant before the box itself reported what it plays was refused as "another figure"; the figure the cloud names counts until then.
- After a restart of Home Assistant the favourites steered a figure again that had been set free by pressing play; what a box plays of its figure is kept now.
- Listening time that ran over a full hour lost a second in the sums per day, per chapter and per hour.

## [1.1.1] - 2026-11-26

### Fixed

- A presence entity of a Toniebox 1 that changed while Home Assistant was starting wrote an error to the log (`'NoneType' object has no attribute 'boxes'`) and the change was lost until the next one; a change during a later poll of the cloud showed only with the poll after it. The entity is now read once more at the end of every poll.

## [1.1.0] - 2026-11-26

### Added

- Four entities per Toniebox 2 for what only the page and the dashboard card could tell so far: whether headphones are connected (`binary_sensor`, with their kind and battery as attributes), whether the night mode of the light ring is at work (`binary_sensor`), when the running sleep timer ends and when the next alarm of the bedtimes rings (both `sensor`, timestamps; the alarm only for a box that rings alarms). Automations can use them, a time trigger with an offset for example reminds before the alarm.
- A sensor on the account's device counts the Tonieboxes 2 and lists them in its attribute `boxes` (name, media player, picture), so a dashboard shows the boxes without searching for them.
- The dashboard card needs no configuration: without `entity` it shows every Toniebox 2. It has a `title` and a `size`, and in a sections view it follows the rows it gets: large with everything, medium with what plays, small as one row.
- The media player of a Toniebox 2 has the attributes `chapters` (how many chapters the figure has) and `box_picture` (the address of the box's picture).

### Changed

- **Breaking:** the dashboard card is now `custom:storybox-plus-card`; it was `custom:storybox-plus-box-card`. A dashboard that has the card shows an error in its place until the type is changed in the card's YAML.
- The dashboard card is written for whoever lives with the box: headphones read "Headphones, battery 80 %" (on the page too), a box that is switched off says so in Home Assistant's word and its dot is no longer red, and the chip of the light ring's night mode is off until `show_night_mode` switches it on.
- The dashboard card reads the entities of its box and nothing else; the WebSocket command `storybox_plus/box/card` it asked before is gone. It follows the entities at once instead of asking every 30 seconds. With that, the volume shows in percent only and its buttons are the media player's steps, the battery does not show while the box is switched off, a sleep timer shows only with its end, and the figure's picture comes through Home Assistant.
- The dashboard card is kept in the dashboard resources (created on setup, pointed to the new version after an update, removed with the last account; resources kept in YAML are left alone) beside being loaded on every page. Its editor is Home Assistant's form with the card's defaults filled in, and writes only what differs from them. Times on the card and the page follow the 12 or 24 hours of the user's profile.
- The media player names the figure on a box from the cloud until the box itself reports what it plays, after a restart of Home Assistant for example.

## [1.0.1] - 2026-11-23

### Changed

- The repository passes the HACS validation without a skipped check: the brand images in the integration's `brand` folder are enough. Nothing changes in the integration itself.

## [1.0.0] - 2026-11-23

### Added

- A Toniebox 1 can be given a presence entity on its settings page: a device tracker (from the router's integration, for example) or a binary sensor for connectivity, such as a ping. The cloud knows nothing live of such a box; with the entity its card shows whether it is online, and the listening summary shows its active time: how long it was in the network. That is an indication, not listening time, and enters none of the listening sums: the box stays awake for some minutes after the last sound, the entity notices its leaving late, and a box in offline mode is not seen. The entity is kept in Home Assistant only; without one, the box shows no state, as before.
- The lag of a Toniebox 1 is taken off its active time: how long the box stays in the network after its last use, as the entity sees it, 20 minutes by default (measured with a router's device tracker) and set per box from 0 to 120. It goes off the end of every stretch in the network; a stretch no longer than the lag counts nothing.
- The card of a Toniebox 2 on the overview opens the list of the chapters of the figure on it, above the page; the one that plays is marked, and a chapter chosen there plays from its start. The dashboard card stays as it is.
- Repeat for a Toniebox 2: the whole figure or one chapter, by a button on the box's card on the overview (off, the whole figure, this chapter) and by the media player's repeat action. The box knows no repeat; the integration sends it back to the first chapter once the figure has ended, or to the start of a chapter that ran out, so the beginning of the next chapter can be heard for a moment. With favourite chapters at work the figure repeats from the first favourite. The repeat belongs to the figure on the box and ends when it is taken off; it is kept in the integration's store, so it goes on after a restart of Home Assistant while that figure is still on the box. An end of the figure that Home Assistant did not see happen is not caught up.
- Setup → Preferences: the text-to-speech entity that speaks text chapters can be chosen, any one of Home Assistant, with its voices in the language of the page. Without a choice Piper speaks, as before, and the text stays in the house; a voice of a cloud service gets the text. A chosen entity that is unavailable is not replaced by another.

### Changed

- The battery level on the card of a Toniebox 2 stands beside its symbol with a gap and on one line with it; before, the two touched.
- A Toniebox 2 that has not reported a battery level since Home Assistant started shows no battery on its card, instead of an empty symbol with a dash; an offline box keeps the last level it reported.
- Listening → Summary: the sums per box are headed "Listening time of the Toniebox 2", beside the active time of the Toniebox 1.

## [0.11.1] - 2026-11-21

### Fixed

- The push channel reopens at once when the cloud drops it at the end of its five-minute token, instead of after a pause of five seconds, and it counts as connected meanwhile: listening time, battery statistics and the alarm check are no longer interrupted every five minutes. The routine reconnect is logged at debug level only; any other drop still waits before the next attempt and is logged at info level.

## [0.11.0] - 2026-11-20

### Added

- Setup → Log: the integration's latest lines on the page, with buttons to copy and download them, a log level (Debug, Info, Warning, Error) and how many days the lines are kept (7 by default, 0 to 90), both kept across restarts. The lines are written to one file per day in Home Assistant's storage folder. Every change sent to the cloud is logged at Info with its answer, refused ones as warnings; reads, push messages and token refreshes at Debug. A Tune that comes onto a figure or leaves it between two polls is logged, whoever did it.
- A chapter fetched from a link is confirmed on the page once it is on the figure.
- Setup → Preferences: how long listening time is kept (1, 2 or 5 years, or always; it was fixed at 2 years), the Piper voice that speaks text chapters (the voices of Home Assistant's language, or Piper's default), and the largest file taken from the Media Fetcher app (10 to 2000 MB, 200 by default; it was fixed).

### Fixed

- A chapter is no longer sent to a creative figure a Tune lies on: the Tunes are read anew first, and the page says to take the Tune off. Before, the cloud accepted such a chapter and the figure never had it.
- A chapter the cloud answers without is an error on the page instead of a silent success.
- Taking a Tune off or laying one on waits until the cloud shows the change; if it does not within about ten seconds, the page says so instead of showing the Tune as gone.

## [0.10.1] - 2026-11-17

### Fixed

- On a phone with a notch or rounded corners (iPhone) the page's header was too high and the bar at the bottom ran off the screen.

## [0.10.0] - 2026-11-17

The page follows the changed page standard: Home Assistant's own frame, areas and subpages.

### Added

- A dashboard card for a Toniebox 2, `custom:storybox-plus-box-card`: the live state and the buttons of the page's card, without settings, bedtimes or charge history. It loads with the integration and is open to every user who may read the box's media player; its data come from the new command `storybox_plus/box/card`, its buttons are the media player's actions. Options `show_picture`, `show_battery`, `show_volume`, `show_headphones`, `show_sleep_timer`, `show_next_alarm`, `show_night_mode`, `show_playback` and `show_controls` leave parts out; the editor offers them as switches. The card takes any width from a quarter of a section on and lays itself out by it: side by side from 600 px (fits 748 × 262 px), stacked and tighter below (fits 370 × 262 px), compact under 300 px.

### Changed

- The page sits in Home Assistant's frame for settings pages, with four areas as tabs (at the bottom on a phone) and their pages as tabs below: **Boxes**, **Figures** (figures, Tunes), **Listening** (summary, times) and **Setup** (overview, household, preferences). Addresses are `/storybox-plus/<area>/<page>`; the old `#boxes`, `#figures`, `#listening` and `#preferences` lead to the page that took their place, and without an account loaded the page starts at the setup.
- A box and a figure open as pages of their own with a back arrow (`?key=…&view=…`) instead of an overlay: a box with its settings, night mode, bedtimes and battery, a figure with its chapters, settings, Tune and what can be added.
- Settings are rows with their explanation behind an (i), saved together with one button that shows while something differs; percent values are text fields with their unit instead of sliders. Bedtimes keep their own add, switch and delete.
- The setup overview lists the steps with their state and leads to the first open one; the version of the integration shows at its bottom only.
- Errors read one line by their kind, Home Assistant's message behind an (i); the dashboard card shows the line only. Numbers follow the number format of the user's profile, on the page, in the fields and on the card, and fields take a point or a comma.
- The kind filter and the period are Home Assistant's filter chips and segmented control, states are its badges; the chart and every cell of the weekday and hour grid say their values in words for screen readers. The integration button in the header is labelled "Integration in Home Assistant".

## [0.9.0] - 2026-11-13

The last steps before 1.0.0: what is left are checks on a real box.

### Added

- The listening tab ranks the figures placed most often on a Toniebox 2. Counted from now on, per day and box like the listening time; a figure already on the box when Home Assistant starts is not counted again.
- The settings tab shows the members of each household with name, email and role, as the cloud shows them to the account; read once an hour, shown only.

### Changed

- Calmer page: the cog of a box opens its settings, night mode and bedtimes in an overlay, the card keeps the live state, the next alarm and the battery; the cog of a figure opens its volume, lock, Tune and shuffling on swap; links, texts and codes are entered in an overlay. Escape or a click beside it closes it.
- The card of a Toniebox 2 shows only the battery's level; a click on it opens what a charge lasts and the charge history. The sleep timer offers 30 and 60 minutes. The firmware moved into the box's settings.
- The volume of a Toniebox 2 shows in the percent the box reports, on the page and in the media player; the levels stay what the buttons set.
- Error messages say in plain words what went wrong and what to do, in the language of Home Assistant; a lost connection says so instead of showing "[object Object]".
- A Toniebox 1 shows as a small card of its own: its settings in a line and when it was last seen, the settings behind the cog; it shows no connection state, as the cloud reports none for it. The page, the device model and the documentation call it Toniebox 1.
- A Toniebox 1 gets no device and no entity: the cloud reports no connection state for it, so its connectivity sensor never knew anything. A device left from before goes after an hour, or at once by hand.
- The settings of a creative figure hold its name, saved by its own button, and the live mode; the edit mode keeps to the chapters and is offered only when there are some. A Tune has an overlay of its own, opened by the icon beside the figure's cog.
- The head of a Toniebox 2's card holds its name, a coloured dot for online or offline (the word in its tooltip), the battery's level and the cog; it names no generation.
- The unique IDs of a box's entities and the identifier of its device start with the config entry, so two accounts of one household no longer collide over their shared box. Installed boxes get new devices and entities; the old ones are left behind and can be deleted.
- A box or figure shared by two accounts of one household shows once on the page, through the account added first, and only that account counts its listening time.

### Fixed

- Escape closes every overlay wherever the focus is; before, it did nothing once the focus had left the page, for instance after a click beside a field.
- Pressing louder or quieter several times in a row on the page goes up or down a level each time; before, a press before the box's answer sent the same level again.

## [0.6.0] - 2026-11-13

### Added

- Chapters renamed one by one in the edit mode of a creative figure.
- A chapter from text: Piper, the local voice of Home Assistant, speaks it; without a Piper voice the button stays grey, like the link button without the Media Fetcher app.
- How long the battery lasts from now, on the card of a Toniebox 2.
- The listening tab compares the period with the one before and shows the weekday and hour grid per box; hours are kept per box.
- A sensor of the account tells whether the live channel is connected, for an automation that tells the admin.

### Changed

- Counting the listening time is switched on the settings tab; the integration has no options flow any more.
- Listening hours are kept per box; hours counted before for all boxes together are left out.

## [0.5.0] - 2026-11-13

### Added

- Bedtimes of a Toniebox 2 on the page: on the box's card with a switch each, added, changed and deleted through a form (name, days of the wake-up, bedtime, wake-up, alarm with volume and morning light).
- The alarm of a bedtime is set on the box by the integration every evening, as soon as the box is online, because the app sets it only once; the page shows the next alarm and whether the box has it. An alarm of the integration that no bedtime wants any more is cleared.
- The diagnostics name a box's feature flags, whether it has a time zone, how many bedtimes it has and whether its timer carries an alarm.
- Page checks for the bedtimes: the alarm set on the box, a switch, a new bedtime through the form and deleting it.
- Settings of a box on the page, as the cloud names them, changed through a form: name and maximum volumes for every box (any percent on a Toniebox 2, the four steps on a classic box); light ring, the limits at bedtime, skipping and winding on a Toniebox 2; tilt and tap, tap direction and LED on a classic box; age mode and language where the box has the feature. The page shows whether the box has taken them and whether it is in offline mode.
- Page checks for the settings: the summary per generation and renaming a box through the form.
- A chapter of the figure on a Toniebox 2 can be picked from the media browser and played from its start (`media_player.play_media`).
- Creative figures are renamed in the edit mode, where their chapters can also be sorted by title or shuffled.
- A volume level per figure: placed on a Toniebox 2, the figure plays at its level; taken off or replaced, the box's level from before comes back exactly, also after a restart.
- The cloud's notifications (the account's unread ones and the broadcasts) are passed on once each as events of `event.<account>_cloud_notification`, on a device of the account.
- Creative figures: live mode (the newest chapter first) as a switch in the edit mode, and a button to remove all chapters there, which asks twice: whether all should go, and whether the audio files are kept elsewhere, because the cloud keeps no copy.
- Shuffle on swap per creative figure: replaced by another figure on a Toniebox 2, it gets a new order; taken off and put back, it keeps where it was.
- The household is renamed on the settings tab; the entry's title and the account's device follow.
- Buttons on the card of a Toniebox 2: play, pause, previous and next chapter, quieter and louder, and a sleep timer of 15, 30, 45 or 60 minutes or cancelling it; the sleep timer buttons are left out while the alarm of a bedtime is due.
- Headphones on a Toniebox 2 shown on its card, with their battery (push channel `metrics/headphones`).
- A Tunes voucher is redeemed on the settings tab; ready-made content goes on a creative figure from a code.
- Listening times also per chapter and per hour of the day: the page ranks the most played chapters and shows a grid of weekdays and hours. Still no single plays are kept.
- Bought Tunes on the figures tab: one laid on a fitting figure and taken off again; a creative figure keeps its chapters meanwhile.
- A settings tab on the page, per account: locking new figures and discs to the household (on), marking passed-on notifications as read in the cloud (off), and the cloud backend's version.
- New bought figures and discs are locked to the household once; every one has a lock switch on its page entry, and one unlocked stays unlocked.
- Passed-on notifications can be marked as read in the cloud; broadcasts are dismissed.
- The box's device takes the name the box has in the cloud, also one given in the app.
- Box cards show the box in its colour, with the app's picture.
- The cloud backend's version is read once an hour; the settings tab says when its release differs from the tested one (v2026.11.10). The commit behind a release is not compared.
- Night mode of the light ring for a Toniebox 2: a span, a brightness for it and one for the rest of the day, set up on the page. The integration sets the light ring at the start and the end of the span, makes up a change missed while Home Assistant was not running and sends a refused one again with the next poll; switched off at night, the normal brightness comes back at once. Kept in the store `storybox_plus.<entry>.night`.

### Changed

- While the alarm of a bedtime is due, `storybox_plus.set_sleep_timer`, `storybox_plus.clear_sleep_timer` and turning the media player off are refused, because each would replace the alarm; the error names the time of the alarm.
- A sleep timer that ends with an alarm is shown with the bedtimes, not as a sleep timer.

## [0.4.0] - 2026-11-11

### Changed

- One header row like on Nico's other pages: the integration's icon (from its brand folder, as Home Assistant serves it), the name and right after it the tabs; the second row with the tabs is gone. On a phone the tabs stay at the bottom.
- The page checks test the header row: the icon loads and sits left of the name, the tabs in the same row right after the name on every tab, icon and name without tabs on a phone.

## [0.3.0] - 2026-11-11

### Added

- The page's header has the shared standard's three actions on every tab: a stamp of when the tab's data came ("As of HH:MM:SS", hidden at phone width), the refresh button, which now spins while the integration answers, and a settings button that opens the integration's page in Home Assistant.
- The page checks test the three on every tab: the stamp, a refresh that asks the integration again and moves the stamp, and the settings button opening the integration's page without a reload.

## [0.2.0] - 2026-11-10

### Added

- The page shows the version of the integration at its bottom, taken from the manifest; a test deployment (`scripts/deploy.sh`) adds its commit.
- The device of a box that left the account can be removed by hand.
- Page checks in a real browser against a throwaway Home Assistant with a made-up cloud, also as a CI job; they make the README's screenshots.

### Changed

- The page is built from Home Assistant's own elements: top app bar with the menu button, cards, buttons, icon buttons, alerts, a switch for the favourites and forms for the search and the link. The header has the sidebar's colour like the settings pages.
- The script of the page is loaded with a hash of its content, so a changed page is never served from a cache.
- Favourite chapters: pressing play at the box after the pause behind the last favourite stops the steering for that figure until it is taken off, so the rest of the figure plays.
- A box's device is removed only after an hour of polls without the box, not after one.
- A box that told nothing about a figure's chapters is asked again an hour later or when the figure is placed anew.
- Requires Home Assistant 2026.11; tests run on pytest-homeassistant 2026.11.1.
- README in the shared layout with diagrams of the design.

### Fixed

- Chapters a box told about a creative figure no longer replace the cloud's chapters, whose IDs rearranging needs.
- A push message the integration cannot take, or any other unexpected failure, no longer ends the push channel for good.
- A box that came back after its device was removed gets its entities again without a reload.
- The fetch of a link ends with the entry when the integration is reloaded and tells the page; answers of the Media Fetcher app in an unexpected shape, and files over 200 MB, are refused with a message instead of an error; only audio content types are passed on.
- Only http and https links with a host, of at most 2048 characters, are fetched.
- The integration loads on installations without the Supervisor's packages.
- The battery clock stops while the push channel is gone, so a lost channel no longer inflates the hours of a charge.
- A battery status such as "charged" no longer counts as charging.

## [0.1.0] - 2026-11-04

First version, for the private test phase.

### Added

- Sign-in with the account of the app; only a refresh token is stored, never the password. The token is renewed and rotated automatically; a refused token asks for a new sign-in.
- One device per box with a connectivity sensor. The Toniebox 2 adds battery, charging, a media player (play, pause, volume, chapters, seeking within a chapter) and a figure event (placed, removed).
- Live state of the Toniebox 2 through the cloud's push channel; the classic box is read from the REST API every 5 minutes.
- Sleep timer of the Toniebox 2 as the actions `set_sleep_timer` and `clear_sleep_timer` on its media player; turning the player off puts the box to sleep.
- Chapters of bought figures come from the library of the app; their lengths, which the library does not tell, are learned from the box the figure stands on and kept.
- Listening time as daily sums per figure and box, kept in the integration's own store (option, on by default).
- How long a charge of the Toniebox 2 lasts: discharge cycles with hours switched on, percent used and the projection per full charge.
- A page for administrators with the boxes, the figures with their chapters and the listening statistics.
- The chapters of Creative-Tonies are managed on the page: audio files are uploaded as chapters, chapters are moved and removed in an edit mode and saved in one go, and chapters the cloud dropped while converting are named.
- A chapter from a YouTube link: the Media Fetcher app fetches the audio, the integration uploads it named after the video, and the page shows the progress. Without the app the button stays grey and says so.
- Favourite chapters of bought figures: stars on the page and a switch per figure; while it is on, a Toniebox 2 is steered past every other chapter, backwards to the previous favourite, and paused after the last one.
- Diagnostics without tokens, names, addresses or listening data.
