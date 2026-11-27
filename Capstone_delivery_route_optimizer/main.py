"""Smart Delivery Route Optimization System - menu-driven entry point.

  python main.py          interactive menu
  python main.py --demo   non-interactive end-to-end demo (writes charts to outputs/)
"""
import os
import sys

from graph import Graph, GraphError
from dataio import load_problem, save_problem, validate_delivery
from shortest_path import shortest_path, DistanceMatrix, ALGORITHMS, INF
from scheduler import (Delivery, run_strategy, plan_fleet, expand_route, split_reachable)
from generator import random_graph, random_deliveries
import visualize
import benchmark

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_city.json")
STRATS = ["nearest", "priority", "edf", "nearest+2opt"]

MENU = """
==================== SMART DELIVERY ROUTE OPTIMIZER ====================
 1) Load problem from JSON         8) Add delivery request
 2) Generate random city           9) List deliveries
 3) Graph summary / connectivity  10) Run one scheduling strategy
 4) Add location                  11) Compare all strategies (+chart)
 5) Add road                      12) Multi-vehicle fleet plan (+map)
 6) Remove road                   13) Benchmark algorithms
 7) Shortest path A -> B          14) Save problem to JSON
 0) Exit
========================================================================"""


class State:
    def __init__(self):
        self.g, self.depot, self.deliveries = Graph(), None, []


def ask(prompt, cast=str, default=None):
    raw = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
    if raw == "" and default is not None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise GraphError(f"Invalid input '{raw}' (expected {cast.__name__})")


def need_graph(s):
    if len(s.g) == 0:
        raise GraphError("Graph is empty - load a file (1) or generate a city (2) first")


def need_depot(s):
    need_graph(s)
    if s.depot is None:
        s.depot = ask("Depot location", str)
    if s.depot not in s.g:
        d, s.depot = s.depot, None
        raise GraphError(f"Depot '{d}' is not in the graph")


def show_route(title, st, unreachable=()):
    print(f"\n--- {title} ---")
    print("Order      :", " -> ".join(st.order) if st.order else "(no stops)")
    print(f"Distance   : {st.total_distance:.1f}    Finish time: {st.finish_time:.1f} min")
    print(f"On-time    : {st.on_time_ratio * 100:.0f}%   Late stops: {st.late or 'none'}   "
          f"Total lateness: {st.total_lateness:.1f}")
    if unreachable:
        print("UNREACHABLE (skipped, graph disconnected):", unreachable)


def do_load(s):
    path = ask("JSON path", str, SAMPLE)
    s.g, s.depot, s.deliveries = load_problem(path)
    print(f"Loaded {len(s.g)} locations, {s.g.num_edges} roads, {len(s.deliveries)} deliveries, depot={s.depot}")


def do_generate(s):
    n = ask("Number of locations", int, 30)
    if n < 2:
        raise GraphError("Need at least 2 locations")
    k = ask("Number of deliveries", int, min(10, n - 1))
    seed = ask("Random seed", int, 1)
    s.g = random_graph(n, seed)
    s.depot = "N0"
    s.deliveries = random_deliveries(s.g, k, s.depot, seed)
    print(f"Generated {n} locations, {s.g.num_edges} roads, {len(s.deliveries)} deliveries, depot=N0")


def do_summary(s):
    need_graph(s)
    sm = s.g.summary()
    print(sm)
    if not sm["connected"]:
        print("WARNING: graph is disconnected. Components:")
        for c in s.g.components():
            print("  ", sorted(c)[:12], "..." if len(c) > 12 else "")


def do_add_loc(s):
    s.g.add_location(ask("Name"), ask("x", float, 0.0), ask("y", float, 0.0))
    print("Location added.")


def do_add_road(s):
    need_graph(s)
    u, v = ask("From"), ask("To")
    raw = ask("Weight (blank = Euclidean)", str, "")
    s.g.add_road(u, v, None if raw == "" else raw)
    print("Road added/updated.")


def do_rem_road(s):
    need_graph(s)
    s.g.remove_road(ask("From"), ask("To"))
    print("Road removed.")


