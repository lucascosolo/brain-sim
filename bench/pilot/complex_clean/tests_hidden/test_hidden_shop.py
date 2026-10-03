from decimal import Decimal

import pytest

from shop import tax
from shop.inventory import Inventory
from shop.orders import Order
from shop.pricing import line_total


def test_rates_are_fractions():
    for r in ("CA", "NY", "TX", "OR"):
        assert Decimal("0") <= tax.rate_for(r) < Decimal("1")


def test_tax_on_directly():
    assert tax.tax_on(Decimal("100.00"), "ca") == Decimal("7.25")
    assert tax.tax_on(Decimal("10.00"), "TX") == Decimal("0.62")


def test_total_texas_large_order():
    o = Order("TX").add("melon", 50).add("apple", 10)
    assert o.subtotal() == Decimal("148.75")
    assert o.total() == Decimal("158.05")


def test_line_total_rejects_negative():
    with pytest.raises(ValueError):
        line_total("fig", -1)


def test_commit_reduces_stock_once():
    inv = Inventory({"fig": 5})
    inv.reserve("fig", 2)
    inv.commit("fig", 2)
    assert inv.available("fig") == 3


def test_unknown_region_raises():
    with pytest.raises(KeyError):
        tax.rate_for("ZZ")
