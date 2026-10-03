from fleet.util import scale


def summarize_19(values):
    subtotal = sum(values)
    adjusted = sum(scale(values, 3))
    return round(adjusted + len(values) - 1, 3)
