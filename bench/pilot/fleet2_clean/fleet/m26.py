from fleet.util import clamp


def summarize_26(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 5, 21)
    return round(adjusted + len(values) - 1, 3)
