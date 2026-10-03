from decimal import Decimal

import pytest

from ledger.invoice import Invoice


def make():
    inv = Invoice()
    inv.add("A", 2, Decimal("3.25"))
    inv.add("B", 1, Decimal("4.00"))
    return inv


def test_subtotal_and_merge_of_same_line():
    inv = make()
    inv.add("A", 1, Decimal("3.25"))
    assert len(inv.lines) == 2
    assert inv.subtotal() == Decimal("13.75")


def test_add_rejects_non_positive_quantity():
    with pytest.raises(ValueError):
        make().add("C", 0, Decimal("1.00"))


def test_tax_without_discount():
    inv = make()
    inv.tax_rate = Decimal("0.05")
    assert inv.subtotal() == Decimal("10.50")
    assert inv.tax() == Decimal("0.53")
    assert inv.total() == Decimal("11.03")


def test_discount_reduces_taxable_amount():
    inv = make()
    inv.discount_rate = Decimal("0.10")
    inv.tax_rate = Decimal("0.20")
    assert inv.discount() == Decimal("1.05")
    assert inv.tax() == Decimal("1.89")
    assert inv.total() == Decimal("11.34")
