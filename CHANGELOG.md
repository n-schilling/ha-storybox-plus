# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-10

### Added

- The page shows the version of the integration at its bottom, taken from the manifest; a test deployment (`scripts/deploy.sh`) adds its commit.
- The device of a box that left the account can be removed by hand.
- Page checks in a real browser against a throwaway Home Assistant with a made-up cloud, also as a CI job; they make the README's screenshots.

### Changed

- The page is built from Home Assistant's own elements: top app bar with the menu button, cards, buttons, icon buttons, alerts, a switch for the favourites and forms for the search and the link. The header has the sidebar's colour like the settings pages.
- The script of the page is loaded with a hash of its content, so a changed page is never served from a cache.
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

[0.2.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.2.0
[0.1.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.1.0
