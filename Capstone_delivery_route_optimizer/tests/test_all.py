import os, sys, json, tempfile, time, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from graph import Graph, GraphError
from shortest_path import (dijkstra, dijkstra_array, bellman_ford, astar, floyd_warshall,
                           shortest_path, DistanceMatrix, INF)
from scheduler import Delivery, run_strategy, plan_fleet, evaluate, earliest_deadline_first, expand_route
from generator import random_graph, two_island_graph, random_deliveries
from dataio import load_problem

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def line_graph():
    g = Graph()
    for i, n in enumerate("ABCD"):
        g.add_location(n, i * 10, 0)
    g.add_road("A", "B", 10); g.add_road("B", "C", 10); g.add_road("C", "D", 10); g.add_road("A", "D", 50)
    return g


class TestGraph(unittest.TestCase):
    def test_valid_build(self):
        g = line_graph(); self.assertEqual((len(g), g.num_edges), (4, 4))
    def test_duplicate_location(self):
        g = line_graph()
        with self.assertRaises(GraphError): g.add_location("A")
    def test_empty_name(self):
        with self.assertRaises(GraphError): Graph().add_location("  ")
    def test_negative_and_zero_weight(self):
        g = line_graph()
        for w in (-1, 0, "abc", float("nan"), float("inf")):
            with self.assertRaises(GraphError): g.add_road("A", "C", w)
    def test_unknown_node_and_self_loop(self):
        g = line_graph()
        with self.assertRaises(GraphError): g.add_road("A", "Z", 1)
        with self.assertRaises(GraphError): g.add_road("A", "A", 1)
    def test_update_edge_does_not_double_count(self):
        g = line_graph(); g.add_road("A", "B", 5); self.assertEqual(g.num_edges, 4)
    def test_remove_road_and_location(self):
        g = line_graph(); g.remove_road("A", "D"); self.assertEqual(g.num_edges, 3)
        with self.assertRaises(GraphError): g.remove_road("A", "D")
        g.remove_location("B"); self.assertEqual((len(g), g.num_edges), (3, 1))
    def test_components(self):
        g = two_island_graph(6); self.assertFalse(g.is_connected()); self.assertEqual(len(g.components()), 2)
    def test_single_and_empty_graph(self):
        self.assertTrue(Graph().is_connected())
        g = Graph(); g.add_location("X"); self.assertTrue(g.is_connected())


