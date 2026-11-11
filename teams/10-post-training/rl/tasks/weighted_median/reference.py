def weighted_median(values, weights):
    if not values or len(values) != len(weights):
        raise ValueError("bad lists")
    if any(w < 0 for w in weights) or sum(weights) == 0:
        raise ValueError("bad weights")
    total = sum(weights)
    acc = 0
    for v, w in sorted(zip(values, weights)):
        acc += w
        if 2 * acc >= total:
            return v
