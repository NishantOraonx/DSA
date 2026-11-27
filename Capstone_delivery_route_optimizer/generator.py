"""Random test-data generators (reproducible via seed)."""
import math
import random
from graph import Graph
from scheduler import Delivery


def random_graph(n, seed=0, k=3, connected=True, size=100.0):
    """Planar-ish road network: each node is linked to its k nearest neighbours
    (grid-bucket search, ~O(n)).  Weights are Euclid * U(1, 1.4) so A* stays admissible."""
    if n < 1:
        raise ValueError("n must be >= 1")
    rnd = random.Random(seed)
    g = Graph()
    names = [f"N{i}" for i in range(n)]
    for nm in names:
        g.add_location(nm, rnd.uniform(0, size), rnd.uniform(0, size))
    cells_per_side = max(1, int(math.sqrt(n / 2)))
    cs = size / cells_per_side
    grid = {}
    for nm in names:
        x, y = g.coords[nm]
        grid.setdefault((min(int(x // cs), cells_per_side - 1), min(int(y // cs), cells_per_side - 1)), []).append(nm)
    for nm in names:
        x, y = g.coords[nm]
        cx, cy = min(int(x // cs), cells_per_side - 1), min(int(y // cs), cells_per_side - 1)
        r, cand = 1, []
        while True:
            cand = [o for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                    for o in grid.get((cx + dx, cy + dy), []) if o != nm]
            if len(cand) >= k or r > cells_per_side:
                break
            r += 1
        cand.sort(key=lambda o: g.euclid(nm, o))
        for o in cand[:k]:
            g.add_road(nm, o, g.euclid(nm, o) * rnd.uniform(1.0, 1.4))
    if connected and n > 1:
        comps = g.components()
        for a, b in zip(comps, comps[1:]):          # chain components together
            u = rnd.choice(sorted(a))
            v = min(rnd.sample(sorted(b), min(len(b), 30)), key=lambda o: g.euclid(u, o))
            g.add_road(u, v, g.euclid(u, v) * rnd.uniform(1.0, 1.4))
    return g


def two_island_graph(n_each=8, seed=0):
    """Deliberately DISCONNECTED graph (two separate islands) for testing."""
    a, b = random_graph(n_each, seed), random_graph(n_each, seed + 1)
    g = Graph()
    for pre, h in (("A", a), ("B", b)):
        for nm, (x, y) in h.coords.items():
            g.add_location(f"{pre}{nm}", x, y)
        for u, v, w in h.edges():
            g.add_road(f"{pre}{u}", f"{pre}{v}", w)
    return g


def random_deliveries(g, count, depot, seed=0, horizon=None):
    rnd = random.Random(seed)
    pool = [n for n in g.coords if n != depot]
    count = min(count, len(pool))
    horizon = horizon or (count * 8 + 60)
    return [Delivery(n, deadline=round(rnd.uniform(0.4, 1.6) * horizon, 1),
                     priority=rnd.randint(1, 5), demand=rnd.randint(1, 4),
                     service_time=round(rnd.uniform(1, 4), 1))
            for n in rnd.sample(pool, count)]
