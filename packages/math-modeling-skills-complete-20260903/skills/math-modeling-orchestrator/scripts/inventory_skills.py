"""Create a deterministic file inventory and SHA-256 manifest for Skill folders."""
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


def is_math_skill(path: Path) -> bool:
    return path.is_dir() and (path.name == "math-modeling-orchestrator" or path.name.startswith("mm-"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a SHA-256 inventory for mathematical-modeling Skills.")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--label", default="math-modeling-skills")
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        ap.error("--root must be an existing directory")
    skills = sorted(path for path in root.iterdir() if is_math_skill(path))
    files = []
    for skill in skills:
        for path in sorted(item for item in skill.rglob("*") if item.is_file()):
            files.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    report = {
        "label": args.label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "skill_count": len(skills),
        "skills": [path.name for path in skills],
        "file_count": len(files),
        "files": files,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("label", "skill_count", "file_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
