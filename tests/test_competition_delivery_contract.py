from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills" / "mm-paper-compile" / "scripts" / "final_delivery_check.py"
VISUAL_GATE = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills" / "mm-paper-compile" / "scripts" / "visual_review_gate.py"
WORKFLOW_STATE = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills" / "math-modeling-orchestrator" / "scripts" / "workflow_state.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("competition_delivery_checker", CHECKER)
gate = load_module("competition_visual_gate", VISUAL_GATE)
workflow = load_module("competition_workflow_state", WORKFLOW_STATE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_page_pdf() -> bytes:
    """Build a tiny structurally valid one-page PDF without a writer dependency."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(payload)


class CompetitionDeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="competition-delivery-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paper = self.root / "paper"
        self.paper.mkdir()
        self.pdf = self.paper / "main.pdf"
        self.pdf.write_bytes(one_page_pdf())
        self.main_tex = self.paper / "main.tex"
        self.main_tex.write_text(
            "\\section{问题一}\n模型、计算、结果、验证与结论均已完成。\n"
            "\\section{问题二}\n模型、优化、结果、验证与结论均已完成。\n"
            "\\section{结论}\n逐问给出最终结果与边界。\n",
            encoding="utf-8",
        )
        self.support = self.root / "support.zip"
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("code/main.py", "print('ok')\n")
            zf.writestr("results/summary.csv", "item,value\nscore,1\n")
        self._write_provenance_chain()

    def _write_provenance_chain(self):
        self.compile_report = self.paper / "compile_report.json"
        self.compile_report.write_text(json.dumps({
            "status": "COMPILED_PENDING_VISUAL_CHECK",
            "pdf_published": True,
            "pdf_path": str(self.pdf.resolve()),
            "pdf_sha256": digest(self.pdf),
        }), encoding="utf-8")
        self.binding = self.paper / "VISUAL_REVIEW_BINDING.json"
        snapshot = gate.source_snapshot(self.paper, {self.compile_report.resolve(), self.pdf.resolve(), self.binding.resolve()})
        binding_payload = {
            "schema_version": "1.0",
            "status": "READY_FOR_VISUAL_REVIEW",
            "paper_dir": str(self.paper.resolve()),
            "compile_report": {"file": str(self.compile_report.resolve()), "sha256": digest(self.compile_report)},
            "paper_pdf": {"file": str(self.pdf.resolve()), "sha256": digest(self.pdf), "page_count": 1},
            "source_snapshot": snapshot,
            "review_artifacts": [],
        }
        self.binding.write_text(json.dumps(binding_payload), encoding="utf-8")
        self.visual = self.paper / "PDF_VISUAL_CHECK.json"
        self.visual.write_text(json.dumps({
            "status": "PASSED",
            "paper_pdf": str(self.pdf.resolve()),
            "paper_sha256": digest(self.pdf),
            "page_count": 1,
            "rendered_pages": [1],
            "reviewed_pages": [1],
            "reviewer_id": "visual-reviewer",
            "reviewer_role": "fresh visual reviewer",
        }), encoding="utf-8")
        self.verification = self.paper / "visual_verification_report.json"
        self.verification.write_text(json.dumps({
            "schema_version": "1.0",
            "verification_mode": "existing_published_artifact_no_recompile",
            "status": "PASSED",
            "paper_pdf": {"file": str(self.pdf.resolve()), "sha256": digest(self.pdf), "page_count": 1},
            "compile_report": {"file": str(self.compile_report.resolve()), "sha256": digest(self.compile_report)},
            "visual_report": {"file": str(self.visual.resolve()), "sha256": digest(self.visual)},
            "source_snapshot": {"expected": snapshot["sha256"], "current": snapshot["sha256"]},
            "visual_check_status": "PASSED_ALL_1_PAGES",
        }), encoding="utf-8")
        binding_payload["review_artifacts"] = [
            {"file": str(self.visual.resolve()), "sha256": digest(self.visual), "role": "visual_report"},
            {"file": str(self.verification.resolve()), "sha256": digest(self.verification), "role": "verification_report"},
        ]
        self.binding.write_text(json.dumps(binding_payload), encoding="utf-8")
        self.reviews_dir = self.paper / "reviews"
        self.reviews_dir.mkdir()
        self.summary = self.paper / "SUBAGENT_REVIEW_SUMMARY.json"
        self._rewrite_subagents_for_current_submission()

    def _rewrite_subagents_for_current_submission(self):
        current_digest = checker.submission_digest(self.pdf, self.compile_report, self.verification, self.binding, self.support)
        summary_rows = []
        for index, dimension in enumerate(checker.REQUIRED_REVIEW_DIMENSIONS, start=1):
            review = self.reviews_dir / f"{dimension}.json"
            reviewer = f"fresh-subagent-{index}"
            review.write_text(json.dumps({
                "status": "PASSED",
                "dimension": dimension,
                "reviewer_id": reviewer,
                "origin": "subagent",
                "independent_of_authorship": True,
                "submission_digest": current_digest,
                "invocation": {"kind": "subagent", "run_id": f"run-{index}", "fresh_context": True},
                "blocking_findings": [],
            }), encoding="utf-8")
            summary_rows.append({
                "dimension": dimension,
                "reviewer_id": reviewer,
                "report_file": str(review.relative_to(self.paper)),
                "report_sha256": digest(review),
            })
        self.summary.write_text(json.dumps({
            "status": "PASSED",
            "competition_submission": True,
            "submission_digest": current_digest,
            "author_agent_id": "author-agent",
            "reviews": summary_rows,
            "unresolved_p0_p1": [],
        }), encoding="utf-8")
        self.submission_digest = current_digest

    def _refresh_visual_binding_and_subagents(self):
        verification = json.loads(self.verification.read_text(encoding="utf-8"))
        verification["visual_report"]["sha256"] = digest(self.visual)
        self.verification.write_text(json.dumps(verification), encoding="utf-8")
        binding = json.loads(self.binding.read_text(encoding="utf-8"))
        binding["review_artifacts"] = [
            {"file": str(self.visual.resolve()), "sha256": digest(self.visual), "role": "visual_report"},
            {"file": str(self.verification.resolve()), "sha256": digest(self.verification), "role": "verification_report"},
        ]
        self.binding.write_text(json.dumps(binding), encoding="utf-8")
        self._rewrite_subagents_for_current_submission()

    def run_check(self, output: Path | None = None):
        output = output or self.root / "FINAL_CHECK.json"
        proc = subprocess.run([
            sys.executable, str(CHECKER), "--paper-dir", str(self.paper), "--support-zip", str(self.support),
            "--competition-ready", "--output", str(output),
        ], capture_output=True, text=True)
        return proc, json.loads(output.read_text(encoding="utf-8")), output

    @staticmethod
    def check_row(report, name):
        return next(row for row in report["checks"] if row["check"] == name)

    def summary_json(self):
        return json.loads(self.summary.read_text(encoding="utf-8"))

    def _refresh_summary_hash(self, changed_review: Path):
        summary = self.summary_json()
        relative = str(changed_review.relative_to(self.paper))
        for row in summary["reviews"]:
            if row["report_file"] == relative:
                row["report_sha256"] = digest(changed_review)
        self.summary.write_text(json.dumps(summary), encoding="utf-8")

    def test_placeholder_skeleton_cannot_pass_as_competition_submission(self):
        self.main_tex.write_text("\\section{符号说明}\n待填写 待填写 待填写\n\\section{结论}\n结果待验证，后续补图。\n", encoding="utf-8")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "no_template_or_todo_placeholders")["passed"])

    def test_main_tex_is_mandatory(self):
        self.main_tex.unlink()
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "main_tex_required")["passed"])

    def test_support_zip_requires_meaningful_source_payload(self):
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("empty/", "")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "support_zip_nonempty")["passed"])
        self.assertFalse(self.check_row(report, "support_zip_contains_substantive_source_program")["passed"])

    def test_whitespace_source_program_is_not_substantive(self):
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("code/main.py", " \n\t\n")
            zf.writestr("results/summary.csv", "item,value\nscore,1\n")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "support_zip_contains_substantive_source_program")["passed"])

    def test_oversized_text_member_is_rejected_instead_of_skipped(self):
        oversized = "print('ok')\n" + ("# filler\n" * ((checker.MAX_INSPECTED_TEXT_BYTES // 9) + 2))
        with zipfile.ZipFile(self.support, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("code/main.py", oversized)
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "support_zip_text_fully_inspected")
        self.assertFalse(row["passed"])
        self.assertTrue(row["uninspected"])

    def test_support_zip_placeholder_text_is_rejected(self):
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("code/main.py", "# TODO: finish contest solution\nprint('draft')\n")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "support_zip_placeholder_free_text")["passed"])

    def test_support_zip_identity_tokens_are_rejected(self):
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("code/main.py", "# 姓名 张三 学号 20260001\nprint('ok')\n")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "support_zip_anonymous_and_runtime_clean")
        self.assertFalse(row["passed"])
        self.assertTrue(row["hits"])

    def test_author_self_review_cannot_replace_subagents(self):
        review_path = self.paper / self.summary_json()["reviews"][0]["report_file"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review.update(reviewer_id="author-agent", origin="self", independent_of_authorship=False)
        review_path.write_text(json.dumps(review), encoding="utf-8")
        self._refresh_summary_hash(review_path)
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")["passed"])

    def test_duplicate_dimension_and_normalized_reviewer_aliases_fail(self):
        summary = self.summary_json()
        summary["reviews"][1]["dimension"] = summary["reviews"][0]["dimension"]
        summary["reviews"][1]["reviewer_id"] = " FRESH-SUBAGENT-1 "
        self.summary.write_text(json.dumps(summary), encoding="utf-8")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")["passed"])

    def test_four_reviews_require_four_distinct_fresh_runs(self):
        summary = self.summary_json()
        for row in summary["reviews"]:
            review_path = self.paper / row["report_file"]
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["invocation"]["run_id"] = "same-run"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            row["report_sha256"] = digest(review_path)
        self.summary.write_text(json.dumps(summary), encoding="utf-8")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")["passed"])

    def test_passing_review_requires_explicit_empty_blocking_findings(self):
        review_path = self.paper / self.summary_json()["reviews"][0]["report_file"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review.pop("blocking_findings")
        review_path.write_text(json.dumps(review), encoding="utf-8")
        self._refresh_summary_hash(review_path)
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")["passed"])

    def test_handwritten_visual_pass_without_gate_provenance_fails(self):
        self.verification.write_text(json.dumps({"status": "PASSED", "paper_pdf": {"sha256": digest(self.pdf)}}), encoding="utf-8")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "visual_verification_and_binding_match_current_submission")["passed"])

    def test_visual_report_semantics_are_revalidated_not_only_hashes(self):
        visual = json.loads(self.visual.read_text(encoding="utf-8"))
        visual["status"] = "FAILED"
        self.visual.write_text(json.dumps(visual), encoding="utf-8")
        self._refresh_visual_binding_and_subagents()
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "visual_verification_and_binding_match_current_submission")
        self.assertFalse(row["passed"])
        self.assertEqual(row["details"].get("reason"), "visual_report_semantic_validation_failed")

    def test_stale_subagent_reviews_fail_after_support_package_changes(self):
        with zipfile.ZipFile(self.support, "a") as zf:
            zf.writestr("result/new.txt", "changed")
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")["passed"])

    def test_complete_competition_package_passes_hard_gate(self):
        proc, report, _ = self.run_check()
        self.assertEqual(proc.returncode, 0, json.dumps(report, ensure_ascii=False, indent=2))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(self.check_row(report, "visual_verification_and_binding_match_current_submission")["passed"])
        subagents = self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")
        self.assertTrue(subagents["passed"])
        self.assertEqual(len(subagents["details"]["unique_normalized_subagent_reviewers"]), 4)
        self.assertEqual(len(subagents["details"]["unique_normalized_subagent_runs"]), 4)
        self.assertTrue(report["competition_ready"]["subagent_evidence_digest"])

    def _reviewing_state(self) -> Path:
        state_path = self.root / "workflow_state.json"
        workflow.initialize(state_path, "competition-fixture", "full submission", "training", "submission_package")
        state = workflow.read_json(state_path)
        state["stage"] = "REVIEWING"
        state["evidence_status"] = "PASS"
        workflow.write_json(state_path, state)
        return state_path

    def test_workflow_complete_requires_recorded_current_final_gate(self):
        state_path = self._reviewing_state()
        with self.assertRaises(ValueError):
            workflow.transition(state_path, "COMPLETE", None, "PASS")
        proc, report, final_check = self.run_check()
        self.assertEqual(proc.returncode, 0, json.dumps(report, ensure_ascii=False, indent=2))
        workflow.record_final_submission_gate(state_path, final_check)
        self.assertEqual(workflow.transition(state_path, "COMPLETE", None, "PASS")["stage"], "COMPLETE")

    def test_workflow_revalidates_artifacts_after_final_gate_record(self):
        state_path = self._reviewing_state()
        proc, report, final_check = self.run_check()
        self.assertEqual(proc.returncode, 0, json.dumps(report, ensure_ascii=False, indent=2))
        workflow.record_final_submission_gate(state_path, final_check)
        with zipfile.ZipFile(self.support, "a") as zf:
            zf.writestr("results/late-change.txt", "changed after final gate\n")
        with self.assertRaises(ValueError):
            workflow.transition(state_path, "COMPLETE", None, "PASS")

    def test_workflow_rejects_changed_review_evidence_after_final_gate_record(self):
        state_path = self._reviewing_state()
        proc, report, final_check = self.run_check()
        self.assertEqual(proc.returncode, 0, json.dumps(report, ensure_ascii=False, indent=2))
        workflow.record_final_submission_gate(state_path, final_check)
        review_path = self.paper / self.summary_json()["reviews"][0]["report_file"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["diagnostic_note"] = "changed after final gate"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        self._refresh_summary_hash(review_path)
        with self.assertRaises(ValueError):
            workflow.transition(state_path, "COMPLETE", None, "PASS")


if __name__ == "__main__":
    unittest.main()
