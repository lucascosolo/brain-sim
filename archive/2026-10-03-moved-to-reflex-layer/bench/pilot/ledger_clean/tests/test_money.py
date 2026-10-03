from decimal import Decimal

import pytest

from ledger.money import format_amount, parse_amount, split_evenly


def test_parse_plain_and_grouped():
    assert parse_amount("12.5") == Decimal("12.50")
    assert parse_amount("1,234.56") == Decimal("1234.56")


def test_parse_currency_and_negative_forms():
    assert parse_amount("$5") == Decimal("5.00")
    assert parse_amount("(12.00)") == Decimal("-12.00")
    assert parse_amount("-3") == Decimal("-3.00")


def test_parse_rejects_garbage():
    for bad in ["", "abc", "1.2.3", "12a"]:
        with pytest.raises(ValueError):
            parse_amount(bad)


def test_format_amount():
    assert format_amount(Decimal("1234.5")) == "1,234.50"
    assert format_amount(Decimal("-7")) == "(7.00)"


def test_split_evenly_sums_exactly():
    parts = split_evenly(Decimal("10.00"), 3)
    assert parts == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]
    assert sum(parts) == Decimal("10.00")


def test_split_evenly_rejects_zero_parts():
    with pytest.raises(ValueError):
        split_evenly(Decimal("1.00"), 0)
