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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("competition_delivery_checker", CHECKER)
gate = load_module("competition_visual_gate", VISUAL_GATE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompetitionDeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="competition-delivery-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paper = self.root / "paper"
        self.paper.mkdir()
        self.pdf = self.paper / "main.pdf"
        self.pdf.write_bytes(b"%PDF-1.7\ncompetition fixture\n")
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
        snapshot = gate.source_snapshot(
            self.paper,
            {self.compile_report.resolve(), self.pdf.resolve(), self.binding.resolve()},
        )
        self.binding.write_text(json.dumps({
            "schema_version": "1.0",
            "status": "READY_FOR_VISUAL_REVIEW",
            "paper_dir": str(self.paper.resolve()),
            "compile_report": {"file": str(self.compile_report.resolve()), "sha256": digest(self.compile_report)},
            "paper_pdf": {"file": str(self.pdf.resolve()), "sha256": digest(self.pdf), "page_count": 1},
            "source_snapshot": snapshot,
            "review_artifacts": [],
        }), encoding="utf-8")

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

        self.submission_digest = checker.submission_digest(
            self.pdf, self.compile_report, self.verification, self.binding, self.support,
        )
        reviews_dir = self.paper / "reviews"
        reviews_dir.mkdir()
        summary_rows = []
        for index, dimension in enumerate(checker.REQUIRED_REVIEW_DIMENSIONS, start=1):
            review = reviews_dir / f"{dimension}.json"
            reviewer = f"fresh-subagent-{index}"
            review.write_text(json.dumps({
                "status": "PASSED",
                "dimension": dimension,
                "reviewer_id": reviewer,
                "origin": "subagent",
                "independent_of_authorship": True,
                "submission_digest": self.submission_digest,
                "invocation": {"kind": "subagent", "run_id": f"run-{index}"},
                "blocking_findings": [],
            }), encoding="utf-8")
            summary_rows.append({
                "dimension": dimension,
                "reviewer_id": reviewer,
                "report_file": str(review.relative_to(self.paper)),
                "report_sha256": digest(review),
            })
        self.summary = self.paper / "SUBAGENT_REVIEW_SUMMARY.json"
        self.summary.write_text(json.dumps({
            "status": "PASSED",
            "competition_submission": True,
            "submission_digest": self.submission_digest,
            "author_agent_id": "author-agent",
            "reviews": summary_rows,
            "unresolved_p0_p1": [],
        }), encoding="utf-8")

    def run_check(self):
        output = self.root / "FINAL_CHECK.json"
        proc = subprocess.run([
            sys.executable, str(CHECKER),
            "--paper-dir", str(self.paper),
            "--support-zip", str(self.support),
            "--competition-ready",
            "--output", str(output),
        ], capture_output=True, text=True)
        return proc, json.loads(output.read_text(encoding="utf-8"))

    def check_row(self, report, name):
        return next(row for row in report["checks"] if row["check"] == name)

    def test_placeholder_skeleton_cannot_pass_as_competition_submission(self):
        self.main_tex.write_text(
            "\\section{符号说明}\n待填写 待填写 待填写\n\\section{结论}\n[待填写：逐问回答题目]\n",
            encoding="utf-8",
        )
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(report["status"], "FAIL")
        placeholder = self.check_row(report, "no_template_or_todo_placeholders")
        self.assertFalse(placeholder["passed"])
        self.assertTrue(placeholder["hits"])
        self.assertFalse(self.check_row(report, "visual_verification_and_binding_match_current_submission")["passed"])

    def test_author_self_review_cannot_replace_subagents(self):
        review_path = self.paper / self.summary_json()["reviews"][0]["report_file"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review.update(reviewer_id="author-agent", origin="self", independent_of_authorship=False)
        review_path.write_text(json.dumps(review), encoding="utf-8")
        self._refresh_summary_hash(review_path)
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")
        self.assertFalse(row["passed"])

    def test_duplicate_dimension_and_normalized_reviewer_aliases_fail(self):
        summary = self.summary_json()
        summary["reviews"][1]["dimension"] = summary["reviews"][0]["dimension"]
        summary["reviews"][1]["reviewer_id"] = " FRESH-SUBAGENT-1 "
        self.summary.write_text(json.dumps(summary), encoding="utf-8")
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")
        self.assertFalse(row["passed"])
        self.assertTrue(row["details"]["duplicate_dimensions"])

    def test_handwritten_visual_pass_without_gate_provenance_fails(self):
        self.verification.write_text(json.dumps({
            "status": "PASSED",
            "paper_pdf": {"sha256": digest(self.pdf)},
        }), encoding="utf-8")
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "visual_verification_and_binding_match_current_submission")
        self.assertFalse(row["passed"])

    def test_stale_subagent_reviews_fail_after_support_package_changes(self):
        with zipfile.ZipFile(self.support, "a") as zf:
            zf.writestr("result/new.txt", "changed")
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")
        self.assertFalse(row["passed"])
        self.assertEqual(row["details"].get("reason"), "summary_not_passed_or_not_bound_to_current_submission")

    def test_complete_competition_package_passes_hard_gate(self):
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["verification_scope"], "competition_submission_gate")
        visual = self.check_row(report, "visual_verification_and_binding_match_current_submission")
        subagents = self.check_row(report, "four_distinct_provenance_bound_subagent_reviews_pass")
        self.assertTrue(visual["passed"])
        self.assertTrue(subagents["passed"])
        self.assertEqual(len(subagents["details"]["unique_normalized_subagent_reviewers"]), 4)

    def summary_json(self):
        return json.loads(self.summary.read_text(encoding="utf-8"))

    def _refresh_summary_hash(self, changed_review: Path):
        summary = self.summary_json()
        relative = str(changed_review.relative_to(self.paper))
        for row in summary["reviews"]:
            if row["report_file"] == relative:
                row["report_sha256"] = digest(changed_review)
        self.summary.write_text(json.dumps(summary), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
