"""Held-out checks: copied in only after a run, to catch fixes that pass the visible tests but are wrong."""
import datetime as dt
from decimal import Decimal

from ledger.csvimport import read_invoice
from ledger.dates import add_months
from ledger.inventory import Inventory
from ledger.invoice import Invoice
from ledger.money import format_amount, parse_amount, split_evenly


def test_split_more_cases():
    assert split_evenly(Decimal("0.05"), 3) == [Decimal("0.02"), Decimal("0.02"), Decimal("0.01")]
    assert split_evenly(Decimal("9.00"), 3) == [Decimal("3.00")] * 3
    assert sum(split_evenly(Decimal("100.01"), 7)) == Decimal("100.01")


def test_parse_large_grouped_and_format_round_trip():
    assert parse_amount("12,345,678.9") == Decimal("12345678.90")
    assert format_amount(parse_amount("(1,000.5)")) == "(1,000.50)"


def test_ship_exactly_all_stock():
    inv = Inventory()
    inv.receive("A", 3)
    inv.ship("A", 3)
    assert inv.on_hand("A") == 0
    assert inv.low_stock(0) == ["A"]


def test_tax_rounding_half_up_and_after_discount():
    inv = Invoice(tax_rate=Decimal("0.05"))
    inv.add("A", 1, Decimal("0.50"))           # 0.025 tax rounds half up to 0.03
    assert inv.tax() == Decimal("0.03")
    inv2 = Invoice(discount_rate=Decimal("0.50"), tax_rate=Decimal("0.10"))
    inv2.add("A", 1, Decimal("10.00"))
    assert inv2.tax() == Decimal("0.50") and inv2.total() == Decimal("5.50")


def test_add_months_more():
    assert add_months(dt.date(2026, 3, 31), 1) == dt.date(2026, 4, 30)
    assert add_months(dt.date(2026, 5, 31), -3) == dt.date(2026, 2, 28)
    assert add_months(dt.date(2026, 12, 31), 2) == dt.date(2027, 2, 28)


def test_csv_with_negative_and_currency():
    inv = read_invoice("sku,quantity,unit_price\nA,1,$2.50\nR,1,(1.00)\n")
    assert inv.subtotal() == Decimal("1.50")
