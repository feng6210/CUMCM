"""Fail-closed edge cases for the no-recompile visual review gate."""
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

    def prepare_args(self, binding: str = "VISUAL_REVIEW_BINDING.json"):
        return argparse.Namespace(
            command="prepare",
            paper_dir=self.paper,
            compile_report=Path("compile_report.json"),
            output_pdf=Path("main.pdf"),
            binding=Path(binding),
        )

    def verify_args(self, visual: Path, report: Path | str = "visual_verification_report.json"):
        return argparse.Namespace(
            command="verify",
            paper_dir=self.paper,
            compile_report=Path("compile_report.json"),
            output_pdf=Path("main.pdf"),
            binding=Path("VISUAL_REVIEW_BINDING.json"),
            visual_report=visual,
            report=Path(report),
        )

    def write_visual(self, path: Path | None = None, **extra) -> Path:
        path = path or (self.paper / "PDF_VISUAL_CHECK.json")
        payload = {
            "status": "PASSED",
            "paper_pdf": "main.pdf",
            "paper_sha256": digest(PDF),
            "page_count": 1,
            "rendered_pages": [1],
            "reviewed_pages": [1],
            "reviewer_id": "reviewer",
            "reviewer_role": "author self-review; not independent",
        }
        payload.update(extra)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

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

    def test_symlink_to_excluded_gate_artifact_is_still_rejected(self):
        gate_artifact = self.paper / "visual_verification_report.json"
        gate_artifact.write_text(
            json.dumps({"verification_mode": gate.VERIFICATION_MODE, "status": "PASSED"}),
            encoding="utf-8",
        )
        link = self.paper / "linked-section.tex"
        try:
            link.symlink_to(gate_artifact.name)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable on this host: {exc}")
        with self.assertRaisesRegex(ValueError, "symlinked paper input"):
            gate.prepare(self.prepare_args())

    def test_binding_cannot_overwrite_existing_json_paper_input(self):
        model = self.paper / "model.json"
        model.write_text(json.dumps({"paper_input": True}), encoding="utf-8")
        before = model.read_bytes()
        with self.assertRaisesRegex(ValueError, "collides with an existing non-binding"):
            gate.prepare(self.prepare_args("model.json"))
        self.assertEqual(model.read_bytes(), before)

    def test_binding_rejects_non_json_destination_without_overwrite(self):
        main = self.paper / "main.tex"
        before = main.read_bytes()
        with self.assertRaisesRegex(ValueError, "must be a .json"):
            gate.prepare(self.prepare_args("main.tex"))
        self.assertEqual(main.read_bytes(), before)

    def test_verification_report_cannot_overwrite_primary_evidence_inputs(self):
        code, _ = gate.prepare(self.prepare_args())
        self.assertEqual(code, 0)
        visual = self.write_visual()
        before = self.compile_report.read_bytes()
        code, result = gate.verify(self.verify_args(visual, "compile_report.json"))
        self.assertEqual(code, 2)
        self.assertEqual(result["visual_check_status"], "OUTPUT_REPORT_PATH_CONFLICT")
        self.assertEqual(self.compile_report.read_bytes(), before)

    def test_verification_report_cannot_overwrite_bound_paper_source(self):
        code, _ = gate.prepare(self.prepare_args())
        self.assertEqual(code, 0)
        visual = self.write_visual()
        main = self.paper / "main.tex"
        before = main.read_bytes()
        code, result = gate.verify(self.verify_args(visual, "main.tex"))
        self.assertEqual(code, 2)
        self.assertEqual(result["visual_check_status"], "OUTPUT_REPORT_PATH_CONFLICT")
        self.assertEqual(main.read_bytes(), before)

    def test_review_page_reference_cannot_hide_an_existing_paper_png(self):
        figure = self.paper / "figure.png"
        figure.write_bytes(b"paper figure v1")
        visual = self.write_visual(
            page_images=[{"page": 1, "file": "figure.png", "sha256": digest(figure.read_bytes())}]
        )
        code, binding = gate.prepare(self.prepare_args())
        self.assertEqual(code, 0)
        self.assertIn("figure.png", {row["path"] for row in binding["source_snapshot"]["files"]})

        figure.write_bytes(b"paper figure v2")
        # Even if the review JSON is rewritten to carry the new exact hash, the
        # bound source identity prevents the paper figure from becoming an exclusion.
        payload = json.loads(visual.read_text(encoding="utf-8"))
        payload["page_images"][0]["sha256"] = digest(figure.read_bytes())
        visual.write_text(json.dumps(payload), encoding="utf-8")
        code, result = gate.verify(self.verify_args(visual))
        self.assertEqual(code, 2)
        self.assertEqual(result["visual_check_status"], "SOURCE_SNAPSHOT_CHANGED")

    def test_verification_report_cannot_overwrite_inherited_review_json(self):
        code, _ = gate.prepare(self.prepare_args())
        self.assertEqual(code, 0)
        prior = self.write_visual(self.paper / "prior-review.json")
        visual = self.write_visual(
            previous_report={"file": "prior-review.json", "sha256": digest(prior.read_bytes())}
        )
        prior_before = prior.read_bytes()
        code, result = gate.verify(self.verify_args(visual, "prior-review.json"))
        self.assertEqual(code, 2)
        self.assertEqual(result["visual_check_status"], "OUTPUT_REPORT_PATH_CONFLICT")
        self.assertEqual(prior.read_bytes(), prior_before)


if __name__ == "__main__":
    unittest.main()
