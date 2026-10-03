from fleet.util import clamp


def summarize_15(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 2, 21)
    return round(adjusted + len(values) - 1, 3)
