"""Shortest-path algorithms.  All return (dist, prev, expanded):
dist  : dict node -> distance (only for REACHED nodes -> unreachable nodes are absent)
prev  : dict node -> predecessor on a shortest path
expanded : number of nodes settled/processed (used to compare algorithms)

Complexities (V nodes, E edges)
  dijkstra        binary heap       O((V+E) log V)   space O(V)
  dijkstra_array  linear-scan       O(V^2)           space O(V)
  astar           heap + heuristic  O((V+E) log V) worst case, usually far fewer expansions
  bellman_ford    edge relaxation   O(V*E)           space O(V)
  floyd_warshall  all pairs         O(V^3)           space O(V^2)
"""
import heapq
from graph import GraphError

INF = float("inf")


def _check(g, *nodes):
    for n in nodes:
        if n is not None and n not in g:
            raise GraphError(f"Unknown location '{n}'")


def dijkstra(g, src, target=None):
    _check(g, src, target)
    dist, prev, done = {src: 0.0}, {}, set()
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue            # lazy deletion of stale heap entries
        done.add(u)
        if u == target:
            break
        for v, w in g.adj[u].items():
            nd = d + w
            if nd < dist.get(v, INF):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    return dist, prev, len(done)


def dijkstra_array(g, src, target=None):
    """Textbook O(V^2) Dijkstra (no heap) - kept as a baseline for Phase 3 comparison."""
    _check(g, src, target)
    dist = {n: INF for n in g.adj}
    dist[src], prev = 0.0, {}
    todo, expanded = set(g.adj), 0
    while todo:
        u = min(todo, key=dist.__getitem__)
        if dist[u] == INF:
            break
        todo.remove(u)
        expanded += 1
        if u == target:
            break
        for v, w in g.adj[u].items():
            if dist[u] + w < dist[v]:
                dist[v], prev[v] = dist[u] + w, u
    return {n: d for n, d in dist.items() if d < INF}, prev, expanded


def astar(g, src, target):
    _check(g, src, target)
    k = g.heuristic_scale()
    h = lambda n: k * g.euclid(n, target)
    dist, prev, done = {src: 0.0}, {}, set()
    heap = [(h(src), 0.0, src)]
    while heap:
        _, d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        if u == target:
            break
        for v, w in g.adj[u].items():
            nd = d + w
            if nd < dist.get(v, INF):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd + h(v), nd, v))
    return dist, prev, len(done)


def bellman_ford(g, src, target=None):
    _check(g, src, target)
    dist, prev = {src: 0.0}, {}
    arcs = [(u, v, w) for u, nb in g.adj.items() for v, w in nb.items()]
    for _ in range(len(g) - 1):
        changed = False
        for u, v, w in arcs:
            if u in dist and dist[u] + w < dist.get(v, INF):
                dist[v], prev[v] = dist[u] + w, u
                changed = True
        if not changed:
            break
    return dist, prev, len(dist)


def floyd_warshall(g):
    """All-pairs distances. Returns dict[a][b] (INF if unreachable). O(V^3)."""
    nodes = list(g.adj)
    d = {a: {b: (0.0 if a == b else g.adj[a].get(b, INF)) for b in nodes} for a in nodes}
    for k in nodes:
        dk = d[k]
        for i in nodes:
            dik = d[i][k]
            if dik == INF:
                continue
            di = d[i]
            for j in nodes:
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return d


ALGORITHMS = {"dijkstra": dijkstra, "dijkstra_array": dijkstra_array,
              "bellman_ford": bellman_ford}


def reconstruct(prev, src, dst):
    path, cur = [dst], dst
    while cur != src:
        if cur not in prev:
            return []
        cur = prev[cur]
        path.append(cur)
    return path[::-1]


def shortest_path(g, src, dst, algo="dijkstra"):
    """Return (cost, path, expanded). cost == INF and path == [] if unreachable."""
    if algo == "astar":
        dist, prev, exp = astar(g, src, dst)
    elif algo in ALGORITHMS:
        dist, prev, exp = ALGORITHMS[algo](g, src, dst)
    else:
        raise GraphError(f"Unknown algorithm '{algo}'")
    if dst not in dist:
        return INF, [], exp
    return dist[dst], reconstruct(prev, src, dst), exp


class DistanceMatrix:
    """Pairwise distances between 'points of interest' (depot + delivery stops).
    Runs one heap-Dijkstra per point: O(k (V+E) log V), space O(k V)."""

    def __init__(self, g, points):
        self.points = list(dict.fromkeys(points))
        self._sp = {p: dijkstra(g, p)[:2] for p in self.points}

    def dist(self, a, b):
        return self._sp[a][0].get(b, INF)

    def path(self, a, b):
        return reconstruct(self._sp[a][1], a, b) if self.dist(a, b) < INF else []
