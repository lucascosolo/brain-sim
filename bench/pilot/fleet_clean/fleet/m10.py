from fleet.util import scale


def summarize_10(values):
    subtotal = sum(values)
    adjusted = sum(scale(values, 2))
    return round(adjusted + len(values) - 1, 3)
