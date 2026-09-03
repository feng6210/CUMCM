#!/usr/bin/env python3
"""Create a factual inventory and conservative static audit of a local modeling corpus.

This script checks files, hashes and selected source-code syntax. It never judges
whether a model, experiment, paper or claim is semantically correct.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRIMARY_EXTENSIONS = {
    ".py", ".m", ".java", ".nb", ".ipynb", ".txt", ".md", ".pdf",
    ".docx", ".doc", ".csv", ".xlsx", ".xls", ".mat", ".zip", ".rar",
}
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".mp4", ".wmv", ".mkv"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_python(path: Path) -> tuple[str | None, str | None]:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding), None
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            return None, f"{type(exc).__name__}: {exc}"
    return None, "unable to decode as UTF-8 or GB18030"


def audit_python(path: Path) -> dict[str, Any]:
    text, error = read_python(path)
    if error or text is None:
        return {"read_error": error}
    try:
        tree = ast.parse(text, filename=str(path))
        syntax = "OK"
    except SyntaxError as exc:
        tree = None
        syntax = f"ERROR:{exc.msg}:line={exc.lineno}"

    imports: set[str] = set()
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

    patterns = {
        "synthetic_data": r"np\.random|make_(?:classification|regression|blobs)|生成示例数据",
        "fixed_seed": r"random_state\s*=|np\.random\.seed|random\.seed",
        "random_split": r"train_test_split",
        "time_split": r"TimeSeriesSplit|walk.?forward|expanding|rolling",
        "external_data": r"read_csv|read_excel|loadmat",
        "solver_status": r"\.success|\.status|exitflag|termination",
        "machine_output": r"to_csv|to_excel|json\.dump|savez|savemat",
    }
    return {
        "syntax": syntax,
        "imports": sorted(imports),
        "signals": sorted(name for name, pattern in patterns.items() if re.search(pattern, text, re.I)),
        "lines": text.count("\n") + 1,
    }


def role_for(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if ext in {".py", ".m", ".java", ".nb", ".ipynb"}:
        return "source_code"
    if ext in {".csv", ".xlsx", ".xls", ".mat"}:
        return "data"
    if ext in {".zip", ".rar"}:
        return "archive"
    if ext == ".downloading" or name.endswith(".baiduyun.p.downloading"):
        return "incomplete_download"
    if ext in MEDIA_EXTENSIONS:
        return "media_or_scan"
    if ext in {".pdf", ".docx", ".doc", ".txt", ".md"}:
        return "document"
    return "other"


def build_report(root: Path, max_hash_bytes: int) -> dict[str, Any]:
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda p: str(p).lower())
    extension_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    python_counts: Counter[str] = Counter()
    hash_error_count = 0

    for path in files:
        relative = path.relative_to(root).as_posix()
        extension = path.suffix.lower() or "[none]"
        role = role_for(path)
        extension_counts[extension] += 1
        role_counts[role] += 1
        record: dict[str, Any] = {
            "relative_path": relative,
            "bytes": path.stat().st_size,
            "extension": extension,
            "role": role,
        }
        if extension in PRIMARY_EXTENSIONS and path.stat().st_size <= max_hash_bytes:
            try:
                record["sha256"] = sha256_file(path)
            except OSError as exc:
                hash_error_count += 1
                record["sha256"] = None
                record["hash_error"] = f"{type(exc).__name__}: {exc}"
        else:
            record["sha256"] = None
            record["hash_skip_reason"] = "outside_primary_scope_or_size_limit"
        if extension == ".py":
            audit = audit_python(path)
            record["python_static_audit"] = audit
            python_counts[audit.get("syntax", "READ_ERROR")] += 1
            for signal in audit.get("signals", []):
                python_counts[f"signal:{signal}"] += 1
        records.append(record)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root.resolve()),
        "semantic_pass": False,
        "semantic_pass_reason": "This report is an inventory and static precheck only.",
        "total_files": len(files),
        "total_bytes": sum(record["bytes"] for record in records),
        "extension_counts": dict(sorted(extension_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "python_static_counts": dict(sorted(python_counts.items())),
        "hash_error_count": hash_error_count,
        "files": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory and statically audit a local math-modeling corpus.")
    parser.add_argument("--root", required=True, type=Path, help="Corpus root directory.")
    parser.add_argument("--output", required=True, type=Path, help="JSON report path.")
    parser.add_argument(
        "--max-hash-mib",
        type=int,
        default=128,
        help="Maximum size of an eligible file to hash (default: 128 MiB).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Corpus root is not a directory: {root}")
    report = build_report(root, args.max_hash_mib * 1024 * 1024)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "total_files": report["total_files"],
        "semantic_pass": report["semantic_pass"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
