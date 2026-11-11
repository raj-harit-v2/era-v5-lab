def digit_sum(n, base=10):
    if base < 2 or n < 0:
        raise ValueError("bad input")
    total = 0
    while n:
        n, d = divmod(n, base)
        total += d
    return total
