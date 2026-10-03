from fleet.util import ratio


def summarize_02(values):
    subtotal = sum(values)
    adjusted = ratio(subtotal, 2)
    return round(adjusted + len(values) - 1, 3)
