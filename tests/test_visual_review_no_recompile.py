"""Regression for compile -> visual review -> verify without rebuilding."""
from __future__ import annotations

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
    / "compile_paper.py"
)


def load_compiler():
    spec = importlib.util.spec_from_file_location("compile_paper_visual_verify_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compiler = load_compiler()
FRESH = b"%PDF-1.7\nfresh mocked build, not a real TeX document\n"
OLD = b"%PDF-1.7\nold sentinel delivery\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VisualVerificationNoRecompileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="visual-verify-no-recompile-")
        self.addCleanup(self.temporary.cleanup)
        self.paper = Path(self.temporary.name) / "paper"
        self.paper.mkdir()
        (self.paper / "main.tex").write_text(
            "\\documentclass{mm-cumcm}\n\\mmBodyStart\nBody\n\\mmAppendixStart\n",
            encoding="utf-8",
        )
        (self.paper / "main.pdf").write_bytes(OLD)

    def fake_backend(self, paper: Path, *args):
        build = paper / "build"
        build.mkdir(exist_ok=True)
        (build / "main.pdf").write_bytes(FRESH)
        (build / "main.log").write_text("", encoding="utf-8")
        (build / "main.aux").write_text(
            "\\newlabel{mm:body-start}{{}{2}}\n\\newlabel{mm:appendix-start}{{}{3}}\n",
            encoding="utf-8",
        )
        return 0, "mock backend completed", "mock"

    def invoke(self, *args, backend=None):
        argv = ["compile_paper.py", "--paper-dir", str(self.paper), *map(str, args)]
        with (
            patch("sys.argv", argv),
            patch.object(compiler, "find_binary", side_effect=lambda name: name),
            patch.object(compiler, "run_compile", side_effect=backend or self.fake_backend),
            patch.object(compiler, "pdf_page_count", return_value=3),
            patch.object(compiler, "render_preview", return_value=[]),
        ):
            code = compiler.main()
        report = json.loads((self.paper / "compile_report.json").read_text(encoding="utf-8"))
        return code, report

    def visual_report(self) -> Path:
        path = self.paper / "PDF_VISUAL_CHECK.json"
        path.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "paper_pdf": "main.pdf",
                    "paper_sha256": digest(FRESH),
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

    def test_second_visual_verification_does_not_recompile_reviewed_pdf(self):
        code, compile_report = self.invoke()
        self.assertEqual(code, 0)
        self.assertIn("source_snapshot", compile_report)
        reviewed_hash = digest((self.paper / "main.pdf").read_bytes())
        visual = self.visual_report()

        code, report = self.invoke(
            "--visual-report",
            visual,
            backend=lambda *args: self.fail("visual verification must not invoke the compiler"),
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["verification_mode"], "existing_published_artifact_no_recompile")
        self.assertEqual(digest((self.paper / "main.pdf").read_bytes()), reviewed_hash)
        self.assertEqual(report["visual_check_status"], "PASSED_ALL_3_PAGES")

    def test_source_change_requires_recompile_instead_of_rebuilding_during_verification(self):
        self.invoke()
        visual = self.visual_report()
        main = self.paper / "main.tex"
        main.write_text(main.read_text(encoding="utf-8") + "% source changed after review\n", encoding="utf-8")

        code, report = self.invoke(
            "--visual-report",
            visual,
            backend=lambda *args: self.fail("stale visual verification must not silently recompile"),
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "VISUAL_VERIFICATION_REQUIRES_RECOMPILE")
        self.assertEqual(report["visual_check_status"], "SOURCE_SNAPSHOT_CHANGED")

    def test_published_pdf_change_requires_recompile_and_rereview(self):
        self.invoke()
        visual = self.visual_report()
        (self.paper / "main.pdf").write_bytes(FRESH + b"changed after review")

        code, report = self.invoke(
            "--visual-report",
            visual,
            backend=lambda *args: self.fail("changed reviewed PDF must not be silently regenerated"),
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "VISUAL_VERIFICATION_REQUIRES_RECOMPILE")
        self.assertEqual(report["visual_check_status"], "PUBLISHED_PDF_CHANGED")


if __name__ == "__main__":
    unittest.main()
