"""Train classification baselines and export metrics plus confusion matrix."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_cols(value):
    return [x.strip() for x in value.split(",") if x.strip()] if value else []


def run(input_path, output_dir, target, features_arg, model_name, test_size, seed, group_column, time_column):
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"input file not found: {p}")
    df = pd.read_csv(p)
    if target not in df.columns:
        raise ValueError(f"missing target column: {target}")
    features = parse_cols(features_arg) or [c for c in df.select_dtypes(include="number").columns if c != target]
    if not features:
        raise ValueError("no numeric feature columns available")
    if group_column and time_column:
        raise ValueError("use only one of --group-column and --time-column")
    aux = [c for c in [group_column, time_column] if c]
    for col in aux:
        if col not in df.columns:
            raise ValueError(f"missing split column: {col}")
    data = df[features + [target] + aux].dropna()
    if len(data) < 6:
        raise ValueError("at least 6 complete rows are required")
    X = data[features].apply(pd.to_numeric, errors="coerce")
    if X.isna().any().any():
        raise ValueError("features must be numeric")
    y = data[target]
    if y.nunique() < 2:
        raise ValueError("classification requires at least two classes")
    if group_column:
        if data[group_column].nunique() < 2:
            raise ValueError("group split requires at least two distinct groups")
        train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed).split(X, y, data[group_column]))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        split_method = f"group holdout: {group_column}"
    elif time_column:
        order = pd.to_datetime(data[time_column], errors="coerce")
        if order.isna().any():
            raise ValueError("time split column contains invalid timestamps")
        sorted_idx = order.sort_values().index
        X, y = X.loc[sorted_idx], y.loc[sorted_idx]
        split = int(len(X) * (1 - test_size))
        if split <= 0 or split >= len(X):
            raise ValueError("invalid time split")
        X_train, X_test, y_train, y_test = X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]
        split_method = f"chronological holdout: {time_column}"
    else:
        min_count = int(y.value_counts().min())
        n_test = int(np.ceil(len(y) * test_size))
        stratify = y if min_count >= 2 and n_test >= y.nunique() else None
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=stratify)
        split_method = "stratified random holdout" if stratify is not None else "random holdout (stratification infeasible)"
    if y_train.nunique() < 2:
        raise ValueError("training split contains fewer than two classes; use more data or a different split")
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    models = {
        "logistic": LogisticRegression(max_iter=1000),
        "decision_tree": DecisionTreeClassifier(random_state=seed),
        "random_forest": RandomForestClassifier(n_estimators=100, random_state=seed),
        "svm": SVC(),
    }
    model = models[model_name]
    if model_name in {"logistic", "svm"}:
        model.fit(X_train_s, y_train)
        pred = model.predict(X_test_s)
        score_X = X_test_s
    else:
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        score_X = X_test
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="weighted", zero_division=0)
    auc = np.nan
    if y.nunique() == 2 and y_test.nunique() == 2:
        if hasattr(model, "predict_proba"):
            score = model.predict_proba(score_X)[:, 1]
        elif hasattr(model, "decision_function"):
            score = model.decision_function(score_X)
        else:
            score = None
        if score is not None:
            auc = roc_auc_score(y_test, score)
    metrics = pd.DataFrame([{"model": model_name, "split": split_method, "train_rows": len(y_train), "test_rows": len(y_test),
                             "accuracy": accuracy_score(y_test, pred), "precision": precision, "recall": recall, "f1": f1, "roc_auc": auc}])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output / "metrics.csv", index=False)
    labels = sorted(y.unique())
    pd.DataFrame(confusion_matrix(y_test, pred, labels=labels), index=labels, columns=labels).to_csv(output / "confusion_matrix.csv")
    pd.DataFrame({"actual": y_test.to_numpy(), "predicted": pred}).to_csv(output / "predictions.csv", index=False)
    (output / "summary.md").write_text(
        f"# Classification Baseline\n\n- Model: {model_name}\n- Split: {split_method}\n"
        f"- Train rows: {len(y_train)}\n- Test rows: {len(y_test)}\n"
        "- Leakage rule: preprocessing was fitted on the training split only.\n",
        encoding="utf-8",
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Train a classification baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--features")
    parser.add_argument("--model", choices=["logistic", "decision_tree", "random_forest", "svm"], default="logistic")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--group-column", help="Keep all rows from the same subject/device/entity in one split.")
    parser.add_argument("--time-column", help="Sort by time and reserve the latest rows for testing.")
    args = parser.parse_args()
    try:
        return run(args.input, args.output, args.target, args.features, args.model, args.test_size, args.seed,
                   args.group_column, args.time_column)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
