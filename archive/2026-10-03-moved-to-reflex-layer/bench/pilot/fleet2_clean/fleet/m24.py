from fleet.util import clamp


def summarize_24(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 5, 20)
    return round(adjusted + len(values) - 1, 3)
