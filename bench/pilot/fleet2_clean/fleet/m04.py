from fleet.util import scale


def summarize_04(values):
    subtotal = sum(values)
    adjusted = sum(scale(values, 4))
    return round(adjusted + len(values) - 1, 3)
