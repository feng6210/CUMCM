"""Compute a windowed spectrum after checking and regularizing the sampling axis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def run(input_path: str, output_dir: str, x_column: str, y_column: str, peaks: int) -> int:
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    frame = pd.read_csv(source)
    if x_column not in frame.columns or y_column not in frame.columns:
        raise ValueError("missing x or y column")
    data = frame[[x_column, y_column]].apply(pd.to_numeric, errors="coerce").dropna().sort_values(x_column)
    data = data.groupby(x_column, as_index=False)[y_column].mean()
    if len(data) < 8:
        raise ValueError("at least eight unique samples are required")
    x = data[x_column].to_numpy(dtype=float)
    y = data[y_column].to_numpy(dtype=float)
    spacing = np.diff(x)
    if np.any(spacing <= 0):
        raise ValueError("x values must be strictly increasing after duplicate aggregation")
    nonuniformity = float(np.std(spacing) / np.mean(spacing))
    x_uniform = np.linspace(x[0], x[-1], len(x))
    y_uniform = np.interp(x_uniform, x, y)
    dx = float(x_uniform[1] - x_uniform[0])
    windowed = (y_uniform - y_uniform.mean()) * np.hanning(len(y_uniform))
    amplitude = np.abs(np.fft.rfft(windowed)) * 2.0 / max(np.hanning(len(y_uniform)).sum(), 1.0)
    frequency = np.fft.rfftfreq(len(y_uniform), d=dx)
    peak_idx, _ = find_peaks(amplitude[1:])
    peak_idx = peak_idx + 1
    peak_idx = peak_idx[np.argsort(amplitude[peak_idx])[::-1][:peaks]] if len(peak_idx) else np.array([], dtype=int)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"frequency": frequency, "amplitude": amplitude}).to_csv(output / "spectrum.csv", index=False)
    pd.DataFrame({"frequency": frequency[peak_idx], "amplitude": amplitude[peak_idx]}).to_csv(output / "peaks.csv", index=False)
    pd.DataFrame({x_column: x_uniform, y_column: y_uniform}).to_csv(output / "uniform_signal.csv", index=False)
    meta = {"samples": len(x), "x_range": [float(x[0]), float(x[-1])], "uniform_dx": dx,
            "original_spacing_cv": nonuniformity, "frequency_resolution": float(1.0 / (len(x_uniform) * dx)),
            "window": "hann", "detrend": "mean"}
    (output / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Signal spectrum\n\n" + "\n".join(f"- {k}: {v}" for k, v in meta.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Regularize sampling and compute a Hann-window FFT spectrum.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--x-column", required=True)
    parser.add_argument("--y-column", required=True)
    parser.add_argument("--peaks", type=int, default=5)
    args = parser.parse_args()
    try:
        if args.peaks < 1:
            raise ValueError("peaks must be positive")
        return run(args.input, args.output, args.x_column, args.y_column, args.peaks)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
