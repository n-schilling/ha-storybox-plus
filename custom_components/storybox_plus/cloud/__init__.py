"""Access to the cloud of the boxes, independent of Home Assistant.

Nothing in this package imports Home Assistant, so it can be tested on its
own and used from a script. The integration passes in the HTTP session and
the TLS context it wants used.
"""

from .auth import Auth, TokenSet
from .errors import CloudAuthError, CloudConnectionError, CloudError, CloudResponseError
from .models import (
    VOLUME_LEVELS,
    WEEKDAYS,
    Alarm,
    Battery,
    BedtimeSchedule,
    Box,
    BoxSettings,
    Chapter,
    CloudNotice,
    Generation,
    Headphones,
    Household,
    Library,
    Member,
    Playback,
    SleepTimer,
    Tonie,
    TonieDetails,
    TonieKind,
    Tune,
    Volume,
)
from .push import (
    SLEEP_TIMER_MAX_MINUTES,
    SLEEP_TIMER_MAX_SECONDS,
    TOPIC_BATTERY,
    TOPIC_HEADPHONES,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    PushClient,
    PushEvent,
)
from .rest import CloudClient

__all__ = [
    "SLEEP_TIMER_MAX_MINUTES",
    "SLEEP_TIMER_MAX_SECONDS",
    "TOPIC_BATTERY",
    "TOPIC_HEADPHONES",
    "TOPIC_ONLINE",
    "TOPIC_PLAYBACK",
    "TOPIC_SLEEP_TIMER",
    "TOPIC_VOLUME",
    "VOLUME_LEVELS",
    "WEEKDAYS",
    "Alarm",
    "Auth",
    "Battery",
    "BedtimeSchedule",
    "Box",
    "BoxSettings",
    "Chapter",
    "CloudAuthError",
    "CloudClient",
    "CloudConnectionError",
    "CloudError",
    "CloudNotice",
    "CloudResponseError",
    "Generation",
    "Headphones",
    "Household",
    "Library",
    "Member",
    "Playback",
    "PushClient",
    "PushEvent",
    "SleepTimer",
    "TokenSet",
    "Tonie",
    "TonieDetails",
    "TonieKind",
    "Tune",
    "Volume",
]
