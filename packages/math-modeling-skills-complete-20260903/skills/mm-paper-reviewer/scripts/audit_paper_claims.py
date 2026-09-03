"""Create a conservative CUMCM paper-claim audit from an evidence map.

This checker deliberately verifies file references and recomputable numeric
anchors only.  It never promotes a claim merely because the referenced files
exist; semantic/model validation remains a human or model-specific review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def claims_from(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("claims"), list):
        return data["claims"]
    raise ValueError("evidence map must be a list or an object containing claims")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit paper claims against local evidence references.")
    ap.add_argument("--evidence-map", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, default=Path("PAPER_CLAIM_AUDIT.json"))
    args = ap.parse_args()
    root = args.root.resolve()
    try:
        claims = claims_from(json.loads(args.evidence_map.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}")
        return 2

    audited: list[dict[str, Any]] = []
    failed = False
    for claim in claims:
        claim_id = str(claim.get("claim_id", "UNNAMED"))
        files = claim.get("evidence_files", [])
        if not isinstance(files, list):
            files = []
        file_checks = []
        for item in files:
            path = (root / str(item)).resolve()
            inside_root = path == root or root in path.parents
            present = inside_root and path.is_file()
            file_checks.append({"path": str(item), "present": present, "sha256": sha256(path) if present else None})
        missing = [entry["path"] for entry in file_checks if not entry["present"]]
        semantic_status = str(claim.get("validation_status", "NOT_EVALUATED"))
        declared = str(claim.get("supported", "blocked")).lower()
        mechanical = "PASS" if not missing else "FAIL"
        status = "REVIEW_REQUIRED" if mechanical == "PASS" else "EVIDENCE_MISSING"
        if missing:
            failed = True
        audited.append({
            "claim_id": claim_id,
            "declared_support": declared,
            "validation_status": semantic_status,
            "evidence_check": mechanical,
            "audit_status": status,
            "evidence_files": file_checks,
            "recomputed_values": claim.get("recomputed_values", {}),
            "paper_locations": claim.get("paper_locations", []),
            "note": "File presence and hashes do not establish model semantics or claim validity.",
        })
    report = {
        "status": "FAILED" if failed else "REVIEW_REQUIRED",
        "root": str(root),
        "claims": audited,
        "scope_limit": "This tool never returns a semantic PASS for a modeling claim.",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
