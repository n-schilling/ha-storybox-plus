# The cloud of the boxes

What this package knows about the manufacturer's cloud. The API is not
documented for third parties; the facts below were learned from the official
app and from the issues of the community project
[HA-Toniebox](https://github.com/git4sim/HA-Toniebox) (MIT). The code here is
written from scratch and imports nothing from Home Assistant.

## Sign-in (`auth.py`)

- Keycloak at `login.tonies.com`, realm `tonies`, client `meine-tonies`, Resource Owner Password flow.
- The access token lives **300 s**. The refresh token is rotated with every refresh; only it is stored. How long a refresh token survives unused is not documented; the login asks for `offline_access` first (a token that does not expire while unused) and falls back to a plain session if the client is not allowed offline tokens. `refresh_expires_in: 0` marks an offline token.
- Wrong credentials: 401 `invalid_grant`. Expired refresh token: 400 `invalid_grant`. Both end in `CloudAuthError`, which the integration turns into a reauthentication flow.

## REST and GraphQL (`rest.py`)

- Base URL `https://api.prod.tcs.toys/v2`. `api.tonie.cloud/v2` is a CDN in front of it that lacks some endpoints (`/contenttonies`, `/discs`).
- `GET /me` → `uuid` (the user name of the push channel). `GET /households`, `GET /households/{id}/tonieboxes`, `GET /households/{id}/creativetonies`; some lists come wrapped (`results`, `households`, `creativetonies`).
- Boxes: tell the generation by the feature flag **`tngSettings`**, not by the field `generation` (`classic`, `rosered`, `tng`, `tb2g2`, …): the flag says what the box can do. `lastSeen` is camelCase. A classic box reports no figure and no battery; it is online while `lastSeen` is recent.
- Content figures and discs come from GraphQL (`POST /graphql`, fields `myContentTonies` and `myDiscs`, Relay pagination with `first`/`after` and `pageInfo`; without paging the lists stop at 100). Creative figures come from REST and carry `secondsRemaining`, `secondsPresent`, `chaptersRemaining`.
- Chapters of a creative figure are replaced with `PATCH /households/{id}/creativetonies/{id}` and a full `chapters` list; a chapter needs `file` (the file ID).
- Upload (not implemented yet): `POST /file` returns a file ID and a presigned S3 POST; the audio goes to S3 with the form fields before the file and without the bearer token.
- Figure pictures: use the URLs the API returns; fixed CDN URLs break (403). Box pictures: `GET /box-item-previews` per `bleColorId`.

## Push channel (`push.py`)

- MQTT 5 over WebSocket at `wss://ici.tonie.cloud:443/`, user name = the account's UUID, password = the access token. The broker drops the connection when the token expires and refuses the old token on reconnect (`Bad user name or password`): refresh before every connect, never log the refusal in a loop.
- Topics `external/toniebox/{MAC}/…` with the MAC in upper case:
  - `metrics/battery` `{percent, raw, status}`; a box that shuts down sends only nulls.
  - `online-state` `{onlineState: "online"|"offline"}`.
  - `playback/state` `{tonie: "<id>", paused, chapter, chapterUntilMs, chapterDuration, chapterPositionMs, ended, downloading, blocked}`; sent again at every chapter change; an **empty payload** means the figure was taken off. While playing the position follows from `chapterUntilMs`, while paused from `chapterPositionMs`.
  - `volume/state` `{level (0..13), hardwarePercentage}`.
  - `app-reply/bedtime-state` `{stl: {state, duration, until, alarm}}`.
  - `metrics/headphones` and `settings-applied` exist and are not used.
- Commands go to `external/toniebox/{MAC}/app-control/…`:
  - `playback` `{action: "start"|"pause"|"setPosition", chapter, ms}`.
  - `volume` `{level}`.
  - `stl` `{state: "on"|"off", duration}`; `duration` is a uint16 of seconds (at most 1092 minutes, more wraps around). The alarm settings live in the same payload (`oneTimeAlarm`, `alarm {morningLight, tone, volume}`), not in the REST API.
  - `sleep` `{}` after a short `stl` puts the box to sleep; it cannot be woken through the cloud.
- `aiomqtt` is used instead of paho's threads, which raced in the community project.
