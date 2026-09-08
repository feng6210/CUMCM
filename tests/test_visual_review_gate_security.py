"""Fail-closed edge cases for the no-recompile visual review gate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

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
    spec = importlib.util.spec_from_file_location("visual_review_gate_security_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()
PDF = b"%PDF-1.7\nmock reviewed artifact\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VisualReviewGateSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="visual-gate-security-")
        self.addCleanup(self.temporary.cleanup)
        self.paper = Path(self.temporary.name) / "paper"
        self.paper.mkdir()
        (self.paper / "main.tex").write_text("\\documentclass{mm-cumcm}\nBody\n", encoding="utf-8")
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
                    "pdf_pages": 1,
                }
            ),
            encoding="utf-8",
        )

    def prepare_args(self):
        return argparse.Namespace(
            command="prepare",
            paper_dir=self.paper,
            compile_report=Path("compile_report.json"),
            output_pdf=Path("main.pdf"),
            binding=Path("VISUAL_REVIEW_BINDING.json"),
        )

    def test_symlinked_paper_input_is_rejected_instead_of_omitted(self):
        target = self.paper / "actual-section.tex"
        target.write_text("section v1\n", encoding="utf-8")
        link = self.paper / "linked-section.tex"
        try:
            link.symlink_to(target.name)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable on this host: {exc}")
        with self.assertRaisesRegex(ValueError, "symlinked paper input"):
            gate.prepare(self.prepare_args())

    def test_verification_report_cannot_overwrite_evidence_inputs(self):
        code, _ = gate.prepare(self.prepare_args())
        self.assertEqual(code, 0)
        visual = self.paper / "PDF_VISUAL_CHECK.json"
        visual.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "paper_pdf": "main.pdf",
                    "paper_sha256": digest(PDF),
                    "page_count": 1,
                    "rendered_pages": [1],
                    "reviewed_pages": [1],
                    "reviewer_id": "reviewer",
                    "reviewer_role": "author self-review; not independent",
                }
            ),
            encoding="utf-8",
        )
        before = self.compile_report.read_bytes()
        args = argparse.Namespace(
            command="verify",
            paper_dir=self.paper,
            compile_report=Path("compile_report.json"),
            output_pdf=Path("main.pdf"),
            binding=Path("VISUAL_REVIEW_BINDING.json"),
            visual_report=visual,
            report=Path("compile_report.json"),
        )
        code, result = gate.verify(args)
        self.assertEqual(code, 2)
        self.assertEqual(result["visual_check_status"], "OUTPUT_REPORT_PATH_CONFLICT")
        self.assertEqual(self.compile_report.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
