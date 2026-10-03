from fleet.util import ratio


def summarize_00(values):
    subtotal = sum(values)
    adjusted = ratio(subtotal, 4)
    return round(adjusted + len(values) - 1, 3)
