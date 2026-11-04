"""Access to the cloud of the boxes, independent of Home Assistant.

Nothing in this package imports Home Assistant, so it can be tested on its
own and used from a script. The integration passes in the HTTP session and
the TLS context it wants used.
"""

from .auth import Auth, TokenSet
from .errors import CloudAuthError, CloudConnectionError, CloudError, CloudResponseError
from .models import (
    VOLUME_LEVELS,
    Battery,
    Box,
    Chapter,
    Generation,
    Household,
    Library,
    Playback,
    SleepTimer,
    Tonie,
    TonieDetails,
    TonieKind,
    Volume,
)
from .push import (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    PushClient,
    PushEvent,
)
from .rest import CloudClient

__all__ = [
    "TOPIC_BATTERY",
    "TOPIC_ONLINE",
    "TOPIC_PLAYBACK",
    "TOPIC_SLEEP_TIMER",
    "TOPIC_VOLUME",
    "VOLUME_LEVELS",
    "Auth",
    "Battery",
    "Box",
    "Chapter",
    "CloudAuthError",
    "CloudClient",
    "CloudConnectionError",
    "CloudError",
    "CloudResponseError",
    "Generation",
    "Household",
    "Library",
    "Playback",
    "PushClient",
    "PushEvent",
    "SleepTimer",
    "TokenSet",
    "Tonie",
    "TonieDetails",
    "TonieKind",
    "Volume",
]
