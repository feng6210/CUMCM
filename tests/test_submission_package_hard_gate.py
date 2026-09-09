from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "math-modeling-skills-complete-20260903"
WORKFLOW = PKG / "skills" / "math-modeling-orchestrator" / "scripts" / "workflow_state.py"
SUBAGENT = PKG / "skills" / "math-modeling-orchestrator" / "scripts" / "subagent_review_gate.py"
FINAL = PKG / "skills" / "mm-paper-compile" / "scripts" / "final_submission_gate.py"
ROLES = ["semantics_math", "numerical_claims", "figure_visual", "paper_structure", "final_submission"]
HOST_READY = {"status": "PASS", "full_submission_ready": True, "missing": []}
HOST_BLOCKED = {"status": "FAIL", "full_submission_ready": False, "missing": ["xelatex"]}


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


def make_subagent_manifest(root: Path, reviewed: Path) -> Path:
    reviews = []
    for index, role in enumerate(ROLES, start=1):
        agent_id = f"fresh-subagent-{index}"
        invocation_id = f"invocation-{index}"
        receipt = root / f"receipt-{index}.json"
        write_json(receipt, {
            "status": "completed", "agent_kind": "subagent", "role": role,
            "agent_id": agent_id, "invocation_id": invocation_id,
        })
        reviews.append({
            "role": role, "agent_id": agent_id, "agent_kind": "subagent",
            "fresh_context": True, "invocation_id": invocation_id, "decision": "PASS",
            "reviewed_artifacts": [{"file": str(reviewed), "sha256": digest(reviewed)}],
            "blocking_findings": [],
            "receipt": {"file": str(receipt), "sha256": digest(receipt)},
        })
    manifest = root / "SUBAGENT_REVIEW_MANIFEST.json"
    write_json(manifest, {"schema_version": "1.0", "status": "PASS", "reviews": reviews})
    return manifest


def make_preflight(root: Path) -> Path:
    path = root / "ENVIRONMENT_PREFLIGHT.json"
    write_json(path, {
        "schema_version": "1.0", "profile": "submission_package", "status": "PASS",
        "full_submission_ready": True, "installation_performed": False,
    })
    return path