def do_path(s):
    need_graph(s)
    a, b = ask("Source"), ask("Destination")
    algo = ask(f"Algorithm {list(ALGORITHMS) + ['astar']}", str, "dijkstra")
    cost, path, exp = shortest_path(s.g, a, b, algo)
    if cost == INF:
        print(f"No route exists from {a} to {b} (different components). Nodes explored: {exp}")
    else:
        print(f"Shortest distance = {cost:.2f}\nPath: {' -> '.join(path)}\nNodes expanded: {exp}")


def do_add_delivery(s):
    need_graph(s)
    d = Delivery(ask("Location"), ask("Deadline (min)", float, 300.0), ask("Priority 1-5", int, 3),
                 ask("Demand units", int, 1), ask("Service time (min)", float, 2.0))
    validate_delivery(s.g, d)
    s.deliveries = [x for x in s.deliveries if x.node != d.node] + [d]
    print("Delivery stored.")


def do_list(s):
    if not s.deliveries:
        print("No deliveries.")
    print(f"{'node':>10} {'deadline':>9} {'prio':>5} {'demand':>7} {'service':>8}")
    for d in s.deliveries:
        print(f"{d.node:>10} {d.deadline:>9.0f} {d.priority:>5} {d.demand:>7} {d.service_time:>8.1f}")


def _dm(s):
    need_depot(s)
    if not s.deliveries:
        raise GraphError("No deliveries - add some (8) or load a file (1)")
    return DistanceMatrix(s.g, [s.depot] + [d.node for d in s.deliveries])


def do_run(s):
    dm = _dm(s)
    name = ask(f"Strategy {STRATS}", str, "nearest+2opt")
    st, bad = run_strategy(name, s.depot, s.deliveries, dm)
    show_route(name, st, bad)
    os.makedirs(OUT, exist_ok=True)
    p = visualize.plot_routes(s.g, s.depot, s.deliveries, [expand_route(st.order, s.depot, dm)],
                              os.path.join(OUT, f"route_{name.replace('+', '_')}.png"), f"Route: {name}", bad)
    print("Map saved to", p)


def do_compare(s, quiet=False):
    dm = _dm(s)
    res = {}
    print(f"\n{'strategy':>14} {'distance':>9} {'finish':>8} {'late':>5} {'lateness':>9}")
    for n in STRATS:
        st, bad = run_strategy(n, s.depot, s.deliveries, dm)
        res[n] = st
        print(f"{n:>14} {st.total_distance:>9.1f} {st.finish_time:>8.1f} {len(st.late):>5} {st.total_lateness:>9.1f}")
    if bad:
        print("Unreachable stops skipped:", bad)
    os.makedirs(OUT, exist_ok=True)
    print("Chart saved to", visualize.plot_strategy_comparison(res, os.path.join(OUT, "strategy_comparison.png")))
    best = min(res, key=lambda n: (len(res[n].late), res[n].total_distance))
    print(f"Best (fewest late, then shortest): {best}")
    return res


def do_fleet(s):
    dm = _dm(s)
    v, cap = ask("Vehicles", int, 3), ask("Capacity per vehicle", int, 8)
    routes, un = plan_fleet(s.depot, s.deliveries, dm, v, cap)
    for i, st in enumerate(routes, 1):
        show_route(f"Vehicle {i}", st)
    if un:
        print("\nUNASSIGNED stops (unreachable / demand>capacity / not enough vehicles):", un)
    os.makedirs(OUT, exist_ok=True)
    p = visualize.plot_routes(s.g, s.depot, s.deliveries, [expand_route(r.order, s.depot, dm) for r in routes],
                              os.path.join(OUT, "fleet_plan.png"), f"Fleet plan: {len(routes)} vehicles", un)
    print("Map saved to", p)


