"""Sales tax rates by region, as fractions of the taxable amount."""
from decimal import Decimal

RATES = {
    "CA": Decimal("0.0725"),
    "NY": Decimal("0.04"),
    "TX": Decimal("0.0625"),
    "OR": Decimal("0"),
}


def rate_for(region: str) -> Decimal:
    """The tax rate for a region as a fraction (0.0725, not 7.25). Unknown regions raise KeyError."""
    return RATES[region.upper()]


def tax_on(amount: Decimal, region: str) -> Decimal:
    return (amount * rate_for(region)).quantize(Decimal("0.01"))
