"""Orders: lines, totals with tax, placement against inventory."""
from decimal import Decimal

from shop import pricing, tax
from shop.inventory import Inventory
from shop.util import money


class Order:
    def __init__(self, region: str):
        self.region = region
        self.lines: list[tuple[str, int]] = []
        self.placed = False

    def add(self, sku: str, qty: int) -> "Order":
        self.lines.append((sku, qty))
        return self

    def subtotal(self) -> Decimal:
        return money(sum((pricing.line_total(s, q) for s, q in self.lines), Decimal("0")))

    def total(self) -> Decimal:
        subtotal = self.subtotal()
        return money(subtotal + tax.tax_on(subtotal, self.region))

    def place(self, inv: Inventory) -> None:
        reserved = []
        try:
            for sku, qty in self.lines:
                inv.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            for sku, qty in reserved:
                inv.release(sku, qty)
            raise
        for sku, qty in self.lines:
            inv.commit(sku, qty)
        self.placed = True
