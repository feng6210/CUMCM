"""Create a hash-bound run manifest without overwriting an existing manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def record(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if not path.is_file() or root.resolve() not in path.parents:
        raise ValueError(f"input must be an existing file under root: {relative}")
    return {"path": path.relative_to(root.resolve()).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a mathematical-modeling RUN_MANIFEST.json.")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model-version", required=True)
    ap.add_argument("--solver", required=True)
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--output-file", action="append", default=[])
    ap.add_argument("--seed", action="append", default=[])
    ap.add_argument("--status", choices=("planned", "completed", "failed", "infeasible", "timeout"), default="planned")
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        ap.error("--root must be an existing directory")
    # A relative destination belongs to the versioned run directory.  Refuse a
    # destination outside it so a manifest cannot silently detach from the
    # files whose hashes it records.
    output = (args.output if args.output.is_absolute() else root / args.output).resolve()
    if output != root and root not in output.parents:
        ap.error("--output must be located under --root")
    if output.exists():
        ap.error("--output already exists; manifests are append-only artifacts")
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": args.model_version,
        "solver": args.solver,
        "status": args.status,
        "seeds": args.seed,
        "inputs": [record(root, item) for item in args.input],
        "outputs": [record(root, item) for item in args.output_file],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