class TestShortestPath(unittest.TestCase):
    def test_known_answer(self):
        g = line_graph()
        for algo in ("dijkstra", "dijkstra_array", "bellman_ford", "astar"):
            c, p, _ = shortest_path(g, "A", "D", algo)
            self.assertEqual(c, 30); self.assertEqual(p, ["A", "B", "C", "D"], algo)
    def test_same_node(self):
        c, p, _ = shortest_path(line_graph(), "B", "B"); self.assertEqual((c, p), (0, ["B"]))
    def test_unknown_node(self):
        with self.assertRaises(GraphError): shortest_path(line_graph(), "A", "Q")
        with self.assertRaises(GraphError): shortest_path(line_graph(), "A", "B", "magic")
    def test_disconnected_unreachable(self):
        g = two_island_graph(6)
        for algo in ("dijkstra", "dijkstra_array", "bellman_ford", "astar"):
            c, p, _ = shortest_path(g, "AN0", "BN0", algo); self.assertEqual((c, p), (INF, []), algo)
    def test_algorithms_agree_on_random_graphs(self):
        for seed in range(5):
            g = random_graph(80, seed)
            fw = floyd_warshall(g)
            d1 = dijkstra(g, "N0")[0]; d2 = dijkstra_array(g, "N0")[0]; d3 = bellman_ford(g, "N0")[0]
            for n in g.coords:
                self.assertAlmostEqual(d1[n], d2[n]); self.assertAlmostEqual(d1[n], d3[n])
                self.assertAlmostEqual(d1[n], fw["N0"][n])
                self.assertAlmostEqual(astar(g, "N0", n)[0][n], d1[n])
    def test_astar_with_cheap_weights_still_optimal(self):
        g = Graph()
        for n, x in zip("ABC", (0, 100, 200)): g.add_location(n, x, 0)
        g.add_road("A", "B", 1); g.add_road("B", "C", 1)     # weights << Euclid
        self.assertEqual(astar(g, "A", "C")[0]["C"], 2)
    def test_distance_matrix_and_path(self):
        dm = DistanceMatrix(line_graph(), ["A", "D"]); self.assertEqual(dm.dist("A", "D"), 30)
        self.assertEqual(dm.path("A", "D"), ["A", "B", "C", "D"])


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.g, self.dep, self.dl = load_problem(os.path.join(DATA, "sample_city.json"))
        self.dm = DistanceMatrix(self.g, [self.dep] + [d.node for d in self.dl])
    def test_all_strategies_visit_every_stop_once(self):
        for s in ("nearest", "priority", "edf", "nearest+2opt"):
            st, bad = run_strategy(s, self.dep, self.dl, self.dm)
            self.assertEqual(sorted(st.order), sorted(d.node for d in self.dl)); self.assertEqual(bad, [])
    def test_2opt_never_worse_than_nearest(self):
        a, _ = run_strategy("nearest", self.dep, self.dl, self.dm)
        b, _ = run_strategy("nearest+2opt", self.dep, self.dl, self.dm)
        self.assertLessEqual(b.total_distance, a.total_distance + 1e-9); self.assertLessEqual(len(b.late), len(a.late))
    def test_edf_order(self):
        order = earliest_deadline_first(self.dep, self.dl, self.dm)
        dls = [next(d.deadline for d in self.dl if d.node == n) for n in order]
        self.assertEqual(dls, sorted(dls))
    def test_empty_and_single_delivery(self):
        st, _ = run_strategy("nearest", self.dep, [], self.dm); self.assertEqual((st.order, st.total_distance), ([], 0.0))
        one = [Delivery("A", 1000)]
        st, _ = run_strategy("edf", self.dep, one, self.dm); self.assertEqual(st.order, ["A"])
        self.assertAlmostEqual(st.total_distance, 2 * self.dm.dist(self.dep, "A"))
    def test_lateness_detected(self):
        st, _ = run_strategy("nearest", self.dep, [Delivery("A", 0.001)], self.dm)
        self.assertEqual(st.late, ["A"]); self.assertGreater(st.total_lateness, 0)
    def test_disconnected_stop_skipped(self):
        g, dep, dl = load_problem(os.path.join(DATA, "disconnected_city.json"))
        dm = DistanceMatrix(g, [dep] + [d.node for d in dl])
        st, bad = run_strategy("nearest+2opt", dep, dl, dm)
        self.assertEqual(bad, ["Island1"]); self.assertNotIn("Island1", st.order)
    def test_fleet_capacity_respected(self):
        routes, un = plan_fleet(self.dep, self.dl, self.dm, 3, 8)
        by = {d.node: d for d in self.dl}
        for r in routes: self.assertLessEqual(sum(by[n].demand for n in r.order), 8)
        served = [n for r in routes for n in r.order]
        self.assertEqual(sorted(served + un), sorted(by)); self.assertEqual(len(served), len(set(served)))
    def test_fleet_oversized_and_insufficient_vehicles(self):
        _, un = plan_fleet(self.dep, self.dl, self.dm, 1, 3)
        self.assertIn("E", un)                       # demand 4 > capacity 3
        _, un = plan_fleet(self.dep, self.dl, self.dm, 1, 100); self.assertEqual(un, [])
        with self.assertRaises(ValueError): plan_fleet(self.dep, self.dl, self.dm, 0, 5)
    def test_expand_route_is_valid_road_path(self):
        st, _ = run_strategy("nearest", self.dep, self.dl, self.dm)
        full = expand_route(st.order, self.dep, self.dm)
        self.assertEqual((full[0], full[-1]), (self.dep, self.dep))
        for a, b in zip(full, full[1:]): self.assertIn(b, self.g.adj[a])


class TestIO(unittest.TestCase):
    def test_invalid_files(self):
        for f in ("invalid_negative_weight.json", "invalid_malformed.json", "invalid_unknown_node.json", "missing.json"):
            with self.assertRaises(GraphError, msg=f): load_problem(os.path.join(DATA, f))
    def test_bad_delivery_entries(self):
        base = {"locations": [{"id": "D"}, {"id": "A"}], "roads": [["D", "A", 1]], "depot": "D"}
        for bad in ({"node": "ZZ"}, {"node": "A", "priority": 9}, {"node": "A", "demand": 0}, {"node": "A", "deadline": "x"}, {}):
            p = os.path.join(tempfile.mkdtemp(), "t.json")
            with open(p, "w") as f: json.dump({**base, "deliveries": [bad]}, f)
            with self.assertRaises(GraphError, msg=str(bad)): load_problem(p)
    def test_bad_depot(self):
        p = os.path.join(tempfile.mkdtemp(), "t.json")
        with open(p, "w") as f: json.dump({"locations": [{"id": "A"}], "depot": "Q"}, f)
        with self.assertRaises(GraphError): load_problem(p)


class TestScale(unittest.TestCase):
    def test_large_graph_runs_fast(self):
        g = random_graph(5000, 3); self.assertTrue(g.is_connected())
        t = time.perf_counter(); d, _, _ = dijkstra(g, "N0"); self.assertEqual(len(d), 5000)
        self.assertLess(time.perf_counter() - t, 2.0)
    def test_one_node_graph_generation(self):
        self.assertEqual(len(random_graph(1)), 1)
        with self.assertRaises(ValueError): random_graph(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
