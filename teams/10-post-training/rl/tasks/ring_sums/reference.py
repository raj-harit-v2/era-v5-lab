def ring_sums(grid):
    if len({len(r) for r in grid}) > 1:
        raise ValueError("ragged grid")
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    out = []
    for k in range((min(rows, cols) + 1) // 2):
        top, bottom, left, right = k, rows - 1 - k, k, cols - 1 - k
        total = 0
        for i in range(top, bottom + 1):
            for j in range(left, right + 1):
                if i in (top, bottom) or j in (left, right):
                    total += grid[i][j]
        out.append(total)
    return out
