from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "math-modeling-skills-complete-20260903"
WORKFLOW = PKG / "skills" / "math-modeling-orchestrator" / "scripts" / "workflow_state.py"
SUBAGENT = PKG / "skills" / "math-modeling-orchestrator" / "scripts" / "subagent_review_gate.py"
ROLES = ["semantics_math", "numerical_claims", "figure_visual", "paper_structure", "final_submission"]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def artifact_digest(rows: list[dict]) -> str:
    normalized = [{"file": row["file"], "sha256": row["sha256"].lower()} for row in rows]
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def make_manifest(root: Path, pdf: Path) -> Path:
    support = root / "support.zip"
    with zipfile.ZipFile(support, "w") as archive:
        archive.writestr("README.txt", "support")
    reviews = []
    for index, role in enumerate(ROLES, start=1):
        artifacts = [{"file": str(pdf), "sha256": digest(pdf)}]
        if role == "final_submission":
            artifacts.append({"file": str(support), "sha256": digest(support)})
        receipt = root / f"receipt-{index}.json"
        write_json(receipt, {
            "receipt_kind": "runtime_subagent_invocation",
            "status": "completed",
            "decision": "PASS",
            "agent_kind": "subagent",
            "fresh_context": True,
            "task_id": "task-A",
            "review_batch_id": "batch-A",
            "role": role,
            "agent_id": f"agent-{index}",
            "invocation_id": f"inv-{index}",
            "reviewed_artifacts_digest": artifact_digest(artifacts),
            "started_at": f"2026-09-09T00:00:0{index}+00:00",
            "completed_at": f"2026-09-09T00:01:0{index}+00:00",
        })
        reviews.append({
            "role": role,
            "agent_id": f"agent-{index}",
            "agent_kind": "subagent",
            "fresh_context": True,
            "invocation_id": f"inv-{index}",
            "decision": "PASS",
            "reviewed_artifacts": artifacts,
            "blocking_findings": [],
            "receipt": {"file": str(receipt), "sha256": digest(receipt)},
        })
    manifest = root / "SUBAGENT_REVIEW_MANIFEST.json"
    write_json(manifest, {
        "schema_version": "1.0",
        "status": "PASS",
        "task_id": "task-A",
        "review_batch_id": "batch-A",
        "reviews": reviews,
    })
    return manifest


class SubmissionAdversarialTests(unittest.TestCase):
    def test_reviewing_backward_transition_invalidates_submission_evidence(self):
        wf = load_module("workflow_submission_backward", WORKFLOW)
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "workflow_state.json"
            state = wf.initialize(
                state_path,
                "task-A",
                "competition submission",
                "training",
                "submission_package",
            )
            state["stage"] = "REVIEWING"
            state["subagent_review_status"] = "PASS"
            state["final_submission_status"] = "PASS"
            wf.write_json(state_path, state)

            moved = wf.transition(state_path, "WRITING", None, None)
            self.assertEqual(moved["subagent_review_status"], "STALE")
            self.assertEqual(moved["final_submission_status"], "STALE")

    def test_receipt_artifact_digest_mismatch_is_rejected(self):
        gate = load_module("submission_receipt_digest_adversarial", SUBAGENT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "main.pdf"
            pdf.write_bytes(b"%PDF-1.7\nfinal\n")
            manifest = make_manifest(root, pdf)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            first = payload["reviews"][0]
            receipt_path = Path(first["receipt"]["file"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["reviewed_artifacts_digest"] = "0" * 64
            write_json(receipt_path, receipt)
            first["receipt"]["sha256"] = digest(receipt_path)
            bad = root / "bad-manifest.json"
            write_json(bad, payload)

            with self.assertRaisesRegex(ValueError, "does not bind the reviewed artifact hashes"):
                gate.validate_manifest(bad)


if __name__ == "__main__":
    unittest.main()
