"""Regression for retained nested visual-gate reports."""
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
SCRIPT = ROOT / "packages/math-modeling-skills-complete-20260903/skills/mm-paper-compile/scripts/visual_review_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("visual_review_gate_nested_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()
PDF = b"%PDF-1.7\nnested gate fixture\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class NestedVerificationReportTests(unittest.TestCase):
    def test_nested_verification_report_is_not_reclassified_as_paper_source_next_cycle(self):
        with tempfile.TemporaryDirectory(prefix="visual-gate-nested-") as tmp:
            paper = Path(tmp) / "paper"
            paper.mkdir()
            (paper / "main.tex").write_text("\\documentclass{mm-cumcm}\nBody\n", encoding="utf-8")
            pdf = paper / "main.pdf"
            pdf.write_bytes(PDF)
            (paper / "compile_report.json").write_text(
                json.dumps(
                    {
                        "status": "COMPILED_PENDING_VISUAL_CHECK",
                        "pdf_published": True,
                        "pdf_path": str(pdf.resolve()),
                        "pdf_sha256": digest(PDF),
                        "pdf_pages": 1,
                    }
                ),
                encoding="utf-8",
            )
            base = argparse.Namespace(
                paper_dir=paper,
                compile_report=Path("compile_report.json"),
                output_pdf=Path("main.pdf"),
                binding=Path("VISUAL_REVIEW_BINDING.json"),
            )
            with patch.object(gate.compile_paper, "pdf_page_count", return_value=1):
                code, first = gate.prepare(argparse.Namespace(command="prepare", **vars(base)))
            self.assertEqual(code, 0)

            visual = paper / "custom-review.json"
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
            nested = Path("evidence/gate/verification.json")
            verify_args = argparse.Namespace(
                command="verify",
                visual_report=visual,
                report=nested,
                **vars(base),
            )
            with patch.object(gate.compile_paper, "pdf_page_count", return_value=1):
                code, result = gate.verify(verify_args)
            self.assertEqual((code, result["status"]), (0, "PASSED"))
            self.assertTrue((paper / nested).is_file())

            with patch.object(gate.compile_paper, "pdf_page_count", return_value=1):
                code, second = gate.prepare(argparse.Namespace(command="prepare", **vars(base)))
            self.assertEqual(code, 0)
            self.assertEqual(first["source_snapshot"]["sha256"], second["source_snapshot"]["sha256"])
            paths = {row["path"] for row in second["source_snapshot"]["files"]}
            self.assertNotIn("evidence/gate/verification.json", paths)
            self.assertNotIn("custom-review.json", paths)


if __name__ == "__main__":
    unittest.main()
