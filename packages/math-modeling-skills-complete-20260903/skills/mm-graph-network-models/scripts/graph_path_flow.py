"""Solve shortest-path, maximum-flow, or minimum-spanning-tree graph models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_edges(path: str) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    frame = pd.read_csv(source)
    required = {"source", "target"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing edge columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("edge table is empty")
    return frame


def build_graph(frame: pd.DataFrame, directed: bool, weight_column: str, capacity_column: str):
    graph = nx.DiGraph() if directed else nx.Graph()
    for idx, row in frame.iterrows():
        attrs = {"row": int(idx)}
        if weight_column in frame.columns:
            weight = float(row[weight_column])
            if not pd.notna(weight):
                raise ValueError(f"row {idx}: invalid weight")
            attrs["weight"] = weight
        else:
            attrs["weight"] = 1.0
        if capacity_column in frame.columns:
            capacity = float(row[capacity_column])
            if capacity < 0:
                raise ValueError(f"row {idx}: capacity must be non-negative")
            attrs["capacity"] = capacity
        graph.add_edge(str(row["source"]), str(row["target"]), **attrs)
    return graph


def run(input_path: str, output_dir: str, algorithm: str, source: str | None, target: str | None,
        directed: bool, weight_column: str, capacity_column: str) -> int:
    frame = load_edges(input_path)
    graph = build_graph(frame, directed, weight_column, capacity_column)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    status = {"algorithm": algorithm, "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}

    if algorithm == "shortest-path":
        if source is None or target is None:
            raise ValueError("shortest-path requires --source and --target")
        negative = [(u, v) for u, v, d in graph.edges(data=True) if d["weight"] < 0]
        if negative:
            if nx.negative_edge_cycle(graph, weight="weight"):
                raise ValueError("reachable negative cycle makes shortest path undefined")
            path = nx.bellman_ford_path(graph, source, target, weight="weight")
            method = "bellman-ford"
        else:
            path = nx.dijkstra_path(graph, source, target, weight="weight")
            method = "dijkstra"
        rows = []
        total = 0.0
        for order, (u, v) in enumerate(zip(path[:-1], path[1:]), 1):
            weight = float(graph[u][v]["weight"])
            total += weight
            rows.append({"order": order, "source": u, "target": v, "weight": weight, "cumulative_weight": total})
        pd.DataFrame(rows).to_csv(output / "path_edges.csv", index=False)
        status.update({"method": method, "source": source, "target": target, "path": path, "objective": total})
    elif algorithm == "max-flow":
        if source is None or target is None:
            raise ValueError("max-flow requires --source and --target")
        if capacity_column not in frame.columns:
            raise ValueError(f"max-flow requires capacity column: {capacity_column}")
        if not directed:
            raise ValueError("max-flow requires --directed to make capacity direction explicit")
        value, flow = nx.maximum_flow(graph, source, target, capacity="capacity")
        rows = [{"source": u, "target": v, "flow": f, "capacity": graph[u][v]["capacity"]}
                for u, targets in flow.items() for v, f in targets.items() if graph.has_edge(u, v)]
        pd.DataFrame(rows).to_csv(output / "edge_flows.csv", index=False)
        cut_value, partition = nx.minimum_cut(graph, source, target, capacity="capacity")
        status.update({"source": source, "target": target, "objective": float(value),
                       "min_cut": float(cut_value), "cut_partition": [sorted(partition[0]), sorted(partition[1])]})
    else:
        if directed:
            raise ValueError("minimum-spanning-tree requires an undirected graph")
        if not nx.is_connected(graph):
            raise ValueError("minimum-spanning-tree requires a connected graph")
        tree = nx.minimum_spanning_tree(graph, weight="weight")
        rows = [{"source": u, "target": v, "weight": float(d["weight"])} for u, v, d in tree.edges(data=True)]
        pd.DataFrame(rows).to_csv(output / "tree_edges.csv", index=False)
        status.update({"objective": float(sum(d["weight"] for _, _, d in tree.edges(data=True))),
                       "tree_edges": tree.number_of_edges()})

    (output / "result.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Graph model result\n\n" + "\n".join(f"- {k}: {v}" for k, v in status.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve graph shortest path, maximum flow, or minimum spanning tree.")
    parser.add_argument("--input", required=True, help="CSV edge table with source,target and optional weight/capacity.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--algorithm", choices=["shortest-path", "max-flow", "minimum-spanning-tree"], default="shortest-path")
    parser.add_argument("--source")
    parser.add_argument("--target")
    parser.add_argument("--directed", action="store_true")
    parser.add_argument("--weight-column", default="weight")
    parser.add_argument("--capacity-column", default="capacity")
    args = parser.parse_args()
    try:
        return run(args.input, args.output, args.algorithm, args.source, args.target, args.directed,
                   args.weight_column, args.capacity_column)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
