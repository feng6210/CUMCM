"""Compute speed and detect threshold-crossing events from a 2-D trajectory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def run(input_path: str, output_dir: str, time_column: str, x_column: str, y_column: str,
        threshold: float) -> int:
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    frame = pd.read_csv(source)
    columns = [time_column, x_column, y_column]
    if any(column not in frame.columns for column in columns):
        raise ValueError(f"required columns: {columns}")
    data = frame[columns].apply(pd.to_numeric, errors="coerce").dropna().sort_values(time_column)
    if len(data) < 3 or data[time_column].duplicated().any():
        raise ValueError("trajectory needs at least three rows and unique timestamps")
    t, x, y = (data[column].to_numpy(dtype=float) for column in columns)
    dt = np.diff(t)
    if np.any(dt <= 0):
        raise ValueError("timestamps must be strictly increasing")
    dx, dy = np.diff(x), np.diff(y)
    speed = np.r_[np.nan, np.hypot(dx, dy) / dt]
    distance = np.hypot(x, y)
    inside = distance <= threshold
    transition = np.r_[False, inside[1:] != inside[:-1]]
    events = pd.DataFrame({"time": t[transition], "event": np.where(inside[transition], "enter", "exit"),
                           "distance": distance[transition]})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = data.copy()
    result["speed"] = speed
    result["distance_to_origin"] = distance
    result["inside_threshold"] = inside
    result.to_csv(output / "trajectory_features.csv", index=False)
    events.to_csv(output / "events.csv", index=False)
    meta = {"rows": len(data), "threshold": threshold, "event_count": len(events),
            "max_speed": float(np.nanmax(speed)), "min_distance": float(distance.min())}
    (output / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Trajectory events\n\n" + "\n".join(f"- {k}: {v}" for k, v in meta.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute 2-D trajectory speed and origin-threshold events.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--x-column", default="x")
    parser.add_argument("--y-column", default="y")
    parser.add_argument("--threshold", type=float, required=True)
    args = parser.parse_args()
    try:
        if args.threshold < 0:
            raise ValueError("threshold must be non-negative")
        return run(args.input, args.output, args.time_column, args.x_column, args.y_column, args.threshold)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
