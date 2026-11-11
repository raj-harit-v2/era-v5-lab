import heapq
def topo_order(deps):
    nodes = set(deps)
    for v in deps.values():
        nodes.update(v)
    need = {n: set(deps.get(n, [])) for n in nodes}
    users = {n: [] for n in nodes}
    for n, ds in need.items():
        for d in ds:
            users[d].append(n)
    ready = [n for n in nodes if not need[n]]
    heapq.heapify(ready)
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for u in users[n]:
            need[u].discard(n)
            if not need[u]:
                heapq.heappush(ready, u)
    if len(out) != len(nodes):
        raise ValueError("cycle")
    return out
