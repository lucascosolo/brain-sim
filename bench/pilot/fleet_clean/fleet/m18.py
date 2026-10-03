from fleet.util import clamp


def summarize_18(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 2, 20)
    return round(adjusted + len(values) - 1, 3)
