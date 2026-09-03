"""Solve a finite-horizon inventory/resource decision by backward dynamic programming."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_problem(path: str | None) -> dict:
    problem = {"demand": [3, 2, 4, 3], "capacity": 8, "initial_inventory": 0,
               "unit_cost": [2.0, 3.0, 2.5, 4.0], "holding_cost": 0.4, "terminal_inventory": 0}
    if path:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"input file not found: {source}")
        problem.update(json.loads(source.read_text(encoding="utf-8")))
    n = len(problem["demand"])
    if n == 0 or len(problem["unit_cost"]) != n:
        raise ValueError("demand and unit_cost must be non-empty and have equal length")
    if int(problem["capacity"]) < 0:
        raise ValueError("capacity must be non-negative")
    return problem


def run(input_path: str | None, output_dir: str) -> int:
    p = load_problem(input_path)
    horizon, capacity = len(p["demand"]), int(p["capacity"])
    terminal = int(p["terminal_inventory"])
    inf = float("inf")
    value = {(horizon, terminal): 0.0}
    policy = {}
    for t in range(horizon - 1, -1, -1):
        demand = int(p["demand"][t])
        for inventory in range(capacity + 1):
            best = (inf, None, None)
            for order in range(capacity - inventory + 1):
                available = inventory + order
                if available < demand:
                    continue
                next_inventory = available - demand
                continuation = value.get((t + 1, next_inventory), inf)
                cost = float(p["unit_cost"][t]) * order + float(p["holding_cost"]) * next_inventory + continuation
                if cost < best[0]:
                    best = (cost, order, next_inventory)
            if best[1] is not None:
                value[(t, inventory)] = best[0]
                policy[(t, inventory)] = (best[1], best[2])
    state = int(p["initial_inventory"])
    if (0, state) not in value:
        raise ValueError("no feasible policy from initial inventory")
    rows = []
    for t in range(horizon):
        order, next_state = policy[(t, state)]
        rows.append({"stage": t + 1, "inventory_before": state, "order": order,
                     "demand": p["demand"][t], "inventory_after": next_state,
                     "cost_to_go": value[(t, state)]})
        state = next_state
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "optimal_policy.csv", index=False)
    summary = {"minimum_cost": value[(0, int(p["initial_inventory"]))], "terminal_inventory": state,
               "states_evaluated": len(value), "horizon": horizon}
    (output / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Dynamic programming result\n\n" + "\n".join(f"- {k}: {v}" for k, v in summary.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Finite-horizon resource dynamic-programming template.")
    parser.add_argument("--input", help="Optional JSON problem.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        return run(args.input, args.output)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
