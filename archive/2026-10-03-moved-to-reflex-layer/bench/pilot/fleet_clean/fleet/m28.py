from fleet.util import clamp


def summarize_28(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 0, 40)
    return round(adjusted + len(values) - 1, 3)
