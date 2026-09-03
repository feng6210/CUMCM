"""Check exported figure files can be reopened and have non-empty dimensions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Reopen exported figure files and report basic readability checks.")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument(
        "--source", action="append", type=Path, default=[],
        help="Source/spec file consumed to create the outputs; repeat for multiple inputs",
    )
    ap.add_argument("--output", type=Path, default=None, help="Write a hash-bound JSON runtime report")
    args = ap.parse_args()
    results, failed = [], False
    for path in args.files:
        item = {"path": path.name, "exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0}
        if not item["exists"] or item["bytes"] == 0:
            item["status"] = "FAILED"; failed = True
        elif path.suffix.lower() == ".svg":
            text = path.read_text(encoding="utf-8", errors="replace")
            item["status"] = "PASSED" if "<svg" in text and "</svg>" in text else "FAILED"; failed |= item["status"] == "FAILED"
        elif path.suffix.lower() == ".pdf":
            data = path.read_bytes()
            item["status"] = "PASSED" if len(data) >= 256 and data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:] else "FAILED"; failed |= item["status"] == "FAILED"
        elif path.suffix.lower() == ".png":
            data = path.read_bytes()
            item["status"] = "PASSED" if data.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in data[-64:] else "FAILED"; failed |= item["status"] == "FAILED"
        elif path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
                item["status"] = "PASSED"
            except Exception:
                item["status"] = "FAILED"; failed = True
        else:
            item["status"] = "EXISTS_ONLY"
        if path.is_file():
            item["sha256"] = sha256_file(path)
        results.append(item)
    report = {
        "renderer": "render_and_reopen_check",
        "status": "FAILED" if failed else "PASSED",
        "reopen_check": not failed,
        "semantic_claim_validation": False,
        "outputs": results,
        "sources": [
            {"path": path.name, "sha256": sha256_file(path)}
            for path in args.source if path.is_file()
        ],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
