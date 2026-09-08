"""Regression for compile -> visual review -> verify without rebuilding."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "packages"
    / "math-modeling-skills-complete-20260903"
    / "skills"
    / "mm-paper-compile"
    / "scripts"
    / "visual_review_gate.py"
)


def load_gate():
    spec = importlib.util.spec_from_file_location("visual_review_gate_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()
PDF = b"%PDF-1.7\nreviewed mocked artifact\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VisualReviewNoRecompileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="visual-review-gate-")
        self.addCleanup(self.temporary.cleanup)
        self.paper = Path(self.temporary.name) / "paper"
        self.paper.mkdir()
        (self.paper / "main.tex").write_text(
            "\\documentclass{mm-cumcm}\n\\mmBodyStart\nBody\n\\mmAppendixStart\n",
            encoding="utf-8",
        )
        self.pdf = self.paper / "main.pdf"
        self.pdf.write_bytes(PDF)
        self.compile_report = self.paper / "compile_report.json"
        self.compile_report.write_text(
            json.dumps(
                {
                    "status": "COMPILED_PENDING_VISUAL_CHECK",
                    "pdf_published": True,
                    "pdf_path": str(self.pdf.resolve()),
                    "pdf_sha256": digest(PDF),
                    "pdf_pages": 3,
                }
            ),
            encoding="utf-8",
        )
        self.binding = self.paper / "VISUAL_REVIEW_BINDING.json"
        self.verify_report = self.paper / "visual_verification_report.json"

    def args(self, command: str, visual: Path | None = None):
        data = {
            "command": command,
            "paper_dir": self.paper,
            "compile_report": Path("compile_report.json"),
            "output_pdf": Path("main.pdf"),
            "binding": Path("VISUAL_REVIEW_BINDING.json"),
        }
        if command == "verify":
            data["visual_report"] = visual
            data["report"] = Path("visual_verification_report.json")
        return argparse.Namespace(**data)

    def visual_report(self) -> Path:
        path = self.paper / "PDF_VISUAL_CHECK.json"
        path.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "paper_pdf": "main.pdf",
                    "paper_sha256": digest(PDF),
                    "page_count": 3,
                    "rendered_pages": [1, 2, 3],
                    "reviewed_pages": [1, 2, 3],
                    "reviewer_id": "test-reviewer",
                    "reviewer_role": "author self-review; not independent",
                }
            ),
            encoding="utf-8",
        )
        return path

    def prepare_binding(self):
        with patch.object(gate.compile_paper, "pdf_page_count", return_value=3):
            code, binding = gate.prepare(self.args("prepare"))
        self.assertEqual(code, 0)
        self.assertEqual(binding["status"], "READY_FOR_VISUAL_REVIEW")
        self.assertTrue(self.binding.is_file())
        return binding

    def verify(self, visual: Path):
        with (
            patch.object(gate.compile_paper, "pdf_page_count", return_value=3),
            patch.object(gate.compile_paper, "run_compile", side_effect=AssertionError("must not compile")),
        ):
            return gate.verify(self.args("verify", visual))

    def test_visual_verification_uses_existing_pdf_without_compiler(self):
        self.prepare_binding()
        visual = self.visual_report()
        code, report = self.verify(visual)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["verification_mode"], "existing_published_artifact_no_recompile")
        self.assertEqual(report["visual_check_status"], "PASSED_ALL_3_PAGES")
        self.assertEqual(self.pdf.read_bytes(), PDF)
        persisted = json.loads(self.verify_report.read_text(encoding="utf-8"))
        self.assertEqual(persisted["status"], "PASSED")

    def test_source_change_requires_recompile_and_overwrites_old_pass_report(self):
        self.prepare_binding()
        visual = self.visual_report()
        code, report = self.verify(visual)
        self.assertEqual((code, report["status"]), (0, "PASSED"))
        self.assertEqual(json.loads(self.verify_report.read_text(encoding="utf-8"))["status"], "PASSED")

        main = self.paper / "main.tex"
        main.write_text(main.read_text(encoding="utf-8") + "% changed after review\n", encoding="utf-8")
        code, report = self.verify(visual)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "VISUAL_VERIFICATION_REQUIRES_RECOMPILE")
        self.assertEqual(report["visual_check_status"], "SOURCE_SNAPSHOT_CHANGED")
        persisted = json.loads(self.verify_report.read_text(encoding="utf-8"))
        self.assertEqual(persisted["status"], "VISUAL_VERIFICATION_REQUIRES_RECOMPILE")
        self.assertEqual(persisted["visual_check_status"], "SOURCE_SNAPSHOT_CHANGED")

    def test_published_pdf_change_requires_recompile_and_rereview(self):
        self.prepare_binding()
        visual = self.visual_report()
        self.pdf.write_bytes(PDF + b"changed")
        code, report = self.verify(visual)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "VISUAL_VERIFICATION_REQUIRES_RECOMPILE")
        self.assertEqual(report["visual_check_status"], "PUBLISHED_PDF_CHANGED")
        persisted = json.loads(self.verify_report.read_text(encoding="utf-8"))
        self.assertEqual(persisted["visual_check_status"], "PUBLISHED_PDF_CHANGED")

    def test_compile_report_change_invalidates_binding_and_persists_failure(self):
        self.prepare_binding()
        visual = self.visual_report()
        payload = json.loads(self.compile_report.read_text(encoding="utf-8"))
        payload["note"] = "changed after binding"
        self.compile_report.write_text(json.dumps(payload), encoding="utf-8")
        code, report = self.verify(visual)
        self.assertEqual(code, 2)
        self.assertEqual(report["visual_check_status"], "COMPILE_REPORT_CHANGED")
        persisted = json.loads(self.verify_report.read_text(encoding="utf-8"))
        self.assertEqual(persisted["visual_check_status"], "COMPILE_REPORT_CHANGED")

    def test_prepare_after_completed_cycle_excludes_prior_review_evidence(self):
        first_binding = self.prepare_binding()
        visual = self.visual_report()
        code, report = self.verify(visual)
        self.assertEqual((code, report["status"]), (0, "PASSED"))
        self.assertTrue(self.verify_report.is_file())

        # Prior review evidence is deliberately retained. A new prepare on an
        # unchanged paper must still freeze the same paper-source snapshot.
        second_binding = self.prepare_binding()
        self.assertEqual(
            first_binding["source_snapshot"]["sha256"],
            second_binding["source_snapshot"]["sha256"],
        )
        code, report = self.verify(visual)
        self.assertEqual((code, report["status"]), (0, "PASSED"))
        self.assertNotEqual(report["visual_check_status"], "SOURCE_SNAPSHOT_CHANGED")

    def test_prepare_follows_custom_visual_report_referenced_by_prior_verification(self):
        first_binding = self.prepare_binding()
        custom = self.paper / "custom-review.json"
        custom.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "paper_pdf": "main.pdf",
                    "paper_sha256": digest(PDF),
                    "page_count": 3,
                    "rendered_pages": [1, 2, 3],
                    "reviewed_pages": [1, 2, 3],
                    "reviewer_id": "custom-reviewer",
                    "reviewer_role": "author self-review; not independent",
                }
            ),
            encoding="utf-8",
        )
        args = self.args("verify", custom)
        code, report = gate.verify(args)
        self.assertEqual((code, report["status"]), (0, "PASSED"))

        second_binding = self.prepare_binding()
        self.assertEqual(
            first_binding["source_snapshot"]["sha256"],
            second_binding["source_snapshot"]["sha256"],
        )
        self.assertNotIn("custom-review.json", {row["path"] for row in second_binding["source_snapshot"]["files"]})


if __name__ == "__main__":
    unittest.main()
