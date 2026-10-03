from decimal import ROUND_HALF_UP, Decimal


def money(x) -> Decimal:
    """Round to cents, half up."""
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))
