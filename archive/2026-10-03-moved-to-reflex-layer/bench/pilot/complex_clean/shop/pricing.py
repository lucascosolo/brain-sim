"""Unit prices and quantity discounts."""
from decimal import Decimal

from shop.util import clamp, money

CATALOG = {
    "apple": Decimal("0.50"),
    "pear": Decimal("0.75"),
    "melon": Decimal("3.20"),
    "fig": Decimal("1.10"),
}

# (minimum quantity, discount fraction), highest threshold first
TIERS = [(100, Decimal("0.15")), (50, Decimal("0.10")), (10, Decimal("0.05"))]


def unit_price(sku: str) -> Decimal:
    return CATALOG[sku]


def quantity_discount(qty: int) -> Decimal:
    for threshold, frac in TIERS:
        if qty >= threshold:
            return frac
    return Decimal("0")


def line_total(sku: str, qty: int) -> Decimal:
    if qty < 0:
        raise ValueError("quantity must be non-negative")
    gross = unit_price(sku) * qty
    discount = clamp(quantity_discount(qty), Decimal("0"), Decimal("0.5"))
    return money(gross * (1 - discount))
