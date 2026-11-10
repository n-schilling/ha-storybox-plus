"""Constants for Storybox Plus."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "storybox_plus"
MANUFACTURER = "tonies"

# Config entry data: only the refresh token and the account's UUID, never the password
CONF_REFRESH_TOKEN = "refresh_token"
CONF_USER_ID = "user_id"

# Options
CONF_ANALYTICS = "analytics"
DEFAULT_ANALYTICS = True

# The REST API is read every 5 minutes: it tells about new figures, chapters,
# names and the classic box; the live state of the Toniebox 2 comes by push.
UPDATE_INTERVAL = timedelta(minutes=5)
RETRY_INTERVAL = timedelta(minutes=1)
# A box missing from this many polls in a row (an hour) has left the account;
# one answer without it may be a hiccup of the cloud
STALE_AFTER_POLLS = 12
UNAVAILABLE_AFTER_FAILURES = 3
# A classic box tells the cloud nothing but when it was last there
CLASSIC_ONLINE_WINDOW = timedelta(minutes=30)

STORAGE_VERSION = 1
ANALYTICS_KEEP_DAYS = 730

# Event entity
EVENT_FIGURE_PLACED = "placed"
EVENT_FIGURE_REMOVED = "removed"
ATTR_TONIE_ID = "tonie_id"
ATTR_TONIE = "tonie"

# Actions of the media player
SERVICE_SET_SLEEP_TIMER = "set_sleep_timer"
SERVICE_CLEAR_SLEEP_TIMER = "clear_sleep_timer"
ATTR_MINUTES = "minutes"

# The page
FRONTEND_URL_BASE = "/storybox_plus"
PANEL_FILENAME = "storybox-plus-panel.js"
PANEL_ELEMENT = "storybox-plus-panel"
PANEL_URL_PATH = "storybox-plus"
PANEL_TITLE = "Storybox Plus"
PANEL_ICON = "mdi:teddy-bear"