class SubmissionWorkflowStateTests(unittest.TestCase):
    def test_submission_cannot_start_or_complete_without_hard_gates(self):
        wf = load_module("submission_workflow_state", WORKFLOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "workflow_state.json"
            wf.initialize(state_path, "demo", "competition submission", "training", "submission_package")
            with self.assertRaisesRegex(ValueError, "environment preflight"):
                wf.transition(state_path, "INPUT_REGISTERED", None, None)

            with patch.object(wf, "_probe_submission_environment", return_value=HOST_READY):
                wf.record_environment_preflight(state_path, make_preflight(root))
                wf.transition(state_path, "INPUT_REGISTERED", None, None)

            state = wf.read_json(state_path)
            state["stage"] = "REVIEWING"
            state["evidence_status"] = "PASS"
            state["result_to_claim_status"] = "YES"
            wf.write_json(state_path, state)
            with patch.object(wf, "_probe_submission_environment", return_value=HOST_READY):
                with self.assertRaisesRegex(ValueError, "subagent"):
                    wf.transition(state_path, "COMPLETE", None, None)

            final_pdf = root / "main.pdf"; final_pdf.write_bytes(b"%PDF-1.7\nsubmission bytes\n")
            support = root / "support.zip"
            with zipfile.ZipFile(support, "w") as archive:
                archive.writestr("README.txt", "support")
            manifest = make_subagent_manifest(root, final_pdf)
            wf.record_subagent_review(state_path, manifest)

            dummy = root / "dummy.json"; write_json(dummy, {"ok": True})
            final_gate = root / "FINAL_SUBMISSION_GATE.json"
            gate_payload = {
                "schema_version": "1.0", "status": "PASS", "competition_ready": True,
                "paper_dir": str(root), "workflow_state": str(state_path),
                "submission_manifest": str(dummy), "subagent_manifest": str(manifest),
                "compile_report": str(dummy), "visual_verification_report": str(dummy),
                "support_zip": str(support),
                "paper_pdf": str(final_pdf), "paper_pdf_sha256": digest(final_pdf),
                "support_zip_sha256": digest(support),
                "submission_manifest_sha256": digest(dummy), "subagent_manifest_sha256": digest(manifest),
                "compile_report_sha256": digest(dummy), "visual_verification_report_sha256": digest(dummy),
                "question_decomposition_sha256": digest(dummy),
            }
            write_json(final_gate, gate_payload)
            with patch.object(wf, "_probe_submission_environment", return_value=HOST_READY), \
                 patch.object(wf, "_recompute_final_submission", return_value=dict(gate_payload)):
                wf.record_final_submission(state_path, final_gate)
                completed = wf.transition(state_path, "COMPLETE", None, None)
            self.assertEqual(completed["stage"], "COMPLETE")

    def test_fake_pass_preflight_does_not_override_current_host(self):
        wf = load_module("submission_workflow_host_probe", WORKFLOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state = root / "workflow_state.json"
            wf.initialize(state, "demo", "competition submission", "training", "submission_package")
            with patch.object(wf, "_probe_submission_environment", return_value=HOST_BLOCKED):
                with self.assertRaisesRegex(ValueError, "current host"):
                    wf.record_environment_preflight(state, make_preflight(root))

    def test_fake_final_gate_label_is_not_accepted_without_revalidation_paths(self):
        wf = load_module("submission_workflow_fake_final", WORKFLOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state_path = root / "workflow_state.json"
            state = wf.initialize(state_path, "demo", "competition submission", "training", "submission_package")
            state["evidence_status"] = "PASS"; state["result_to_claim_status"] = "YES"
            wf.write_json(state_path, state)
            fake = root / "FINAL_SUBMISSION_GATE.json"
            write_json(fake, {"status": "PASS", "competition_ready": True})
            with patch.object(wf, "_probe_submission_environment", return_value=HOST_READY):
                with self.assertRaisesRegex(ValueError, "revalidation paths"):
                    wf.record_final_submission(state_path, fake)

    def test_submission_review_or_delivery_change_invalidates_final_evidence(self):
        wf = load_module("submission_workflow_stale", WORKFLOW)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state_path = root / "workflow_state.json"
            state = wf.initialize(state_path, "demo", "competition submission", "training", "submission_package")
            state["subagent_review_status"] = "PASS"; state["final_submission_status"] = "PASS"
            wf.write_json(state_path, state)
            stale = wf.mark_stale(state_path, ["paper/main.tex"], "paper changed")
            self.assertEqual(stale["subagent_review_status"], "STALE")
            self.assertEqual(stale["final_submission_status"], "STALE")


class SubagentReviewGateTests(unittest.TestCase):
    def test_requires_five_distinct_fresh_subagents(self):
        gate = load_module("submission_subagent_gate_test", SUBAGENT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = root / "main.pdf"; pdf.write_bytes(b"%PDF-1.7\nfinal\n")
            manifest = make_subagent_manifest(root, pdf)
            report = gate.validate_manifest(manifest)
            self.assertEqual(report["status"], "PASS"); self.assertEqual(report["distinct_subagents"], 5)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["reviews"][1]["agent_id"] = payload["reviews"][0]["agent_id"]
            bad = root / "bad.json"; write_json(bad, payload)
            with self.assertRaisesRegex(ValueError, "distinct subagent"):
                gate.validate_manifest(bad)

    def test_self_review_or_nonfresh_review_is_rejected(self):
        gate = load_module("submission_subagent_gate_nonfresh", SUBAGENT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = root / "main.pdf"; pdf.write_bytes(b"%PDF-1.7\nfinal\n")
            manifest = make_subagent_manifest(root, pdf)
            payload = json.loads(manifest.read_text(encoding="utf-8")); payload["reviews"][0]["fresh_context"] = False
            bad = root / "bad.json"; write_json(bad, payload)
            with self.assertRaisesRegex(ValueError, "fresh subagent"):
                gate.validate_manifest(bad)


class FinalSubmissionGateTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        paper = root / "paper"; paper.mkdir()
        tex = paper / "main.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\n完整答案\\label{sec:q1}\n\\end{document}\n", encoding="utf-8")
        pdf = paper / "main.pdf"; pdf.write_bytes(b"%PDF-1.7\nfinal submission\n")
        support = root / "support.zip"
        with zipfile.ZipFile(support, "w") as archive:
            archive.writestr("code/model.py", "print('ok')")
        result = root / "q1-result.json"; write_json(result, {"value": 1})
        validation = root / "q1-validation.json"; write_json(validation, {"status": "PASS"})
        decomposition = root / "QUESTION_DECOMPOSITION.json"
        write_json(decomposition, {"expected_question_ids": ["Q1"], "questions": [{"question_id": "Q1"}]})
        state = root / "workflow_state.json"
        write_json(state, {"deliverable_mode": "submission_package", "evidence_status": "PASS",
                           "result_to_claim_status": "YES", "problem_parts": ["Q1"]})
        submission = root / "FINAL_SUBMISSION_MANIFEST.json"
        write_json(submission, {
            "schema_version": "1.0", "status": "READY", "deliverable_mode": "submission_package",
            "question_decomposition": {"file": str(decomposition), "sha256": digest(decomposition)},
            "expected_question_ids_field": "expected_question_ids",
            "paper_pdf": {"file": str(pdf), "sha256": digest(pdf)},
            "support_zip": {"file": str(support), "sha256": digest(support)},
            "question_completion": [{
                "question_id": "Q1", "status": "PASS", "paper_label": "sec:q1",
                "result_artifacts": [{"file": str(result), "sha256": digest(result)}],
                "validation_artifacts": [{"file": str(validation), "sha256": digest(validation)}],
            }],
        })
        compile_report = paper / "compile_report.json"
        write_json(compile_report, {"status": "COMPILED_PENDING_VISUAL_CHECK", "pdf_published": True,
                                    "pdf_sha256": digest(pdf)})
        visual = paper / "visual_verification_report.json"
        write_json(visual, {
            "status": "PASSED", "verification_mode": "existing_published_artifact_no_recompile",
            "paper_pdf": {"file": str(pdf), "sha256": digest(pdf), "page_count": 2},
            "compile_report": {"file": str(compile_report), "sha256": digest(compile_report)},
        })
        subagents = make_subagent_manifest(root, pdf)
        return paper, tex, pdf, support, state, submission, subagents, compile_report, visual, decomposition

    def test_complete_fixture_passes_and_placeholder_fails(self):
        gate = load_module("final_submission_gate_test", FINAL)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper, tex, pdf, support, state, submission, subagents, compile_report, visual, _ = self.make_fixture(root)
            with patch.object(gate, "pdf_text_and_pages", return_value=("完整答案", 2)):
                report = gate.check_submission(paper, state, submission, subagents, compile_report, visual, support)
            self.assertEqual(report["status"], "PASS"); self.assertTrue(report["competition_ready"])
            self.assertEqual(report["support_zip_sha256"], digest(support)); self.assertEqual(report["paper_dir"], str(paper.resolve()))

            tex.write_text("\\documentclass{article}\n\\begin{document}\n待填写\\label{sec:q1}\n\\end{document}\n", encoding="utf-8")
            with patch.object(gate, "pdf_text_and_pages", return_value=("完整答案", 2)):
                failed = gate.check_submission(paper, state, submission, subagents, compile_report, visual, support)
            self.assertEqual(failed["status"], "FAIL"); self.assertFalse(failed["competition_ready"])

    def test_truncated_workflow_question_list_cannot_hide_decomposition_question(self):
        gate = load_module("final_submission_gate_questions", FINAL)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper, _, _, support, state, submission, subagents, compile_report, visual, decomposition = self.make_fixture(root)
            write_json(decomposition, {"expected_question_ids": ["Q1", "Q2"],
                                       "questions": [{"question_id": "Q1"}, {"question_id": "Q2"}]})
            payload = json.loads(submission.read_text(encoding="utf-8"))
            payload["question_decomposition"]["sha256"] = digest(decomposition)
            write_json(submission, payload)
            with patch.object(gate, "pdf_text_and_pages", return_value=("完整答案", 2)):
                failed = gate.check_submission(paper, state, submission, subagents, compile_report, visual, support)
            self.assertEqual(failed["status"], "FAIL")
            relevant = [row for row in failed["checks"] if row["check"] == "workflow_problem_parts_match_decomposition"]
            self.assertEqual(len(relevant), 1); self.assertFalse(relevant[0]["passed"])

    def test_visual_report_must_bind_the_current_compile_report(self):
        gate = load_module("final_submission_gate_visual_compile", FINAL)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper, _, _, support, state, submission, subagents, compile_report, visual, _ = self.make_fixture(root)
            payload = json.loads(visual.read_text(encoding="utf-8")); payload["compile_report"]["sha256"] = "0" * 64
            write_json(visual, payload)
            with patch.object(gate, "pdf_text_and_pages", return_value=("完整答案", 2)):
                failed = gate.check_submission(paper, state, submission, subagents, compile_report, visual, support)
            self.assertEqual(failed["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
