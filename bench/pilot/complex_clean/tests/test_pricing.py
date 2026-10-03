from decimal import Decimal

from shop.pricing import line_total, quantity_discount


def test_no_discount_below_ten():
    assert line_total("apple", 9) == Decimal("4.50")


def test_tier_discounts():
    assert quantity_discount(10) == Decimal("0.05")
    assert quantity_discount(75) == Decimal("0.10")
    assert line_total("melon", 100) == Decimal("272.00")
