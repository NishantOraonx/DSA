"""matplotlib visualisations (headless-safe: Agg backend)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b"]


def plot_routes(g, depot, deliveries, routes, path, title="Optimised delivery route", unreachable=()):
    """routes: list of full node paths (each starts/ends at the depot)."""
    fig, ax = plt.subplots(figsize=(9, 7))
    for u, v, w in g.edges():
        (x1, y1), (x2, y2) = g.coords[u], g.coords[v]
        ax.plot([x1, x2], [y1, y2], color="#cccccc", lw=1, zorder=1)
    stops = {d.node: d for d in deliveries}
    for i, full in enumerate(routes):
        c = COLORS[i % len(COLORS)]
        for a, b in zip(full, full[1:]):
            (x1, y1), (x2, y2) = g.coords[a], g.coords[b]
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle="->", color=c, lw=2), zorder=3)
        ax.plot([], [], color=c, lw=2, label=f"Vehicle {i + 1}")
    for n, (x, y) in g.coords.items():
        if n == depot:
            ax.scatter(x, y, s=260, marker="s", color="black", zorder=5)
        elif n in unreachable:
            ax.scatter(x, y, s=120, marker="X", color="red", zorder=4)
        elif n in stops:
            ax.scatter(x, y, s=40 + 25 * stops[n].priority, color="#ffcc00", edgecolor="k", zorder=4)
        else:
            ax.scatter(x, y, s=20, color="#999999", zorder=2)
        if len(g) <= 40:
            ax.annotate(n, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.scatter([], [], marker="s", color="black", label="Depot")
    ax.scatter([], [], color="#ffcc00", edgecolor="k", label="Delivery (size = priority)")
    if unreachable:
        ax.scatter([], [], marker="X", color="red", label="Not served (unreachable / over capacity)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_strategy_comparison(results, path):
    """results: {strategy: RouteStats}"""
    names = list(results)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    data = [("Total distance", [results[n].total_distance for n in names]),
            ("Late deliveries", [len(results[n].late) for n in names]),
            ("Total lateness (min)", [results[n].total_lateness for n in names])]
    for ax, (t, vals) in zip(axes, data):
        bars = ax.bar(names, vals, color=COLORS[:len(names)])
        ax.set_title(t)
        ax.tick_params(axis="x", rotation=20)
        ax.bar_label(bars, fmt="%.0f", fontsize=8)
    fig.suptitle("Greedy scheduling strategies - performance metrics")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_benchmark(rows, path, title, xkey, series, logy=True):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key, label in series:
        pts = [(r[xkey], r[key]) for r in rows if r.get(key) is not None]
        if pts:
            ax.plot(*zip(*pts), marker="o", label=label)
    ax.set_xlabel(xkey)
    ax.set_ylabel("time (ms)")
    if logy:
        ax.set_yscale("log")
        ax.set_xscale("log")
    ax.set_title(title)
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
