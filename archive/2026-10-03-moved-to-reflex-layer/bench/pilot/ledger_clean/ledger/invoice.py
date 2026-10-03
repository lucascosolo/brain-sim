from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from ledger.money import CENT


@dataclass
class Line:
    sku: str
    quantity: int
    unit_price: Decimal

    def total(self):
        return (self.unit_price * self.quantity).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Invoice:
    lines: list = field(default_factory=list)
    discount_rate: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")

    def add(self, sku, quantity, unit_price):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        for line in self.lines:
            if line.sku == sku and line.unit_price == unit_price:
                line.quantity += quantity
                return line
        line = Line(sku, quantity, unit_price)
        self.lines.append(line)
        return line

    def subtotal(self):
        return sum((line.total() for line in self.lines), Decimal("0.00"))

    def discount(self):
        return (self.subtotal() * self.discount_rate).quantize(CENT, rounding=ROUND_HALF_UP)

    def tax(self):
        return ((self.subtotal() - self.discount()) * self.tax_rate).quantize(CENT, rounding=ROUND_HALF_UP)

    def total(self):
        return self.subtotal() - self.discount() + self.tax()
