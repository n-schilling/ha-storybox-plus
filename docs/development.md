# Storybox Plus: development

Back to the [README](../README.md).

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
scripts/check.sh
```

`scripts/check.sh` runs what CI runs: ruff, the changelog and translation checks, mypy, the tests with their coverage threshold, the page checks and hassfest in Docker (`--no-page`, `--no-hassfest` leave them out). The page check is not part of CI: run `scripts/check.sh` before a release that changes the page.

The cloud access lives in `custom_components/storybox_plus/cloud/` and imports nothing from Home Assistant, so it can be tested on its own; its README collects what is known about the API. Endpoints and payloads were learned from the official app and from the community project [HA-Toniebox](https://github.com/git4sim/HA-Toniebox) (MIT); the code here is written from scratch.

The page checks start a throwaway Home Assistant, reachable from this machine only, whose integration talks to a made-up cloud (`scripts/panel/demo_cloud.py`: one household, a Toniebox 2 that plays and confirms its alarm, a Toniebox 1, invented figures, bedtimes, listening times and charges). They drive the page in a headless browser (Home Assistant's frame with the four areas and each page's tab on every page, the header's stamp, refresh and integration button, old addresses and a change of the query alone, boxes and figures as subpages with a back arrow, settings rows with their (i) and the one save button for box settings, night mode, figure settings, the household and the preferences, bedtimes added, switched and deleted, the charge history by keyboard, search and the kind filter, favourites, rearranging, uploading and removing all chapters, a Tune laid on and taken off, a voucher refused with one error line and redeemed, content from a code, the listening summary and times with their words for screen readers, the setup steps, numbers and a comma typed back in German, counting switched off and on, the start at the setup without a loaded account, the dashboard card, phone width in dark mode, no page for non-administrators) and stop Home Assistant again. They need their own environment:

```bash
uv venv --python 3.14 .venv-panel && uv pip install --python .venv-panel/bin/python -r requirements_panel.txt
```

They use an installed Google Chrome, otherwise Playwright's Chromium (`.venv-panel/bin/python -m playwright install chromium`). The pictures in this README come from the same run:

```bash
.venv-panel/bin/python -I scripts/panel/check_panel.py --screenshots docs/screenshots
```

Releases: CI runs on `dev`; once it is green, push that commit to `main`. CI does not run again there: the release workflow checks that CI passed for the commit, then tags the version from `manifest.json` and publishes a GitHub release with its CHANGELOG section; the Marketplace offers it as an update.

For testing on a Home Assistant OS host before a release (copies the files, writes the deployed commit for the page and restarts Home Assistant):

```bash
scripts/deploy.sh <ssh-host>
```

The page shows the version and that commit at the bottom; `-dirty` marks files that differ from it.
