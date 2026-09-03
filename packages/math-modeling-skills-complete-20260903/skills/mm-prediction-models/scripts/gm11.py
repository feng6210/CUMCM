"""Fit a GM(1,1) grey prediction model and export fitted and forecast values."""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def gm11(values, periods):
    x0 = np.asarray(values, dtype=float)
    if len(x0) < 4:
        raise ValueError("GM(1,1) requires at least 4 observations")
    if np.any(x0 <= 0):
        raise ValueError("GM(1,1) requires positive sequence values")
    x1 = np.cumsum(x0)
    z1 = 0.5 * (x1[1:] + x1[:-1])
    B = np.column_stack((-z1, np.ones(len(z1))))
    Y = x0[1:]
    a, b = np.linalg.lstsq(B, Y, rcond=None)[0]
    total = len(x0) + periods
    if abs(a) < 1e-12:
        x1_hat = x0[0] + np.arange(total) * b
    else:
        k = np.arange(total)
        x1_hat = (x0[0] - b / a) * np.exp(-a * k) + b / a
    x0_hat = np.empty(total)
    x0_hat[0] = x0[0]
    x0_hat[1:] = np.diff(x1_hat)
    return float(a), float(b), x0_hat


def diagnostics(actual, fitted):
    residual = np.asarray(actual, dtype=float) - np.asarray(fitted, dtype=float)
    s1 = float(np.std(actual, ddof=1))
    s2 = float(np.std(residual, ddof=1))
    c = s2 / s1 if s1 > 0 else np.nan
    mean_residual = float(np.mean(residual))
    threshold = 0.6745 * s1
    p = float(np.mean(np.abs(residual - mean_residual) < threshold)) if s1 > 0 else np.nan
    rel = np.abs(residual / np.asarray(actual, dtype=float))
    return {"posterior_error_ratio_C": c, "small_error_probability_P": p,
            "mean_relative_error": float(np.mean(rel)), "max_relative_error": float(np.max(rel))}


def run(input_path, output_dir, column, periods):
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    df = pd.read_csv(path)
    if column not in df.columns:
        raise ValueError(f"missing column: {column}")
    values = pd.to_numeric(df[column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"column {column} contains non-numeric or missing values")
    a, b, fitted = gm11(values.to_numpy(), periods)
    n = len(values)
    ratios = values.to_numpy()[0:-1] / values.to_numpy()[1:]
    level_lower, level_upper = np.exp(-2 / (n + 1)), np.exp(2 / (n + 1))
    level_ratio_pass = bool(np.all((ratios > level_lower) & (ratios < level_upper)))
    diag = diagnostics(values.to_numpy(), fitted[:n])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame({
        "step": np.arange(1, n + periods + 1),
        "actual": list(values) + [np.nan] * periods,
        "gm11_value": fitted,
        "type": ["fitted"] * n + ["forecast"] * periods,
    })
    result["residual"] = result["actual"] - result["gm11_value"]
    result.to_csv(output / "gm11_forecast.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(result["step"], result["gm11_value"], marker="o", label="GM(1,1)")
    ax.plot(result.loc[:n-1, "step"], result.loc[:n-1, "actual"], marker="s", label="Actual")
    ax.legend()
    ax.set_xlabel("step")
    ax.set_ylabel(column)
    fig.tight_layout()
    fig.savefig(output / "gm11_plot.png", dpi=150)
    plt.close(fig)
    pd.DataFrame([diag]).to_csv(output / "diagnostics.csv", index=False)
    (output / "summary.md").write_text(
        f"# GM(1,1) Summary\n\n- a: {a:.6f}\n- b: {b:.6f}\n- Forecast periods: {periods}\n"
        f"- Level-ratio test pass: {level_ratio_pass}\n- Level-ratio interval: ({level_lower:.6f}, {level_upper:.6f})\n"
        f"- Posterior error ratio C: {diag['posterior_error_ratio_C']:.6f}\n"
        f"- Small-error probability P: {diag['small_error_probability_P']:.6f}\n",
        encoding="utf-8",
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Fit and forecast with GM(1,1).")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output", required=True, help="Output directory.")
    parser.add_argument("--column", default="value", help="Positive numeric sequence column.")
    parser.add_argument("--periods", type=int, default=3, help="Forecast periods.")
    args = parser.parse_args()
    try:
        if args.periods < 0:
            raise ValueError("periods must be non-negative")
        return run(args.input, args.output, args.column, args.periods)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