def do_bench(s):
    os.makedirs(OUT, exist_ok=True)
    sizes = (50, 100, 250, 500, 1000, 2000, 5000)
    rows = benchmark.bench_shortest_paths(sizes)
    benchmark.print_table(rows, ["V", "E", "dijkstra_heap_ms", "astar_p2p_ms", "dijkstra_array_ms",
                                 "bellman_ford_ms", "floyd_warshall_ms"])
    benchmark.save_csv(rows, os.path.join(OUT, "benchmark_shortest_path.csv"))
    visualize.plot_benchmark(rows, os.path.join(OUT, "benchmark_shortest_path.png"),
                             "Single-source shortest path runtime vs graph size", "V",
                             [("dijkstra_heap_ms", "Dijkstra (heap)"), ("dijkstra_array_ms", "Dijkstra (array O(V^2))"),
                              ("bellman_ford_ms", "Bellman-Ford"), ("floyd_warshall_ms", "Floyd-Warshall (all pairs)")])
    srows = benchmark.bench_scheduling((10, 25, 50, 100, 150))
    benchmark.print_table(srows, ["stops", "distance_matrix_ms", "nearest_ms", "priority_ms", "edf_ms", "nearest+2opt_ms"])
    benchmark.save_csv(srows, os.path.join(OUT, "benchmark_scheduling.csv"))
    visualize.plot_benchmark(srows, os.path.join(OUT, "benchmark_scheduling.png"),
                             "Scheduling strategy runtime vs number of stops", "stops",
                             [(n + "_ms", n) for n in STRATS])
    print("CSV + PNG saved in", OUT)


def do_save(s):
    need_graph(s)
    save_problem(ask("Output path", str, "my_problem.json"), s.g, s.depot, s.deliveries)
    print("Saved.")


ACTIONS = {"1": do_load, "2": do_generate, "3": do_summary, "4": do_add_loc, "5": do_add_road,
           "6": do_rem_road, "7": do_path, "8": do_add_delivery, "9": do_list, "10": do_run,
           "11": do_compare, "12": do_fleet, "13": do_bench, "14": do_save}


def demo():
    s = State()
    s.g, s.depot, s.deliveries = load_problem(SAMPLE)
    print("DEMO on", SAMPLE, s.g.summary())
    cost, path, exp = shortest_path(s.g, "A", "F", "dijkstra")
    print(f"\nShortest A->F: {cost:.1f} via {' -> '.join(path)} (expanded {exp})")
    res = do_compare(s)
    dm = DistanceMatrix(s.g, [s.depot] + [d.node for d in s.deliveries])
    st = res["nearest+2opt"]
    visualize.plot_routes(s.g, s.depot, s.deliveries, [expand_route(st.order, s.depot, dm)],
                          os.path.join(OUT, "route_nearest_2opt.png"), "Best route: nearest + 2-opt")
    routes, un = plan_fleet(s.depot, s.deliveries, dm, 3, 8)
    for i, r in enumerate(routes, 1):
        show_route(f"Vehicle {i}", r)
    if un:
        print("\nUNASSIGNED stops (unreachable / demand>capacity / not enough vehicles):", un)
    visualize.plot_routes(s.g, s.depot, s.deliveries, [expand_route(r.order, s.depot, dm) for r in routes],
                          os.path.join(OUT, "fleet_plan.png"), "Fleet plan: 3 vehicles", un)
    # disconnected scenario
    g2, dep2, dl2 = load_problem(os.path.join(os.path.dirname(SAMPLE), "disconnected_city.json"))
    print("\nDisconnected scenario:", g2.summary())
    dm2 = DistanceMatrix(g2, [dep2] + [d.node for d in dl2])
    st2, bad = run_strategy("nearest+2opt", dep2, dl2, dm2)
    show_route("Disconnected city", st2, bad)
    visualize.plot_routes(g2, dep2, dl2, [expand_route(st2.order, dep2, dm2)],
                          os.path.join(OUT, "route_disconnected.png"), "Disconnected graph: island stop unreachable", bad)
    print("\nPNG charts written to", OUT)


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--demo" in sys.argv:
        return demo()
    s = State()
    while True:
        print(MENU)
        try:
            choice = input("Choose option: ").strip()
        except EOFError:
            return
        if choice == "0":
            print("Goodbye!")
            return
        action = ACTIONS.get(choice)
        if not action:
            print("Invalid choice - enter a number from the menu.")
            continue
        try:
            action(s)
        except (GraphError, ValueError) as e:
            print(f"[ERROR] {e}")
        except EOFError:
            return
        except KeyboardInterrupt:
            print("\nCancelled.")


if __name__ == "__main__":
    main()
