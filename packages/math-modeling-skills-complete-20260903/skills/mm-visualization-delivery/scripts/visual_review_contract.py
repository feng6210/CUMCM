"""Hash-bound review records, not an automated aesthetic/scientific verdict."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

CHECKS = {"layout", "palette", "whitespace", "hierarchy", "final_size",
          "grayscale", "chinese_labels", "units", "reference_comparison"}
MECHANISM_CHECKS = {"entities", "arrows", "branches", "stop_conditions", "no_invented_mechanism"}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bound_file(record, root: Path, label: str):
    if not isinstance(record, dict) or not record.get("file"):
        raise ValueError(f"{label}: hash-bound file required")
    path = Path(record["file"])
    path = path if path.is_absolute() else root / path
    if not path.is_file() or digest(path) != record.get("sha256"):
        raise ValueError(f"{label}: missing/stale file or hash mismatch")
    return path

def validate_review(entry, root: Path) -> list[str]:
    errors = []
    try:
        path = bound_file(entry.get("visual_review"), root, "visual_review")
        review = json.loads(path.read_text(encoding="utf-8"))
        # Every reference in a review is relative to the intent base, not the review file.
        required = {}
        for field, key in (("latex_output", "output"), ("editable_output", "editable")):
            target = Path(entry[field])
            target = target if target.is_absolute() else root / target
            required[key] = digest(target)
        if review.get("bindings", {}).get("output") != required["output"]:
            errors.append("visual_review: stale output binding")
        if review.get("bindings", {}).get("editable") != required["editable"]:
            errors.append("visual_review: stale editable/brief binding")
        # Bind the entire intent except fields that would introduce a hash cycle.
        payload = {k: v for k, v in entry.items() if k not in {"visual_review"}}
        intent_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                                separators=(",", ":")).encode()).hexdigest()
        if review.get("bindings", {}).get("intent") != intent_hash:
            errors.append("visual_review: stale intent/source/style/spec binding")
        ref = entry.get("style_reference")
        if not isinstance(ref, dict) or not ref.get("card_id"):
            errors.append("style_reference: card_id required")
        else:
            bound_file(ref.get("catalog"), root, "style_reference.catalog")
            bound_file(ref.get("preview"), root, "style_reference.preview")
            catalog = json.loads(bound_file(ref["catalog"], root, "catalog").read_text(encoding="utf-8"))
            cards = catalog.get("cards", [])
            if ref["card_id"] not in {c["card_id"] for c in cards}:
                errors.append("style_reference: unknown card_id")
            else:
                selected = next(c for c in cards if c["card_id"] == ref["card_id"])
                if ref["preview"].get("sha256") != selected.get("preview_sha256"):
                    errors.append("style_reference: preview does not belong to selected card")
        if review.get("decision") != "PASSED":
            errors.append("visual_review: decision not PASSED")
        generator = review.get("generator_id")
        reviewers = review.get("reviewers", [])
        if not generator or not isinstance(reviewers, list) or not reviewers:
            errors.append("visual_review: generator_id and reviewers required")
            reviewers = []
        visual = [r for r in reviewers if r.get("role") == "visual"]
        independent = [r for r in visual if r.get("reviewer_id") and
                       r["reviewer_id"] != generator and
                       r.get("origin") in {"same-family-fresh", "external"}]
        if not independent:
            errors.append("visual_review: independent visual reviewer missing (do not claim independence)")
        checks = review.get("checks", {})
        required_checks = CHECKS | (MECHANISM_CHECKS if entry.get("narrative_role") in
                                    {"orientation", "mechanism"} else {"numeric_consistency"})
        for name in sorted(required_checks):
            check = checks.get(name, {})
            if check.get("status") not in {"PASSED", "NOT_APPLICABLE"} or len(str(check.get("note", "")).strip()) < 8:
                errors.append(f"visual_review.{name}: status and concrete observation required")
            if check.get("status") == "NOT_APPLICABLE" and name not in {"units", "branches", "stop_conditions"}:
                errors.append(f"visual_review.{name}: cannot be skipped")
        if review.get("blocking_findings"):
            errors.append("visual_review: blocking findings remain")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(f"visual_review: {exc}")
    return errors

def intent_digest(entry):
    return hashlib.sha256(json.dumps({k:v for k,v in entry.items() if k != "visual_review"},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def main():
    import argparse
    p = argparse.ArgumentParser(description="Validate an intent's hash-bound visual review; no automatic aesthetic scoring")
    p.add_argument("intent", type=Path)
    p.add_argument("--base-dir", type=Path)
    a = p.parse_args()
    errors = validate_review(json.loads(a.intent.read_text(encoding="utf-8")), a.base_dir or a.intent.parent)
    print(json.dumps({"status":"FAILED" if errors else "PASSED","errors":errors,
                      "semantic_claim_validation":False},ensure_ascii=False,indent=2))
    return int(bool(errors))

if __name__ == "__main__":
    raise SystemExit(main())
