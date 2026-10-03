from fleet.util import clamp


def summarize_03(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 0, 30)
    return round(adjusted + len(values) - 1, 3)
