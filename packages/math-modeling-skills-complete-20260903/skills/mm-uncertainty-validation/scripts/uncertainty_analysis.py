"""Bootstrap a result column and quantify rank/linear sensitivity to numeric inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def split(value: str | None) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


def run(input_path: str, output_dir: str, result_column: str, parameter_arg: str | None,
        iterations: int, seed: int) -> int:
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    frame = pd.read_csv(source)
    if result_column not in frame.columns:
        raise ValueError(f"missing result column: {result_column}")
    result = pd.to_numeric(frame[result_column], errors="coerce")
    parameters = split(parameter_arg) or [c for c in frame.select_dtypes(include="number").columns if c != result_column]
    data = pd.DataFrame({result_column: result})
    for column in parameters:
        if column not in frame.columns:
            raise ValueError(f"missing parameter column: {column}")
        data[column] = pd.to_numeric(frame[column], errors="coerce")
    data = data.dropna()
    if len(data) < 5:
        raise ValueError("at least five complete rows are required")
    rng = np.random.default_rng(seed)
    values = data[result_column].to_numpy(dtype=float)
    boot = np.array([rng.choice(values, size=len(values), replace=True).mean() for _ in range(iterations)])
    rows = []
    for column in parameters:
        x = data[column].to_numpy(dtype=float)
        if np.isclose(x.std(ddof=1), 0):
            rows.append({"parameter": column, "standardized_slope": np.nan, "spearman_rho": np.nan,
                         "spearman_p": np.nan, "status": "constant"})
            continue
        slope = np.polyfit((x - x.mean()) / x.std(ddof=1), (values - values.mean()) / values.std(ddof=1), 1)[0]
        rho, p_value = spearmanr(x, values)
        rows.append({"parameter": column, "standardized_slope": float(slope),
                     "spearman_rho": float(rho), "spearman_p": float(p_value), "status": "ok"})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).sort_values("spearman_rho", key=lambda s: s.abs(), ascending=False).to_csv(
        output / "sensitivity.csv", index=False)
    summary = {"samples": len(data), "bootstrap_iterations": iterations, "seed": seed,
               "mean": float(values.mean()), "bootstrap_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
               "bootstrap_standard_error": float(boot.std(ddof=1))}
    (output / "uncertainty.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Uncertainty analysis\n\n" + "\n".join(f"- {k}: {v}" for k, v in summary.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a result and estimate input sensitivity.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--result-column", required=True)
    parser.add_argument("--parameters", help="Comma-separated numeric parameter columns.")
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        if args.iterations < 100:
            raise ValueError("iterations must be at least 100")
        return run(args.input, args.output, args.result_column, args.parameters, args.iterations, args.seed)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
