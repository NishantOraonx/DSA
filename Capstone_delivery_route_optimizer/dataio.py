"""Load / save a complete problem instance (graph + depot + deliveries) as JSON."""
import json
from graph import Graph, GraphError
from scheduler import Delivery


def load_problem(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise GraphError(f"File not found: {path}")
    except json.JSONDecodeError as e:
        raise GraphError(f"Malformed JSON in {path}: {e}")
    g = Graph.from_dict(data)
    depot = data.get("depot")
    if depot is not None and depot not in g:
        raise GraphError(f"Depot '{depot}' is not a location in the graph")
    deliveries = []
    for item in data.get("deliveries", []):
        try:
            d = Delivery(item["node"], float(item.get("deadline", float("inf"))),
                         int(item.get("priority", 1)), int(item.get("demand", 1)),
                         float(item.get("service_time", 0)))
        except (KeyError, TypeError, ValueError) as e:
            raise GraphError(f"Invalid delivery entry {item}: {e}")
        validate_delivery(g, d)
        deliveries.append(d)
    return g, depot, deliveries


def validate_delivery(g, d):
    if d.node not in g:
        raise GraphError(f"Delivery location '{d.node}' is not in the graph")
    if not 1 <= d.priority <= 5:
        raise GraphError("Priority must be between 1 and 5")
    if d.demand < 1:
        raise GraphError("Demand must be >= 1")
    if d.deadline <= 0 or d.service_time < 0:
        raise GraphError("Deadline must be > 0 and service time >= 0")


def save_problem(path, g, depot, deliveries):
    data = g.to_dict()
    data["depot"] = depot
    data["deliveries"] = [{"node": d.node, "deadline": d.deadline if d.deadline != float("inf") else 1e9,
                           "priority": d.priority, "demand": d.demand,
                           "service_time": d.service_time} for d in deliveries]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
