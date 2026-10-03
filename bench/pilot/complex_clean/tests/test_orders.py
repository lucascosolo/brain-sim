from decimal import Decimal

import pytest

from shop.inventory import Inventory, OutOfStock
from shop.orders import Order


def test_total_with_tax_ca():
    o = Order("CA").add("apple", 4).add("pear", 2)
    assert o.subtotal() == Decimal("3.50")
    assert o.total() == Decimal("3.75")


def test_total_oregon_no_tax():
    assert Order("or").add("fig", 3).total() == Decimal("3.30")


def test_place_commits_stock():
    inv = Inventory({"apple": 10})
    Order("NY").add("apple", 4).place(inv)
    assert inv.available("apple") == 6


def test_place_rolls_back_on_shortage():
    inv = Inventory({"apple": 10, "pear": 1})
    with pytest.raises(OutOfStock):
        Order("NY").add("apple", 4).add("pear", 2).place(inv)
    assert inv.available("apple") == 10
