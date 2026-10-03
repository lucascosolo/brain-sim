from fleet.util import clamp


def summarize_17(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 5, 34)
    return round(adjusted + len(values) - 1, 3)
