"""Runtime benchmarks for shortest-path algorithms and scheduling strategies."""
import csv
import time
import tracemalloc
from generator import random_graph, random_deliveries
from shortest_path import (dijkstra, dijkstra_array, bellman_ford, astar,
                           floyd_warshall, DistanceMatrix)
from scheduler import run_strategy


def _ms(fn, repeat=3):
    best = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best * 1000


def bench_shortest_paths(sizes=(50, 100, 250, 500, 1000, 2000, 5000), seed=1):
    rows = []
    for n in sizes:
        g = random_graph(n, seed=seed)
        tgt = f"N{n - 1}"
        row = {"V": n, "E": g.num_edges,
               "dijkstra_heap_ms": _ms(lambda: dijkstra(g, "N0")),
               "dijkstra_p2p_ms": _ms(lambda: dijkstra(g, "N0", tgt)),
               "astar_p2p_ms": _ms(lambda: astar(g, "N0", tgt)),
               "dijkstra_array_ms": _ms(lambda: dijkstra_array(g, "N0"), 1) if n <= 2000 else None,
               "bellman_ford_ms": _ms(lambda: bellman_ford(g, "N0"), 1) if n <= 2000 else None,
               "floyd_warshall_ms": _ms(lambda: floyd_warshall(g), 1) if n <= 150 else None}
        row["dijkstra_expanded"] = dijkstra(g, "N0", tgt)[2]
        row["astar_expanded"] = astar(g, "N0", tgt)[2]
        tracemalloc.start()
        dijkstra(g, "N0")
        row["dijkstra_peak_kb"] = round(tracemalloc.get_traced_memory()[1] / 1024, 1)
        tracemalloc.stop()
        rows.append(row)
    return rows


def bench_scheduling(stops=(10, 25, 50, 100, 200), n_nodes=1500, seed=2):
    g = random_graph(n_nodes, seed=seed)
    rows = []
    for k in stops:
        dl = random_deliveries(g, k, "N0", seed=k)
        t0 = time.perf_counter()
        dm = DistanceMatrix(g, ["N0"] + [d.node for d in dl])
        dm_ms = (time.perf_counter() - t0) * 1000
        row = {"stops": k, "distance_matrix_ms": dm_ms}
        for s in ("nearest", "priority", "edf", "nearest+2opt"):
            row[s + "_ms"] = _ms(lambda: run_strategy(s, "N0", dl, dm), 1)
            st, _ = run_strategy(s, "N0", dl, dm)
            row[s + "_dist"] = round(st.total_distance, 1)
            row[s + "_late"] = len(st.late)
        rows.append(row)
    return rows


def save_csv(rows, path):
    keys = list(rows[0])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def print_table(rows, cols):
    print(" | ".join(f"{c:>18}" for c in cols))
    for r in rows:
        print(" | ".join(f"{(round(r[c], 2) if isinstance(r.get(c), float) else r.get(c, '-')) if r.get(c) is not None else '-':>18}" for c in cols))
