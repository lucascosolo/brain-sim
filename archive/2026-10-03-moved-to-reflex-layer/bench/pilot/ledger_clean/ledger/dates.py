import calendar
import datetime as dt


def parse_date(text):
    """Strict ISO date 'YYYY-MM-DD'."""
    try:
        return dt.date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f"not an ISO date: {text!r}") from None


def add_months(day, months):
    """Same day of month `months` later, clamped to the last day of the target month."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day.day, last))


def is_overdue(due, today, grace_days=0):
    return today > due + dt.timedelta(days=grace_days)


def days_between(start, end):
    """Whole days from start to end (negative if end is earlier)."""
    return (end - start).days
