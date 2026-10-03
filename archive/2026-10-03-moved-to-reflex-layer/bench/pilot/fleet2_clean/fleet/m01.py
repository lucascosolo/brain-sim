from fleet.util import clamp


def summarize_01(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 2, 32)
    return round(adjusted + len(values) - 1, 3)
