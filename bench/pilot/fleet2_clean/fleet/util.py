def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def ratio(a, b):
    return a / b if b else 0.0


def scale(xs, k):
    return [x * k for x in xs]
