from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills" / "mm-paper-compile" / "scripts" / "final_delivery_check.py"


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
        self.support = self.root / "support.zip"
        with zipfile.ZipFile(self.support, "w") as zf:
            zf.writestr("code/main.py", "print('ok')\n")
        self._write_reports()

    def _write_reports(self):
        pdf_hash = digest(self.pdf)
        (self.paper / "compile_report.json").write_text(json.dumps({
            "status": "COMPILED_PENDING_VISUAL_CHECK",
            "pdf_published": True,
            "pdf_sha256": pdf_hash,
        }), encoding="utf-8")
        (self.paper / "visual_verification_report.json").write_text(json.dumps({
            "status": "PASSED",
            "paper_pdf": {"sha256": pdf_hash},
        }), encoding="utf-8")
        reviews = []
        for index, dimension in enumerate(("semantics_math", "numbers_claims", "figures_evidence", "paper_delivery"), start=1):
            reviews.append({
                "dimension": dimension,
                "reviewer_id": f"fresh-subagent-{index}",
                "origin": "subagent",
                "independent_of_authorship": True,
                "status": "PASSED",
                "blocking_findings": [],
            })
        (self.paper / "SUBAGENT_REVIEW_SUMMARY.json").write_text(json.dumps({
            "status": "PASSED",
            "competition_submission": True,
            "author_agent_id": "author-agent",
            "reviews": reviews,
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

    def test_placeholder_skeleton_cannot_pass_as_competition_submission(self):
        (self.paper / "main.tex").write_text(
            "\\section{符号说明}\n待填写 待填写 待填写\n\\section{结论}\n[待填写：逐问回答题目]\n",
            encoding="utf-8",
        )
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(report["status"], "FAIL")
        placeholder = next(row for row in report["checks"] if row["check"] == "no_template_or_todo_placeholders")
        self.assertFalse(placeholder["passed"])
        self.assertTrue(placeholder["hits"])

    def test_author_self_review_or_reused_reviewer_cannot_replace_subagents(self):
        (self.paper / "main.tex").write_text("\\section{结论}\n四问均已闭合。\n", encoding="utf-8")
        summary = json.loads((self.paper / "SUBAGENT_REVIEW_SUMMARY.json").read_text(encoding="utf-8"))
        for row in summary["reviews"]:
            row["reviewer_id"] = "author-agent"
            row["origin"] = "self"
            row["independent_of_authorship"] = False
        (self.paper / "SUBAGENT_REVIEW_SUMMARY.json").write_text(json.dumps(summary), encoding="utf-8")
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 2)
        row = next(row for row in report["checks"] if row["check"] == "four_distinct_subagent_reviews_pass")
        self.assertFalse(row["passed"])

    def test_complete_competition_package_passes_hard_gate(self):
        (self.paper / "main.tex").write_text(
            "\\section{问题一}\n模型、计算、结果、验证与结论均已完成。\n"
            "\\section{问题二}\n模型、优化、结果、验证与结论均已完成。\n"
            "\\section{结论}\n逐问给出最终结果与边界。\n",
            encoding="utf-8",
        )
        proc, report = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["verification_scope"], "competition_submission_gate")
        row = next(row for row in report["checks"] if row["check"] == "four_distinct_subagent_reviews_pass")
        self.assertTrue(row["passed"])
        self.assertEqual(len(row["details"]["unique_subagent_reviewers"]), 4)


if __name__ == "__main__":
    unittest.main()
