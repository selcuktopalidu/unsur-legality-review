"""Working-day arithmetic for Turkish time limits.

Only the holidays needed for the examples are listed.  28 October is a
half-day holiday (Law No. 2429, Art. 1: the national holiday begins at
13:00); whether it counts as a working day is left open (IR-2) and both
readings are computed.
"""
from datetime import date, timedelta

FULL_HOLIDAYS = {date(2026, 1, 1), date(2026, 4, 23), date(2026, 5, 1), date(2026, 5, 19),
                 date(2026, 7, 15), date(2026, 8, 30), date(2026, 10, 29)}
HALF_DAYS = {date(2026, 10, 28)}


def is_working_day(d: date, half_day_counts: bool) -> bool:
    if d.weekday() >= 5 or d in FULL_HOLIDAYS:
        return False
    if d in HALF_DAYS:
        return half_day_counts
    return True


def nth_working_day(received: date, n: int, half_day_counts: bool) -> date:
    """The n-th working day after the day of receipt (IR-1: the period starts the next working day)."""
    d, count = received, 0
    while count < n:
        d += timedelta(days=1)
        if is_working_day(d, half_day_counts):
            count += 1
    return d


def working_days_late(deadline: date, done: date, half_day_counts: bool) -> int:
    d, late = deadline, 0
    while d < done:
        d += timedelta(days=1)
        if is_working_day(d, half_day_counts):
            late += 1
    return late


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)
