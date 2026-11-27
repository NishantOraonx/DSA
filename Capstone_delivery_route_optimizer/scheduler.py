"""Greedy delivery scheduling strategies + route evaluation.

Time model: travel time = distance / speed, plus service_time at each stop.
All strategies work on a DistanceMatrix (built from shortest paths on the road graph).

Strategy            Greedy rule                                   Time
nearest             go to the closest unserved stop               O(k^2)
priority            minimise distance / priority                  O(k^2)
edf                 earliest deadline first (min-heap)            O(k log k)
nearest + 2-opt     local improvement of the nearest route        O(k^2) per pass
fleet               capacity-constrained nearest, many vehicles   O(m k^2)
"""
import heapq
from dataclasses import dataclass, field

INF = float("inf")


@dataclass
class Delivery:
    node: str
    deadline: float = INF       # latest acceptable arrival time
    priority: int = 1           # 1 (low) .. 5 (high)
    demand: int = 1             # load units
    service_time: float = 0.0   # minutes spent at the stop


@dataclass
class RouteStats:
    order: list
    total_distance: float
    finish_time: float
    arrivals: dict = field(default_factory=dict)
    late: list = field(default_factory=list)
    total_lateness: float = 0.0

    @property
    def on_time_ratio(self):
        n = len(self.order)
        return 1.0 if n == 0 else (n - len(self.late)) / n


def split_reachable(depot, deliveries, dm):
    """Separate stops reachable from the depot (and back) from unreachable ones."""
    ok, bad = [], []
    for d in deliveries:
        (ok if dm.dist(depot, d.node) < INF and dm.dist(d.node, depot) < INF else bad).append(d)
    return ok, bad


def evaluate(order, depot, by_node, dm, speed=1.0, return_to_depot=True):
    t = dist = 0.0
    cur, arrivals, late, lateness = depot, {}, [], 0.0
    for n in order:
        leg = dm.dist(cur, n)
        dist += leg
        t += leg / speed
        arrivals[n] = t
        dl = by_node[n].deadline
        if t > dl:
            late.append(n)
            lateness += t - dl
        t += by_node[n].service_time
        cur = n
    if return_to_depot:
        dist += dm.dist(cur, depot)
        t += dm.dist(cur, depot) / speed
    return RouteStats(list(order), dist, t, arrivals, late, lateness)


def _greedy_pick(depot, deliveries, dm, score):
    remaining = {d.node: d for d in deliveries}
    order, cur = [], depot
    while remaining:
        nxt = min(remaining, key=lambda n: (score(cur, remaining[n]), n))
        order.append(nxt)
        del remaining[nxt]
        cur = nxt
    return order


def nearest_neighbor(depot, deliveries, dm):
    return _greedy_pick(depot, deliveries, dm, lambda c, d: dm.dist(c, d.node))


def priority_weighted(depot, deliveries, dm):
    return _greedy_pick(depot, deliveries, dm, lambda c, d: dm.dist(c, d.node) / max(d.priority, 1))


def earliest_deadline_first(depot, deliveries, dm):
    heap = [(d.deadline, -d.priority, d.node) for d in deliveries]
    heapq.heapify(heap)                       # O(k)
    return [heapq.heappop(heap)[2] for _ in range(len(heap))]   # k pops, O(log k) each


def two_opt(order, depot, by_node, dm, speed=1.0, max_passes=20):
    """2-opt local search; a move is accepted only if distance drops and the number of
    late deliveries does not increase (so optimisation never hurts service quality)."""
    best = list(order)
    best_stats = evaluate(best, depot, by_node, dm, speed)
    for _ in range(max_passes):
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                st = evaluate(cand, depot, by_node, dm, speed)
                if st.total_distance < best_stats.total_distance - 1e-9 and len(st.late) <= len(best_stats.late):
                    best, best_stats, improved = cand, st, True
        if not improved:
            break
    return best


STRATEGIES = {
    "nearest": nearest_neighbor,
    "priority": priority_weighted,
    "edf": earliest_deadline_first,
}


def run_strategy(name, depot, deliveries, dm, speed=1.0):
    """Run a named strategy. Unreachable stops are skipped and returned separately."""
    ok, bad = split_reachable(depot, deliveries, dm)
    by_node = {d.node: d for d in ok}
    if name == "nearest+2opt":
        order = two_opt(nearest_neighbor(depot, ok, dm), depot, by_node, dm, speed)
    elif name in STRATEGIES:
        order = STRATEGIES[name](depot, ok, dm)
    else:
        raise ValueError(f"Unknown strategy '{name}'")
    return evaluate(order, depot, by_node, dm, speed), [d.node for d in bad]


def plan_fleet(depot, deliveries, dm, vehicles, capacity, speed=1.0):
    """Greedy multi-vehicle plan: each vehicle repeatedly takes the nearest stop that
    still fits its capacity.  Returns (list[RouteStats], unassigned_nodes)."""
    if vehicles < 1 or capacity < 1:
        raise ValueError("vehicles and capacity must be >= 1")
    ok, bad = split_reachable(depot, deliveries, dm)
    unassigned = [d.node for d in bad]
    too_big = [d for d in ok if d.demand > capacity]
    unassigned += [d.node for d in too_big]
    pool = {d.node: d for d in ok if d.demand <= capacity}
    by_node = {d.node: d for d in ok}
    routes = []
    for _ in range(vehicles):
        cur, load, order = depot, 0, []
        while True:
            fits = [n for n, d in pool.items() if load + d.demand <= capacity]
            if not fits:
                break
            nxt = min(fits, key=lambda n: (dm.dist(cur, n), n))
            load += pool.pop(nxt).demand
            order.append(nxt)
            cur = nxt
        if order:
            routes.append(evaluate(order, depot, by_node, dm, speed))
    unassigned += list(pool)
    return routes, unassigned


def expand_route(order, depot, dm):
    """Turn a stop order into the full node-by-node road path (for plotting)."""
    full, cur = [depot], depot
    for n in list(order) + [depot]:
        seg = dm.path(cur, n)
        full += seg[1:]
        cur = n
    return full
