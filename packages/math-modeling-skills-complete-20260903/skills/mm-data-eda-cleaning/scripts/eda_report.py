"""Generate an EDA report for CSV or Excel data used in math modeling."""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_table(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(p)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(p)
    else:
        raise ValueError("supported input formats: .csv, .xlsx, .xls")
    if df.empty:
        raise ValueError("input CSV is empty")
    return df


def write_plot(df, output):
    plots_dir = output / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    numeric = df.select_dtypes(include="number")
    for col in numeric.columns[:6]:
        fig, ax = plt.subplots(figsize=(6, 4))
        numeric[col].dropna().hist(ax=ax, bins=10)
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("count")
        fig.tight_layout()
        fig.savefig(plots_dir / f"hist_{col}.png", dpi=150)
        plt.close(fig)
    categorical = df.select_dtypes(exclude="number")
    for col in categorical.columns[:3]:
        counts = categorical[col].astype(str).value_counts().head(10)
        fig, ax = plt.subplots(figsize=(7, 4))
        counts.plot(kind="bar", ax=ax)
        ax.set_title(f"Top categories of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("count")
        fig.tight_layout()
        fig.savefig(plots_dir / f"bar_{col}.png", dpi=150)
        plt.close(fig)


def run(input_path, output_dir):
    df = load_table(input_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    missing = pd.DataFrame({
        "column": df.columns,
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_rate": [float(df[c].isna().mean()) for c in df.columns],
    })
    missing.to_csv(output / "missing_values.csv", index=False)

    numeric = df.select_dtypes(include="number")
    categorical = df.select_dtypes(exclude="number")
    if not numeric.empty:
        numeric.describe().T.to_csv(output / "describe_numeric.csv")
        numeric.corr().to_csv(output / "correlation.csv")
        outlier_rows = []
        for col in numeric.columns:
            values = numeric[col].dropna()
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (numeric[col] < lower) | (numeric[col] > upper)
            outlier_rows.append({"column": col, "q1": q1, "q3": q3, "lower_fence": lower,
                                 "upper_fence": upper, "outlier_count": int(mask.sum()),
                                 "outlier_rate": float(mask.mean())})
        pd.DataFrame(outlier_rows).to_csv(output / "outlier_iqr_summary.csv", index=False)
    else:
        pd.DataFrame().to_csv(output / "describe_numeric.csv")
        pd.DataFrame().to_csv(output / "correlation.csv")
        pd.DataFrame(columns=["column", "q1", "q3", "lower_fence", "upper_fence", "outlier_count", "outlier_rate"]).to_csv(
            output / "outlier_iqr_summary.csv", index=False)
    if not categorical.empty:
        rows = []
        for col in categorical.columns:
            counts = categorical[col].astype(str).value_counts(dropna=False).head(20)
            for value, count in counts.items():
                rows.append({"column": col, "value": value, "count": int(count)})
        pd.DataFrame(rows).to_csv(output / "describe_categorical.csv", index=False)
    else:
        pd.DataFrame(columns=["column", "value", "count"]).to_csv(output / "describe_categorical.csv", index=False)

    write_plot(df, output)
    duplicate_count = int(df.duplicated().sum())
    summary = [
        "# EDA Summary",
        "",
        f"- Rows: {len(df)}",
        f"- Columns: {len(df.columns)}",
        f"- Duplicate rows: {duplicate_count}",
        f"- Numeric columns: {len(numeric.columns)}",
        f"- Categorical columns: {len(categorical.columns)}",
        "",
        "## Columns",
        "",
    ]
    for col in df.columns:
        summary.append(f"- `{col}`: {df[col].dtype}, missing={int(df[col].isna().sum())}")
    (output / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate CSV/Excel EDA report files.")
    parser.add_argument("--input", required=True, help="Input CSV, XLSX, or XLS path.")
    parser.add_argument("--output", required=True, help="Output directory.")
    args = parser.parse_args()
    try:
        return run(args.input, args.output)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
