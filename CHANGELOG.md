# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

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

[0.3.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.3.0
[0.2.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.2.0
[0.1.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.1.0
