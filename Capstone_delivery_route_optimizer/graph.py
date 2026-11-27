"""Graph ADT for delivery locations (nodes) and roads (weighted, undirected edges).

Data structures
---------------
* adj    : dict[str, dict[str, float]]  -> adjacency list implemented with hash maps.
           O(1) average edge lookup / update / delete, O(deg) neighbour iteration.
* coords : dict[str, (x, y)]            -> hash map used for O(1) location lookup and for
           the A* heuristic / visualisation.
Space: O(V + E).
"""
import json
import math
from collections import deque


class GraphError(ValueError):
    """Raised for any invalid graph operation (bad name, weight, unknown node ...)."""


class Graph:
    def __init__(self):
        self.coords = {}
        self.adj = {}
        self._edges = 0

    # ---------- basic queries ----------
    def __len__(self):
        return len(self.coords)

    def __contains__(self, name):
        return name in self.coords

    @property
    def num_edges(self):
        return self._edges

    def neighbors(self, u):
        self._require(u)
        return self.adj[u]

    def _require(self, name):
        if name not in self.coords:
            raise GraphError(f"Unknown location '{name}'")

    @staticmethod
    def _clean_name(name):
        if not isinstance(name, str) or not name.strip():
            raise GraphError("Location name must be a non-empty string")
        return name.strip()

    # ---------- mutation ----------
    def add_location(self, name, x=0.0, y=0.0):
        name = self._clean_name(name)
        if name in self.coords:
            raise GraphError(f"Location '{name}' already exists")
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            raise GraphError("Coordinates must be numbers")
        if not (math.isfinite(x) and math.isfinite(y)):
            raise GraphError("Coordinates must be finite numbers")
        self.coords[name] = (x, y)
        self.adj[name] = {}
        return name

    def euclid(self, a, b):
        (x1, y1), (x2, y2) = self.coords[a], self.coords[b]
        return math.hypot(x1 - x2, y1 - y2)

    def add_road(self, u, v, w=None):
        """Add/update an undirected road. If w is None the Euclidean length is used."""
        self._require(u)
        self._require(v)
        if u == v:
            raise GraphError("Self-loops are not allowed")
        if w is None:
            w = self.euclid(u, v)
        try:
            w = float(w)
        except (TypeError, ValueError):
            raise GraphError("Road weight must be a number")
        if not math.isfinite(w) or w <= 0:
            raise GraphError("Road weight must be a finite number > 0 (negative weights are invalid)")
        if v not in self.adj[u]:
            self._edges += 1
        self.adj[u][v] = w
        self.adj[v][u] = w

    def remove_road(self, u, v):
        self._require(u)
        self._require(v)
        if v not in self.adj[u]:
            raise GraphError(f"No road between '{u}' and '{v}'")
        del self.adj[u][v]
        del self.adj[v][u]
        self._edges -= 1

    def remove_location(self, name):
        self._require(name)
        for v in list(self.adj[name]):
            self.remove_road(name, v)
        del self.adj[name]
        del self.coords[name]

    # ---------- structure analysis ----------
    def edges(self):
        """Yield each undirected edge once as (u, v, w).  O(V+E)."""
        for u, nb in self.adj.items():
            for v, w in nb.items():
                if u < v:
                    yield u, v, w

    def components(self):
        """Connected components via iterative BFS.  O(V+E)."""
        seen, comps = set(), []
        for s in self.adj:
            if s in seen:
                continue
            comp, q = {s}, deque([s])
            seen.add(s)
            while q:
                u = q.popleft()
                for v in self.adj[u]:
                    if v not in seen:
                        seen.add(v)
                        comp.add(v)
                        q.append(v)
            comps.append(comp)
        return comps

    def is_connected(self):
        return len(self) <= 1 or len(self.components()) == 1

    def heuristic_scale(self):
        """Largest k<=1 such that k*euclid(u,v) <= w(u,v) for every road.
        Makes the A* heuristic admissible even for user-supplied road weights."""
        k = 1.0
        for u, v, w in self.edges():
            e = self.euclid(u, v)
            if e > 0:
                k = min(k, w / e)
        return k

    # ---------- (de)serialisation ----------
    def to_dict(self):
        return {
            "locations": [{"id": n, "x": c[0], "y": c[1]} for n, c in self.coords.items()],
            "roads": [[u, v, w] for u, v, w in self.edges()],
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or "locations" not in data:
            raise GraphError("Invalid graph file: missing 'locations'")
        g = cls()
        for loc in data["locations"]:
            if not isinstance(loc, dict) or "id" not in loc:
                raise GraphError("Each location needs an 'id'")
            g.add_location(loc["id"], loc.get("x", 0), loc.get("y", 0))
        for road in data.get("roads", []):
            if not isinstance(road, (list, tuple)) or len(road) not in (2, 3):
                raise GraphError(f"Invalid road entry: {road}")
            g.add_road(*road)
        return g

    def summary(self):
        comps = self.components()
        deg = [len(n) for n in self.adj.values()]
        return {
            "locations": len(self), "roads": self.num_edges, "components": len(comps),
            "connected": len(comps) <= 1,
            "avg_degree": round(sum(deg) / len(deg), 2) if deg else 0.0,
        }
