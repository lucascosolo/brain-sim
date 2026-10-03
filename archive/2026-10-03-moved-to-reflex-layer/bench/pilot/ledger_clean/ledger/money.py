from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def parse_amount(text):
    """Parse '1,234.50', '$5', '(12.00)' or '-3' into a Decimal rounded to cents."""
    s = text.strip().replace(",", "").replace("$", "")
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1]
    elif s.startswith("-"):
        negative, s = True, s[1:]
    if not s or s.count(".") > 1 or not all(c.isdigit() or c == "." for c in s):
        raise ValueError(f"not an amount: {text!r}")
    value = Decimal(s).quantize(CENT, rounding=ROUND_HALF_UP)
    return -value if negative else value


def format_amount(value):
    """Format a Decimal as '1,234.50', with negatives in parentheses."""
    q = value.quantize(CENT, rounding=ROUND_HALF_UP)
    body = f"{abs(q):,.2f}"
    return f"({body})" if q < 0 else body


def split_evenly(total, parts):
    """Split a non-negative total into `parts` amounts summing exactly to it; earlier parts get extra cents."""
    if parts <= 0:
        raise ValueError("parts must be positive")
    cents = int((total * 100).to_integral_value(rounding=ROUND_HALF_UP))
    base, extra = divmod(cents, parts)
    return [Decimal(base + (1 if i < extra else 0)) / 100 for i in range(parts)]
