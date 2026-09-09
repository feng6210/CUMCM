#!/usr/bin/env python3
"""Validate mandatory fresh-subagent evidence for competition submission packages."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

REQUIRED_ROLES = {
    "semantics_math",
    "numerical_claims",
    "figure_visual",
    "paper_structure",
    "final_submission",
}
ARTIFACT_KINDS = {
    "question_decomposition", "problem_semantics", "paper_pdf", "result_evidence_map",
    "figure_plan", "visual_verification", "paper_source", "support_zip",
    "submission_manifest", "compile_report",
}
REQUIRED_ARTIFACT_KINDS = {
    "semantics_math": {"question_decomposition", "problem_semantics", "paper_pdf"},
    "numerical_claims": {"paper_pdf", "result_evidence_map"},
    "figure_visual": {"paper_pdf", "figure_plan", "visual_verification"},
    "paper_structure": {"paper_pdf", "paper_source"},
    "final_submission": {"paper_pdf", "support_zip", "submission_manifest", "compile_report", "visual_verification"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def reviewed_artifacts_digest(artifacts: list[dict]) -> str:
    normalized = []
    for row in artifacts:
        if (not isinstance(row, dict) or not isinstance(row.get("kind"), str)
                or not isinstance(row.get("file"), str) or not isinstance(row.get("sha256"), str)):
            raise ValueError("invalid reviewed artifact record for digest")
        normalized.append({"kind": row["kind"], "file": row["file"], "sha256": row["sha256"].lower()})
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_timestamp(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} timestamp required")
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed


def validate_receipt(path: Path, expected: dict, *, task_id: str, review_batch_id: str,
                     role: str, agent_id: str, invocation_id: str,
                     artifacts: list[dict]) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{role}: subagent receipt missing or not a regular file")
    if sha256(path).lower() != str(expected.get("sha256", "")).lower():
        raise ValueError(f"{role}: subagent receipt hash mismatch")
    payload = load_json(path)
    if payload.get("receipt_kind") != "runtime_subagent_invocation":
        raise ValueError(f"{role}: receipt_kind must identify a runtime subagent invocation")
    if payload.get("status") != "completed" or payload.get("decision") != "PASS":
        raise ValueError(f"{role}: receipt must record a completed PASS decision")
    if payload.get("agent_kind") != "subagent" or payload.get("fresh_context") is not True:
        raise ValueError(f"{role}: receipt does not certify a fresh subagent invocation")
    if payload.get("task_id") != task_id or payload.get("review_batch_id") != review_batch_id:
        raise ValueError(f"{role}: receipt task/batch does not match manifest")
    if payload.get("role") != role or payload.get("agent_id") != agent_id or payload.get("invocation_id") != invocation_id:
        raise ValueError(f"{role}: receipt identity does not match manifest")
    if payload.get("reviewed_artifacts_digest") != reviewed_artifacts_digest(artifacts):
        raise ValueError(f"{role}: receipt does not bind the reviewed artifact hashes")
    started = parse_timestamp(payload.get("started_at"), f"{role}.started_at")
    completed = parse_timestamp(payload.get("completed_at"), f"{role}.completed_at")
    if completed < started:
        raise ValueError(f"{role}: completed_at precedes started_at")


def validate_manifest(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != "1.0" or manifest.get("status") != "PASS":
        raise ValueError("subagent manifest must be schema_version 1.0 with status PASS")
    task_id = manifest.get("task_id")
    review_batch_id = manifest.get("review_batch_id")
    if not isinstance(task_id, str) or not task_id or not isinstance(review_batch_id, str) or not review_batch_id:
        raise ValueError("subagent manifest requires task_id and review_batch_id")
    reviews = manifest.get("reviews")
    if not isinstance(reviews, list) or len(reviews) < len(REQUIRED_ROLES):
        raise ValueError("at least five role-specific subagent reviews are required")

    by_role: dict[str, dict] = {}
    agent_ids: set[str] = set()
    invocation_ids: set[str] = set()
    base = manifest_path.parent

    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("review entries must be objects")
        role = review.get("role")
        if role not in REQUIRED_ROLES:
            raise ValueError(f"unknown or non-submission review role: {role}")
        if role in by_role:
            raise ValueError(f"duplicate required review role: {role}")
        agent_id = review.get("agent_id")
        invocation_id = review.get("invocation_id")
        if not isinstance(agent_id, str) or not agent_id or not isinstance(invocation_id, str) or not invocation_id:
            raise ValueError(f"{role}: agent_id and invocation_id are required")
        if review.get("agent_kind") != "subagent" or review.get("fresh_context") is not True:
            raise ValueError(f"{role}: fresh subagent review is mandatory; self/cross-review is not accepted")
        if review.get("decision") != "PASS" or review.get("blocking_findings") != []:
            raise ValueError(f"{role}: review must PASS with no unresolved blocking findings")
        if agent_id in agent_ids:
            raise ValueError("submission roles must use distinct subagent identities")
        if invocation_id in invocation_ids:
            raise ValueError("submission roles must use distinct subagent invocations")
        agent_ids.add(agent_id); invocation_ids.add(invocation_id)

        artifacts = review.get("reviewed_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"{role}: at least one reviewed artifact is required")
        kinds: set[str] = set()
        for row in artifacts:
            if (not isinstance(row, dict) or not isinstance(row.get("kind"), str)
                    or not isinstance(row.get("file"), str)):
                raise ValueError(f"{role}: invalid reviewed artifact record")
            kind = row["kind"]
            if kind not in ARTIFACT_KINDS:
                raise ValueError(f"{role}: unknown reviewed artifact kind: {kind}")
            if kind in kinds:
                raise ValueError(f"{role}: duplicate reviewed artifact kind: {kind}")
            kinds.add(kind)
            artifact = resolve(base, row["file"])
            if not artifact.is_file() or artifact.is_symlink():
                raise ValueError(f"{role}: reviewed artifact missing: {artifact}")
            if sha256(artifact).lower() != str(row.get("sha256", "")).lower():
                raise ValueError(f"{role}: reviewed artifact hash mismatch: {artifact.name}")
        missing_kinds = REQUIRED_ARTIFACT_KINDS[role] - kinds
        if missing_kinds:
            raise ValueError(f"{role}: missing required reviewed artifact kinds: " + ", ".join(sorted(missing_kinds)))

        receipt = review.get("receipt")
        if not isinstance(receipt, dict) or not isinstance(receipt.get("file"), str):
            raise ValueError(f"{role}: hash-bound invocation receipt required")
        validate_receipt(resolve(base, receipt["file"]), receipt,
                         task_id=task_id, review_batch_id=review_batch_id, role=role,
                         agent_id=agent_id, invocation_id=invocation_id, artifacts=artifacts)
        by_role[role] = review

    missing = REQUIRED_ROLES - by_role.keys()
    if missing:
        raise ValueError("missing mandatory subagent roles: " + ", ".join(sorted(missing)))

    return {
        "schema_version": "1.0",
        "status": "PASS",
        "task_id": task_id,
        "review_batch_id": review_batch_id,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "required_roles": sorted(REQUIRED_ROLES),
        "required_artifact_kinds": {role: sorted(kinds) for role, kinds in REQUIRED_ARTIFACT_KINDS.items()},
        "distinct_subagents": len(agent_ids),
        "self_review_accepted": False,
        "same_family_cross_review_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("SUBAGENT_REVIEW_GATE.json"))
    args = parser.parse_args()
    try:
        report = validate_manifest(args.manifest); code = 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"schema_version": "1.0", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}; code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return code


if __name__ == "__main__":
    raise SystemExit(main())
