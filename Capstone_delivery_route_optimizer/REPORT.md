# Smart Delivery Route Optimization System - Short Report

## Phase 1 - Problem & data-structure design
**Problem:** a depot must serve many customers in a city. Find shortest road paths between points and decide the
visiting order (and vehicle assignment) so that distance is small and deadlines are met.

| Need | Structure | Why |
|---|---|---|
| City / roads | Graph as **adjacency list of hash maps** `dict[node][nbr]=w` | O(V+E) space (matrix would be O(V^2), wasteful for sparse road nets); O(1) edge lookup/update |
| Location lookup, coordinates | **Hash map** `coords` | O(1) access; used for A* heuristic and plotting |
| Dijkstra frontier | **Binary min-heap** (`heapq`) | extract-min in O(log V) |
| Earliest-deadline scheduling | **Min-heap** keyed (deadline, -priority) | k pops in O(k log k) |
| Visited / unserved sets | **Hash sets / dicts** | O(1) membership & deletion |
| Routes, paths | **Arrays (lists)** | ordered stops; cheap slicing for 2-opt |
| Stop-to-stop distances | `DistanceMatrix` (dict of dicts) | one Dijkstra per stop, O(1) later queries |

Data flow: JSON -> `Graph` -> `DistanceMatrix` (Dijkstra) -> scheduler strategy -> `RouteStats` -> plot/report.

## Phase 2 - Implementation (modules)
Graph ADT with validation; 5 shortest-path algorithms; 3 greedy strategies + 2-opt; capacity-aware fleet planner;
generator; menu-driven CLI integrating everything in one program.

## Phase 3 - Complexity analysis (V nodes, E edges, k stops, m vehicles)
| Operation | Time | Space | Note |
|---|---|---|---|
| add/remove road, lookup | O(1) avg | - | hash maps |
| components (BFS) | O(V+E) | O(V) | detects disconnected graphs |
| Dijkstra (heap) | O((V+E) log V) | O(V) | **chosen default** |
| Dijkstra (array) | O(V^2) | O(V) | baseline |
| A* | O((V+E) log V) worst | O(V) | heuristic scaled to stay admissible |
| Bellman-Ford | O(VE) | O(V) | baseline |
| Floyd-Warshall | O(V^3) | O(V^2) | only feasible for tiny graphs |
| DistanceMatrix | O(k (V+E) log V) | O(kV) | |
| Nearest / priority greedy | O(k^2) | O(k) | |
| EDF (heap) | O(k log k) | O(k) | |
| 2-opt | O(k^3) per pass as implemented (O(k^2) candidates x O(k) evaluate) | O(k) | evaluation protects deadlines |
| Fleet greedy | O(m k^2) | O(k) | |

**Measured (ms, `outputs/benchmark_shortest_path.csv`)**

| V | Dijkstra heap | Dijkstra array | Bellman-Ford | Floyd-Warshall |
|---|---|---|---|---|
| 100 | 0.08 | 0.23 | 0.40 | 19.6 |
| 500 | 0.55 | 4.45 | 3.15 | - |
| 1000 | 0.79 | 14.3 | 8.1 | - |
| 2000 | 1.44 | 46.0 | 17.3 | - |
| 5000 | 4.75 | - | - | - |

Heap Dijkstra grows almost linearly (~3x for 2.5x nodes at 5000 vs 2000) while the O(V^2) version grows ~3x per doubling.
A* expanded noticeably fewer nodes for point-to-point queries (e.g. 939 vs 2416 at V=5000) but was not faster in wall-clock
time in pure Python because computing the heuristic costs more than it saves on these small, sparse graphs - an honest
finding; it would pay off on larger/denser maps. Scheduling: EDF and greedy are sub-10 ms for 150 stops; 2-opt takes 1.7 s at
150 stops, confirming the O(k^3) cost - so it is an optional refinement for small/medium routes.
Peak memory of Dijkstra grows linearly (6 KB at V=50 to ~956 KB at V=5000).

## Phase 4 - Testing (30 automated tests, all pass; see `outputs/test_run_trace.txt`)
* **Valid:** known-answer path; 4 algorithms agree with Floyd-Warshall on 5 random graphs; every strategy visits each stop once; EDF ordering; capacity respected.
* **Invalid:** duplicate/empty names, negative/zero/NaN/inf/non-numeric weights, unknown nodes, self-loops, malformed JSON, missing file, bad priority/demand/deadline, bad depot, unknown algorithm, 0 vehicles.
* **Boundary:** empty graph, one-node graph, source == target, no deliveries, a single delivery, demand > capacity, too few vehicles.
* **Disconnected:** BFS components, "no route" result (INF) for all algorithms, unreachable stops skipped and reported (`data/disconnected_city.json`).
* **Scale:** 5000-node connected graph, full SSSP < 2 s.
The CLI catches all `GraphError`/`ValueError`, prints `[ERROR] ...`, and returns to the menu (`outputs/interactive_session_trace.txt`).

## Phase 5 - Results
Sample city (11 stops, deadlines 120-450 min), `outputs/demo_trace.txt`:

| Strategy | Distance | Finish | Late stops | Lateness |
|---|---|---|---|---|
| Nearest neighbour | 334.7 | 361.7 | 1 | 45.8 |
| Priority-weighted | 525.6 | 552.6 | 4 | 205.1 |
| Earliest deadline first | 581.0 | 608.0 | 7 | 493.0 |
| Nearest + 2-opt | 334.7 | 361.7 | 1 | 45.8 |

Findings: on this dense-deadline instance the distance-driven greedy rule gave both the shortest route *and* the fewest late
stops; EDF ignores geography and zig-zags across the city. 2-opt found no further safe improvement here (it rejects moves that
add late stops). Fleet of 3 vehicles (capacity 8) served 10/11 stops all on time; stop E (demand 4) was left unassigned and
reported. In the disconnected city, the island stop is detected, reported as unreachable and the rest is routed normally.
Images: `route_nearest_2opt.png`, `fleet_plan.png`, `route_disconnected.png`, `strategy_comparison.png`, benchmark PNGs.

**Limitations:** greedy rules are heuristics (no optimality guarantee; the problem is NP-hard); undirected static weights
(no live traffic); no time windows with waiting; fleet planner is greedy.

**Real-world use cases:** e-commerce/last-mile parcels, food & grocery delivery with deadlines and priorities, courier/medical
sample pick-up (priority 5 = urgent), waste collection, field-service technician dispatch, school-bus/shuttle routing,
disaster relief where roads become disconnected (the system reports which sites are unreachable).
**Possible extensions:** directed/one-way roads, time-dependent traffic weights, time windows, Or-opt/Clarke-Wright savings, live map data.
