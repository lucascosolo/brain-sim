import datetime as dt

import pytest

from ledger.dates import add_months, days_between, is_overdue, parse_date


def test_parse_date():
    assert parse_date(" 2026-02-03 ") == dt.date(2026, 2, 3)
    with pytest.raises(ValueError):
        parse_date("03/02/2026")


def test_add_months_simple_and_year_wrap():
    assert add_months(dt.date(2026, 1, 15), 1) == dt.date(2026, 2, 15)
    assert add_months(dt.date(2026, 11, 15), 3) == dt.date(2027, 2, 15)


def test_add_months_clamps_to_month_end():
    assert add_months(dt.date(2026, 1, 31), 1) == dt.date(2026, 2, 28)
    assert add_months(dt.date(2028, 1, 31), 1) == dt.date(2028, 2, 29)


def test_overdue_with_grace():
    due = dt.date(2026, 3, 1)
    assert not is_overdue(due, dt.date(2026, 3, 1))
    assert is_overdue(due, dt.date(2026, 3, 2))
    assert not is_overdue(due, dt.date(2026, 3, 4), grace_days=3)


def test_days_between():
    assert days_between(dt.date(2026, 3, 1), dt.date(2026, 3, 11)) == 10
