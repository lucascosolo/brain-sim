from fleet.util import ratio


def summarize_21(values):
    subtotal = sum(values)
    adjusted = ratio(subtotal, 3)
    return round(adjusted + len(values) - 1, 3)
