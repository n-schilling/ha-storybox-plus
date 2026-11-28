"""The interface of the cloud as this package relies on it, and a check of it.

The cloud's API is not documented for third parties and changes with its
releases. The parsers are forgiving: a field that is gone reads as "not
there", and nothing fails loudly. So this module writes down, per read
request, the fields the integration uses with their kinds, and compares the
real answers with it.

The check only reads. It runs the client's own read methods, so the very
requests the integration sends are looked at, and it listens to what they
answer through the client's ``watch`` hook. What a box sends over the push
channel is not asked for: the key names of the messages that came by since
the channel opened are compared.

A result never carries a value of the account: only the request by its
shape (IDs replaced), field names, kinds and HTTP statuses. It can be put
into a public issue as it is.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial
import re
from typing import Any, Literal

from .errors import CloudError, CloudResponseError
from .models import CLASSIC_SETTINGS, FEATURE_SETTINGS, LIVE_SETTINGS, SETTING_FIELDS, Box
from .push import (
    TOPIC_ALARM,
    TOPIC_BATTERY,
    TOPIC_HEADPHONES,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
)
from .rest import CloudClient

type Status = Literal["ok", "changed", "failed", "empty", "unseen"]
type Spec = dict[str, tuple[str, ...]]

# Kinds of values
S = ("str",)
I = ("int",)
N = ("int", "float")
B = ("bool",)
L = ("list",)
D = ("dict",)
NULL = ("null",)

# Path segments that are words of the API; every other segment is an ID
_WORDS = frozenset(
    {
        "bedtime-schedules",
        "box-item-previews",
        "creativetonies",
        "graphql",
        "households",
        "me",
        "memberships",
        "notifications",
        "playback-info",
        "system-notifications",
        "tonieboxes",
    }
)


@dataclass(frozen=True, slots=True)
class Result:
    """What the check found for one request, or one topic of the push channel.

    ok: the answer has every field the integration uses, of the expected kind.
    changed: fields are missing or of another kind; detail names them.
    failed: the request was refused or not answered; detail names how.
    empty: the answer holds nothing to compare (an empty list).
    unseen: nothing was asked or sent that could be compared.
    """

    name: str
    status: Status
    detail: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """For the page and the store."""
        return {"name": self.name, "status": self.status, "detail": list(self.detail)}


def endpoint(method: str, path: str, body: Any = None) -> str:
    """Name a request by its shape: IDs replaced, the query string dropped.

    A GraphQL request is named by the field it asks for.
    """
    path = path.split("?", 1)[0]
    if path == "/graphql":
        query = body.get("query") if isinstance(body, dict) else None
        match = _FIELD.search(query) if isinstance(query, str) else None
        return f"GraphQL {match[1]}" if match else "GraphQL"
    parts = [p if p in _WORDS else "{id}" for p in path.strip("/").split("/")]
    return f"{method.upper()} /{'/'.join(parts)}"


def _kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _values(item: Any, path: str) -> tuple[bool, list[Any]]:
    """Return whether the path can be looked at, and the values found along it.

    ``a.b`` goes into an object, ``a[].b`` into every object of a list. A
    path whose list is empty, or whose parent object is null, cannot be
    looked at: there is nothing to compare.
    """
    head, _, rest = path.partition(".")
    many = head.endswith("[]")
    key = head.removesuffix("[]")
    if not isinstance(item, dict) or key not in item:
        return True, [_MISSING]
    value = item[key]
    if not rest:
        return True, [value]
    if many:
        if not isinstance(value, list):
            return True, [value]
        found: list[Any] = []
        for entry in value:
            if isinstance(entry, dict):
                found.extend(_values(entry, rest)[1])
        return bool(found), found
    if value is None:
        return False, []
    return _values(value, rest)


_MISSING = object()
# The first field a GraphQL query asks for
_FIELD = re.compile(r"\{\s*(\w+)")


def compare(item: Any, spec: Spec) -> list[str]:
    """Return what differs between an object and what is expected of it.

    Field names and kinds only, never a value.
    """
    if not isinstance(item, dict):
        return [f"answer is {_kind(item)}, expected an object"]
    differences: list[str] = []
    for path, kinds in spec.items():
        seen, values = _values(item, path)
        if not seen:
            continue
        if any(value is _MISSING for value in values):
            differences.append(f"{path} is missing")
            continue
        wrong = sorted({_kind(v) for v in values} - set(kinds))
        if wrong:
            differences.append(f"{path} is {'/'.join(wrong)}, expected {'/'.join(kinds)}")
    return differences


# ---------------------------------------------------------------- the REST API

_ME: Spec = {"uuid": S}
_HOUSEHOLD: Spec = {"id": S, "name": S}
_CREATIVE: Spec = {
    "id": S,
    "name": S,
    "imageUrl": S + NULL,
    "chapters": L,
    "chapters[].id": S,
    "chapters[].title": S,
    "chapters[].seconds": N,
    "chapters[].file": S,
    "secondsRemaining": N,
    "chaptersRemaining": I,
    "transcoding": B,
    "live": B,
}
_MEMBER: Spec = {"id": S, "displayName": S, "mtype": S, "isSelf": B}
_NOTICE: Spec = {"id": S, "text": S, "read": B, "ntype": S}
_SYSTEM_NOTICE: Spec = {"id": S, "translatedText": S}
_SCHEDULE: Spec = {
    "id": S,
    "name": S,
    "sleepTime": S + NULL,
    "wakeupTime": S + NULL,
    "days": L,
    "enabled": B,
    "alarmEnabled": B,
}
_PREVIEW: Spec = {"bleColorId": I + S, "thumbnail": S}
_PLAYBACK_INFO: Spec = {"status": S}
_PLAYBACK_INFO_AVAILABLE: Spec = {
    "status": S,
    "chapters": L,
    "chapters[].title": S,
    "chapters[].seconds": N,
}


def _box_spec(item: Any) -> Spec:
    """What a box must name: its settings follow from its generation and feature flags."""
    spec: Spec = {"id": S, "name": S, "features": L}
    features = item.get("features") if isinstance(item, dict) else None
    if not isinstance(features, list):
        return spec
    live = "tngSettings" in features
    if live:
        spec["macAddress"] = S
    for name, (api, allowed) in SETTING_FIELDS.items():
        if name == "name":
            continue
        if name in LIVE_SETTINGS and not live:
            continue
        if name in CLASSIC_SETTINGS and live:
            continue
        feature = FEATURE_SETTINGS.get(name)
        if feature is not None and feature not in features:
            continue
        if allowed is bool:
            spec[api] = B
        elif isinstance(allowed[0], int):
            spec[api] = I
        else:
            spec[api] = S
    return spec


def _playback_info_spec(item: Any) -> Spec:
    available = isinstance(item, dict) and item.get("status") == "available"
    return _PLAYBACK_INFO_AVAILABLE if available else _PLAYBACK_INFO


def _listed(*keys: str) -> Callable[[Any], list[Any] | None]:
    """Unwrap a list the way the client does: plain, or under one of the keys."""

    def unwrap(answer: Any) -> list[Any] | None:
        if isinstance(answer, dict):
            for key in keys:
                if isinstance(answer.get(key), list):
                    return list(answer[key])
        return list(answer) if isinstance(answer, list) else None

    return unwrap


def _single(answer: Any) -> list[Any] | None:
    return [answer]


def _graphql_households(answer: Any) -> list[Any] | None:
    data = answer.get("data") if isinstance(answer, dict) else None
    households = data.get("households") if isinstance(data, dict) else None
    if not isinstance(households, list):
        return None
    return [
        node
        for household in households
        if isinstance(household, dict)
        for node in household.get("contentTonies") or []
    ]


def _graphql_nodes(field: str) -> Callable[[Any], list[Any] | None]:
    def unwrap(answer: Any) -> list[Any] | None:
        data = answer.get("data") if isinstance(answer, dict) else None
        connection = data.get(field) if isinstance(data, dict) else None
        edges = connection.get("edges") if isinstance(connection, dict) else None
        if not isinstance(edges, list):
            return None
        return [edge.get("node") if isinstance(edge, dict) else None for edge in edges]

    return unwrap


_CONTENT: Spec = {
    "id": S,
    "title": S,
    "lock": B,
    "imageUrl": S + NULL,
    "chapters": L,
    "chapters[].name": S,
    "secondsPresent": N + NULL,
}
_DISC: Spec = {"id": S, "householdId": S, "title": S, "lock": B}
_TUNE: Spec = {
    "id": S,
    "title": S,
    "allCreativeTonies": B,
    "compatibleTonies": L,
    "myTune": D,
    "myTune.id": S,
    "myTune.assignCountRemaining": I + NULL,
    "myTune.assignedTonies": L,
}


@dataclass(frozen=True, slots=True)
class _Request:
    """One read request: how its answer lists what to compare, and what is expected."""

    items: Callable[[Any], list[Any] | None]
    spec: Callable[[Any], Spec]


def _fixed(spec: Spec) -> Callable[[Any], Spec]:
    return lambda _item: spec


# Every read request of the integration, by its shape
REQUESTS: Mapping[str, _Request] = {
    "GET /me": _Request(_single, _fixed(_ME)),
    "GET /households": _Request(_listed("households", "results"), _fixed(_HOUSEHOLD)),
    "GET /households/{id}/tonieboxes": _Request(_listed("results"), _box_spec),
    "GET /households/{id}/creativetonies": _Request(
        _listed("creativetonies", "results"), _fixed(_CREATIVE)
    ),
    "GET /households/{id}/memberships": _Request(_listed("results"), _fixed(_MEMBER)),
    "GET /households/{id}/tonieboxes/{id}/bedtime-schedules": _Request(
        _listed("results", "bedtimeSchedules"), _fixed(_SCHEDULE)
    ),
    "GET /notifications": _Request(_listed("results", "notifications"), _fixed(_NOTICE)),
    "GET /system-notifications": _Request(
        _listed("results", "notifications"), _fixed(_SYSTEM_NOTICE)
    ),
    "GET /box-item-previews": _Request(_listed("results"), _fixed(_PREVIEW)),
    "GET /playback-info/{id}/{id}": _Request(_single, _playback_info_spec),
    "GraphQL households": _Request(_graphql_households, _fixed(_CONTENT)),
    "GraphQL myDiscs": _Request(_graphql_nodes("myDiscs"), _fixed(_DISC)),
    "GraphQL tunesItems": _Request(_graphql_nodes("tunesItems"), _fixed(_TUNE)),
}

# The version answers plain text and without a sign-in; the client reads it its own way
VERSION = "GET /version"
DISCS = "GraphQL myDiscs"

# ---------------------------------------------------------------- the push channel

# Per topic the keys a message must carry, and groups of which one must be there
TOPICS: Mapping[str, tuple[frozenset[str], tuple[frozenset[str], ...]]] = {
    TOPIC_BATTERY: (frozenset({"percent", "status"}), ()),
    TOPIC_ONLINE: (frozenset({"onlineState"}), ()),
    TOPIC_PLAYBACK: (
        frozenset({"tonie", "chapter", "paused", "ended", "downloading", "chapterDuration"}),
        (frozenset({"chapterUntilMs", "chapterPositionMs"}),),
    ),
    TOPIC_VOLUME: (frozenset({"level"}), ()),
    TOPIC_SLEEP_TIMER: (frozenset({"stl"}), ()),
    TOPIC_HEADPHONES: (frozenset({"connected"}), ()),
    TOPIC_ALARM: (frozenset({"tone"}), ()),
}


def check_topics(seen: Mapping[str, frozenset[str]]) -> list[Result]:
    """Compare the keys of the last message per topic with what is expected."""
    results: list[Result] = []
    for topic, (needed, one_of) in TOPICS.items():
        name = f"Push {topic}"
        keys = seen.get(topic)
        if keys is None:
            results.append(Result(name, "unseen"))
            continue
        missing = [f"{key} is missing" for key in sorted(needed - keys)]
        missing.extend(
            f"none of {', '.join(sorted(group))}" for group in one_of if not group & keys
        )
        results.append(Result(name, "changed" if missing else "ok", tuple(missing)))
    return results


# ---------------------------------------------------------------- the check


def _judge(name: str, answers: list[Any]) -> Result:
    """Compare every answer a request got with what is expected of it."""
    request = REQUESTS[name]
    differences: list[str] = []
    compared = 0
    for answer in answers:
        items = request.items(answer)
        if items is None:
            if name == DISCS:
                # An account without discs gets an error for an answer, and always has
                continue
            differences.append(f"answer is {_kind(answer)}, not the list it was")
            continue
        for item in items:
            compared += 1
            for difference in compare(item, request.spec(item)):
                if difference not in differences:
                    differences.append(difference)
    if differences:
        return Result(name, "changed", tuple(differences))
    return Result(name, "ok" if compared else "empty")


def _failure(err: CloudError) -> str:
    """Name a failed request without its path, which carries IDs."""
    if isinstance(err, CloudResponseError):
        return f"answered {err.status}"
    return type(err).__name__


async def async_check(
    client: CloudClient,
    figures_on_boxes: Iterable[tuple[str, str, int]] = (),
    topics: Mapping[str, frozenset[str]] | None = None,
) -> list[Result]:
    """Read everything the integration reads and compare it with what is expected.

    ``figures_on_boxes`` names (box, figure, content version) for the
    figures that stand on boxes: the chapters of a figure are told only for
    one a box has in front of it. ``topics`` are the keys of the push
    messages seen. Nothing in the cloud is changed.
    """
    answers: dict[str, list[Any]] = {}
    failed: dict[str, str] = {}

    def watch(method: str, path: str, body: Any, answer: Any) -> None:
        answers.setdefault(endpoint(method, path, body), []).append(answer)

    async def step(names: tuple[str, ...], call: Callable[[], Awaitable[Any]]) -> Any:
        """Run one read; a failure counts for the requests it stands for that got no answer."""
        try:
            return await call()
        except CloudError as err:
            for name in names:
                if name not in answers:
                    failed[name] = _failure(err)
            return None

    before = client.watch
    client.watch = watch
    try:
        await step(("GET /me",), client.async_user_id)
        households = await step(("GET /households",), client.async_households) or []
        boxes: list[Box] = []
        for household in households:
            boxes.extend(
                await step(
                    ("GET /households/{id}/tonieboxes",),
                    partial(client.async_boxes, household.id),
                )
                or []
            )
            await step(
                ("GET /households/{id}/creativetonies",),
                partial(client.async_creative_tonies, household.id),
            )
            await step(
                ("GET /households/{id}/memberships",),
                partial(client.async_members, household.id),
            )
        await step(("GraphQL households",), client.async_content_tonies)
        await step(("GraphQL myDiscs",), client.async_discs)
        await step(("GraphQL tunesItems",), client.async_tunes)
        await step(("GET /notifications", "GET /system-notifications"), client.async_notices)
        await step(("GET /box-item-previews",), client.async_box_pictures)
        for box in boxes:
            if box.alarm_capable:
                await step(
                    ("GET /households/{id}/tonieboxes/{id}/bedtime-schedules",),
                    partial(client.async_bedtime_schedules, box),
                )
        for box_id, tonie_id, version in figures_on_boxes:
            await step(
                ("GET /playback-info/{id}/{id}",),
                partial(client.async_playback_info, box_id, tonie_id, version),
            )
        version_failure: str | None = None
        try:
            await client.async_backend_version()
        except CloudError as err:
            version_failure = _failure(err)
    finally:
        client.watch = before

    results: list[Result] = []
    for name in REQUESTS:
        if name in answers:
            results.append(_judge(name, answers[name]))
        elif name in failed:
            results.append(Result(name, "failed", (failed[name],)))
        else:
            results.append(Result(name, "unseen"))
    results.append(
        Result(VERSION, "failed", (version_failure,)) if version_failure else Result(VERSION, "ok")
    )
    if topics is not None:
        results.extend(check_topics(topics))
    return results


def passed(results: Iterable[Result]) -> bool:
    """Return whether nothing changed and nothing failed; empty and unseen say nothing."""
    return all(result.status not in ("changed", "failed") for result in results)
