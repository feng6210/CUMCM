"""Solve a damped forced oscillator and report a numerical-convergence check."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_params(path: str | None) -> dict:
    params = {"mass": 1.0, "damping": 0.2, "stiffness": 2.0, "force_amplitude": 1.0,
              "force_frequency": 1.0, "x0": 0.0, "v0": 0.0, "t_end": 20.0, "samples": 401}
    if path:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"input file not found: {source}")
        params.update(json.loads(source.read_text(encoding="utf-8")))
    if params["mass"] <= 0 or params["stiffness"] < 0 or params["damping"] < 0:
        raise ValueError("mass must be positive; damping and stiffness must be non-negative")
    if params["t_end"] <= 0 or int(params["samples"]) < 3:
        raise ValueError("t_end must be positive and samples >= 3")
    return params


def solve(params: dict, rtol: float, atol: float, times: np.ndarray):
    def rhs(t, state):
        x, v = state
        force = params["force_amplitude"] * np.cos(params["force_frequency"] * t)
        a = (force - params["damping"] * v - params["stiffness"] * x) / params["mass"]
        return [v, a]

    result = solve_ivp(rhs, (0.0, params["t_end"]), [params["x0"], params["v0"]],
                       t_eval=times, method="RK45", rtol=rtol, atol=atol)
    if not result.success:
        raise RuntimeError(result.message)
    return result, rhs


def run(input_path: str | None, output_dir: str, rtol: float, atol: float) -> int:
    params = load_params(input_path)
    times = np.linspace(0.0, float(params["t_end"]), int(params["samples"]))
    result, rhs = solve(params, rtol, atol, times)
    tighter, _ = solve(params, rtol / 10.0, atol / 10.0, times)
    delta = np.max(np.abs(result.y - tighter.y), axis=1)
    derivatives = np.array([rhs(t, result.y[:, i]) for i, t in enumerate(times)])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time": times, "position": result.y[0], "velocity": result.y[1],
                  "acceleration": derivatives[:, 1]}).to_csv(output / "trajectory.csv", index=False)
    diagnostics = {"solver": "RK45", "rtol": rtol, "atol": atol, "nfev": result.nfev,
                   "max_position_change_tighter": float(delta[0]), "max_velocity_change_tighter": float(delta[1])}
    (output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# ODE system result\n\n" + "\n".join(f"- {k}: {v}" for k, v in diagnostics.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve a damped forced oscillator with convergence diagnostics.")
    parser.add_argument("--input", help="Optional JSON parameters.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--rtol", type=float, default=1e-7)
    parser.add_argument("--atol", type=float, default=1e-9)
    args = parser.parse_args()
    try:
        if args.rtol <= 0 or args.atol <= 0:
            raise ValueError("rtol and atol must be positive")
        return run(args.input, args.output, args.rtol, args.atol)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
