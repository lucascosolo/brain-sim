from fleet.util import scale


def summarize_12(values):
    subtotal = sum(values)
    adjusted = sum(scale(values, 5))
    return round(adjusted + len(values) - 1, 3)
