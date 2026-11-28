"""The alarm of the bedtime schedules: the integration arms it every evening.

A Toniebox 2 keeps one timer. The alarm of a bedtime schedule rings when
that timer ends, and the app arms it only once: the schedule alone makes no
box ring again. So the integration arms it itself, as soon as the box is
online and the next wake-up of its enabled schedules lies within the
timer's reach (about 18 hours). The alarm then replaces a running sleep
timer, and a sleep timer would replace the alarm, so the integration's own
sleep timer actions are refused while an alarm is due.

What is armed is read back from the box (app-reply/bedtime-state), never
assumed; a box that did not take the command is asked again a little later.
An alarm the integration armed for a wake-up that no schedule wants any
more, because a schedule was switched off or changed, is cleared again.

The wake-up light (the app's "Lichtwecker") is one alarm at a time of its
own, set on the page or by an action and kept in the preferences. It goes the
same way: of it and the schedules, the alarm that rings first is armed, the
other one after it has rung. Once its time has passed, it is forgotten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

from .cloud import (
    ALARM_TONES,
    SLEEP_TIMER_MAX_SECONDS,
    WEEKDAYS,
    Alarm,
    BedtimeSchedule,
    SleepTimer,
)

# An alarm is armed at most this long before it rings: the box counts the timer
# in an unsigned 16-bit number of seconds
ARM_WINDOW = timedelta(seconds=SLEEP_TIMER_MAX_SECONDS)
# The box ignores commands for a moment after it came online
SETTLE = timedelta(seconds=30)
# The box drops an alarm set less than this far ahead: the app asks for five
# minutes as well. One closer than that is not sent, and a wake-up light needs it
LEAD = timedelta(minutes=5)
# A box that did not confirm an alarm is asked again after this long
RETRY = timedelta(minutes=2)
# How often a step is sent to a box that does not confirm it, per time it comes online
TRIES = 3
# The box reports the end of its timer to the second; this much difference still counts as armed
TOLERANCE = timedelta(minutes=2)
# The names of the alarm tones in actions and translations, in the app's order
TONE_NAMES = ("morning_glow", "birdsong", "sound_hopper", "wake_up_call", "good_morning_beat")
TONE_BY_NAME = dict(zip(TONE_NAMES, ALARM_TONES, strict=True))
TONE_NAME = dict(zip(ALARM_TONES, TONE_NAMES, strict=True))


@dataclass(frozen=True, slots=True)
class OneTimeAlarm:
    """The wake-up light: one alarm at a time of its own (aware), with how it rings."""

    at: datetime
    alarm: Alarm


@dataclass(frozen=True, slots=True)
class NextAlarm:
    """The next wake-up of a box: of a schedule, or of the wake-up light (schedule None)."""

    at: datetime
    alarm: Alarm
    schedule: BedtimeSchedule | None = None


type Step = tuple[Literal["arm"], NextAlarm] | tuple[Literal["clear"], None]


def next_alarm(
    schedules: tuple[BedtimeSchedule, ...] | None,
    now: datetime,
    once: OneTimeAlarm | None = None,
) -> NextAlarm | None:
    """Return the next wake-up after now: the enabled schedules with an alarm and the wake-up light.

    ``now`` carries the box's time zone, because the times of the schedules
    are local to the box. The days of a schedule are the days of the
    wake-up. Of a schedule and the wake-up light at the same minute, the
    wake-up light counts.
    """
    found: NextAlarm | None = (
        NextAlarm(once.at, once.alarm) if once is not None and once.at > now else None
    )
    for schedule in schedules or ():
        if not (schedule.enabled and schedule.alarm_enabled and schedule.wakeup_time):
            continue
        hour, minute = (int(p) for p in schedule.wakeup_time.split(":"))
        for offset in range(8):
            day = now.date() + timedelta(days=offset)
            if WEEKDAYS[day.weekday()] not in schedule.days:
                continue
            at = datetime.combine(day, time(hour, minute), tzinfo=now.tzinfo)
            if at > now:
                if found is None or at < found.at:
                    found = NextAlarm(at, schedule.alarm, schedule)
                break
    return found


def next_at(clock: time, now: datetime) -> datetime:
    """Return the next time the clock shows that time, in now's zone: today, or tomorrow."""
    at = datetime.combine(now.date(), clock.replace(tzinfo=None), tzinfo=now.tzinfo)
    return at if at > now else at + timedelta(days=1)


def asleep(schedules: tuple[BedtimeSchedule, ...] | None, now: datetime) -> bool:
    """Return whether now lies within a bedtime: from the sleep time to the wake-up of an enabled schedule.

    ``now`` carries the box's time zone. The days of a schedule are the days
    of the wake-up, so a bedtime that begins in the evening belongs to the
    day after.
    """
    for schedule in schedules or ():
        if not schedule.enabled:
            continue
        sleep, wakeup = _clock(schedule.sleep_time), _clock(schedule.wakeup_time)
        if sleep is None or wakeup is None or sleep == wakeup:
            # Neither a time nor a span: an alarm alone is no bedtime
            continue
        clock = now.time().replace(tzinfo=None)
        today = WEEKDAYS[now.weekday()] in schedule.days
        tomorrow = WEEKDAYS[(now.weekday() + 1) % 7] in schedule.days
        if sleep < wakeup:
            if today and sleep <= clock < wakeup:
                return True
        elif (tomorrow and clock >= sleep) or (today and clock < wakeup):
            return True
    return False


def _clock(value: str | None) -> time | None:
    """Read "H:MM", "HH:MM" or "HH:MM:SS"; None for anything else."""
    try:
        hour, minute = (int(part) for part in (value or "").split(":")[:2])
        return time(hour, minute)
    except ValueError:
        return None


def due(
    schedules: tuple[BedtimeSchedule, ...] | None,
    now: datetime,
    once: OneTimeAlarm | None = None,
) -> NextAlarm | None:
    """Return the next alarm if it is close enough to be armed now."""
    alarm = next_alarm(schedules, now, once)
    if alarm is None or alarm.at - now > ARM_WINDOW:
        return None
    return alarm


def armed_for(timer: SleepTimer | None, at: datetime) -> bool:
    """Return whether the box's timer carries an alarm that rings at that time."""
    return (
        timer is not None
        and timer.running
        and timer.alarm is not None
        and timer.until is not None
        and abs(timer.until - at) <= TOLERANCE
    )


def decide(
    alarm: NextAlarm | None,
    timer: SleepTimer | None,
    armed_by_us: datetime | None,
) -> Step | None:
    """What the box needs: the due alarm armed, a stale alarm of ours cleared, or nothing.

    ``armed_by_us`` is the wake-up the integration armed last for this box.
    An alarm someone else armed (the app) is left alone unless an alarm of
    ours (a schedule's or the wake-up light) is due, which then takes its place.
    """
    if alarm is not None:
        return None if armed_for(timer, alarm.at) else ("arm", alarm)
    if armed_by_us is not None and armed_for(timer, armed_by_us):
        return ("clear", None)
    return None
