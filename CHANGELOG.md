# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/n-schilling/ha-storybox-plus/releases/tag/v0.1.0
