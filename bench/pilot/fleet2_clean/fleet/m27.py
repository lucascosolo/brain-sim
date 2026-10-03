from fleet.util import clamp


def summarize_27(values):
    subtotal = sum(values)
    adjusted = clamp(subtotal, 0, 28)
    return round(adjusted + len(values) - 1, 3)
