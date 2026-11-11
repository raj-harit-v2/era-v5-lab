Write `topo_order(deps)`. `deps` maps a task name (string) to the list of task names it depends on. Every name that appears as a key or inside any list is a task. A task must come after all tasks it depends on. Duplicate entries in a dependency list are allowed and mean the same as one entry.

Return the build order as a list of names. Among the tasks that can be placed next, always choose the one that is smallest in normal Python string order, so the answer is unique. Raise `ValueError` if the dependencies contain a cycle (including a task that depends on itself). An empty mapping gives `[]`.

Examples:
- `topo_order({'app': ['lib', 'util'], 'lib': ['core'], 'util': ['core']})` returns `['core', 'lib', 'util', 'app']`
- `topo_order({'b': [], 'a': []})` returns `['a', 'b']`
- `topo_order({})` returns `[]`

Reply with the complete code in one ```python block. Use only the standard library.
