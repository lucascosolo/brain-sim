from fleet.util import clamp


def summarize_23(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 1, 25)
    return round(adjusted + len(values) - 1, 3)
