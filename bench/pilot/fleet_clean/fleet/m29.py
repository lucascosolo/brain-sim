from fleet.util import clamp


def summarize_29(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 4, 24)
    return round(adjusted + len(values) - 1, 3)
