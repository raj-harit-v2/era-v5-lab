Write `ring_sums(grid)`. `grid` is a list of rows of integers. Think of the grid as concentric rectangular rings: ring 0 is the outer border (first and last row, first and last column), ring 1 is the border of what is left after removing ring 0, and so on until nothing is left. Return the list of ring sums from the outermost ring inwards.

If the grid has a single row or a single column, or the inner part is a single row or column, that part is one ring. Every cell belongs to exactly one ring. An empty grid, or a grid whose rows are all empty, gives `[]`. Raise `ValueError` if the rows do not all have the same length.

Examples:
- `ring_sums([[1, 2, 3], [4, 5, 6], [7, 8, 9]])` returns `[40, 5]`
- `ring_sums([[1, 2, 3, 4]])` returns `[10]`
- `ring_sums([])` returns `[]`

Reply with the complete code in one ```python block. Use only the standard library.
