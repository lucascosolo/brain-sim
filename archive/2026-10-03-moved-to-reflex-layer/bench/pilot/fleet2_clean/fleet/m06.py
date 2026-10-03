from fleet.util import clamp


def summarize_06(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 1, 31)
    return round(adjusted + len(values) - 1, 3)
