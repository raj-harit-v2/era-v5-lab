def session_split(timestamps, idle):
    if idle < 0:
        raise ValueError("idle must be >= 0")
    out = []
    for t in sorted(timestamps):
        if out and t - out[-1][1] <= idle:
            out[-1][1] = t
            out[-1][2] += 1
        else:
            out.append([t, t, 1])
    return out
