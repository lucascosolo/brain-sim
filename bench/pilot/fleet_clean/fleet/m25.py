from fleet.util import clamp


def summarize_25(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 5, 35)
    return round(adjusted + len(values) - 1, 3)
