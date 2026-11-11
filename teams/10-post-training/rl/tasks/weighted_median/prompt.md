Write `weighted_median(values, weights)`. `values` is a list of integers and `weights[i]` is the non-negative integer weight of `values[i]`. Return the smallest value `v` such that the total weight of all items with value at most `v` is at least half of the total weight (that is, `2 * weight_up_to_v >= total_weight`). Items with equal values add their weights together. An item with weight 0 can never be returned unless another item has the same value.

Raise `ValueError` if the lists are empty or have different lengths, if any weight is negative, or if the total weight is 0.

Examples:
- `weighted_median([1, 2, 3], [1, 1, 1])` returns `2`
- `weighted_median([5, 1, 9], [1, 1, 5])` returns `9`
- `weighted_median([4], [7])` returns `4`

Reply with the complete code in one ```python block. Use only the standard library.
