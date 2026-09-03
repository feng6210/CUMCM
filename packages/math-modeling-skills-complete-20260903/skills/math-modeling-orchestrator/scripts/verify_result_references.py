"""Check a result-evidence map with the deterministic evidence pre-check only."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_precheck(path: Path):
    spec = importlib.util.spec_from_file_location("mm_evidence_precheck", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evidence pre-check")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify result_evidence_map.json file and value references.")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--precheck", type=Path, default=Path(__file__).with_name("evidence_precheck.py"))
    args = ap.parse_args()
    data = json.loads(args.map.read_text(encoding="utf-8"))
    claims = data.get("claims", data) if isinstance(data, dict) else data
    if not isinstance(claims, list):
        ap.error("map must be a list or an object with a claims list")
    normalized = []
    for claim in claims:
        if not isinstance(claim, dict):
            normalized.append({"status": "unparseable", "detail": "claim is not an object"})
            continue
        normalized.append({"id": claim.get("claim_id"), "value": claim.get("value"), "source": claim.get("source")})
    precheck = load_precheck(args.precheck)
    result = precheck.check_batch(normalized, str(args.root.resolve()))
    result["meaning"] = "verified means only evidence existence; it does not establish that a claim is true"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not any(r["status"] in {"path_missing", "value_not_found"} for r in result["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
