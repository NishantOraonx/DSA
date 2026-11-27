# Smart Delivery Route Optimization System

A single connected Python program that models a city as a weighted graph, computes shortest
paths, schedules deliveries with greedy strategies (and a 2-opt improvement), plans multi-vehicle
routes, visualises results and benchmarks everything. **Pure standard library + matplotlib.**

## Run
```bash
pip install matplotlib          # only external dependency
python main.py                  # interactive menu (14 options)
python main.py --demo           # one-shot end-to-end demo -> outputs/*.png
python -m unittest discover -s tests -v    # 30 automated tests
```
Suggested interactive flow: `1` (Enter = load sample city) -> `3` -> `7` (A to F, try each algorithm)
-> `11` (compare strategies) -> `12` (fleet) -> `13` (benchmark).

## Project layout
| File | Role |
|---|---|
| `graph.py` | Graph ADT: hash-map adjacency list, validation, components (BFS), JSON I/O |
| `shortest_path.py` | Dijkstra (heap), Dijkstra (array), A*, Bellman-Ford, Floyd-Warshall, `DistanceMatrix` |
| `scheduler.py` | Greedy strategies (nearest, priority-weighted, EDF with min-heap), 2-opt, fleet planner, evaluation |
| `generator.py` | Reproducible random cities, disconnected "two island" city, random deliveries |
| `dataio.py` | Load/save problem instances with full validation |
| `visualize.py` | Route maps, strategy comparison and benchmark charts |
| `benchmark.py` | Runtime/memory scalability experiments |
| `main.py` | Menu-driven CLI + `--demo` |
| `tests/test_all.py` | Valid / invalid / boundary / disconnected / scale tests |
| `data/` | `sample_city.json`, `disconnected_city.json`, three invalid files for error-handling tests |
| `outputs/` | Screenshots (PNG), CSV benchmarks, text traces of runs |
| `REPORT.md` | Design, complexity analysis, test summary, results, use cases |

## Input format (JSON)
```json
{"depot": "Depot",
 "locations": [{"id": "A", "x": 20, "y": 80}],
 "roads": [["A", "B", 24.3]],
 "deliveries": [{"node": "A", "deadline": 270, "priority": 3, "demand": 2, "service_time": 3}]}
```
Road weight may be omitted (Euclidean length is used). Priority 1-5. Time = distance / speed (speed = 1).

## Outputs
`outputs/route_nearest_2opt.png`, `fleet_plan.png`, `route_disconnected.png`, `strategy_comparison.png`,
`benchmark_shortest_path.png`, `benchmark_scheduling.png`, plus `*_trace.txt` console captures.
