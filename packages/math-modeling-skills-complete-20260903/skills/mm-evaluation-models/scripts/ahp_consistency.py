"""Calculate AHP weights and consistency ratio for a judgment matrix."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_matrix(path):
    if path is None:
        return np.array([[1, 3, 5], [1/3, 1, 2], [1/5, 1/2, 1]], dtype=float)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input file not found: {p}")
    df = pd.read_csv(p, header=None)
    matrix = df.to_numpy(dtype=float)
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("AHP judgment matrix must be square")
    if np.any(matrix <= 0):
        raise ValueError("AHP judgment matrix values must be positive")
    if not np.allclose(np.diag(matrix), 1.0, rtol=0, atol=1e-8):
        raise ValueError("AHP diagonal values must equal 1")
    if not np.allclose(matrix * matrix.T, 1.0, rtol=1e-5, atol=1e-8):
        raise ValueError("AHP matrix must be reciprocal: a_ij * a_ji = 1")
    return matrix


def run(input_path, output_dir):
    matrix = load_matrix(input_path)
    n = matrix.shape[0]
    if n > max(RI):
        raise ValueError("RI table in this script supports matrix size n <= 10")
    values, vectors = np.linalg.eig(matrix)
    max_idx = int(np.argmax(values.real))
    lambda_max = float(values[max_idx].real)
    weights = np.abs(vectors[:, max_idx].real)
    weights = weights / weights.sum()
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RI[n]
    cr = 0.0 if ri == 0 else ci / ri
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"item": [f"item_{i+1}" for i in range(n)], "weight": weights}).to_csv(output / "ahp_weights.csv", index=False)
    pd.DataFrame(matrix).to_csv(output / "judgment_matrix.csv", index=False, header=False)
    (output / "summary.md").write_text(
        f"# AHP Consistency Summary\n\n- lambda_max: {lambda_max:.6f}\n- CI: {ci:.6f}\n- CR: {cr:.6f}\n- Pass: {cr < 0.1}\n",
        encoding="utf-8",
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Calculate AHP weights and consistency ratio.")
    parser.add_argument("--input", help="CSV judgment matrix path. If omitted, a demo matrix is used.")
    parser.add_argument("--output", required=True, help="Output directory.")
    args = parser.parse_args()
    try:
        return run(args.input, args.output)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
