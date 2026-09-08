"""Output publication and visual-review regressions; no TeX install required."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "packages/math-modeling-skills-complete-20260903/skills/mm-paper-compile/scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compiler = load_script("compile_paper")
delivery = load_script("final_delivery_check")
FRESH = b"%PDF-1.7\nfresh mocked build, not a real TeX document\n"
OLD = b"%PDF-1.7\nold sentinel delivery\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class CompilePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="paper-compile-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.paper = Path(self.temporary.name) / "paper"
        self.paper.mkdir()
        (self.paper / "main.tex").write_text(
            "\\documentclass{mm-cumcm}\n\\mmBodyStart\nBody\n\\mmAppendixStart\n",
            encoding="utf-8",
        )
        self.old = self.paper / "main.pdf"
        self.old.write_bytes(OLD)

    def fake_backend(self, paper, *args):
        build = paper / "build"
        build.mkdir(exist_ok=True)
        (build / "main.pdf").write_bytes(FRESH)
        (build / "main.log").write_text("Underfull \\hbox (badness 10000)\n", encoding="utf-8")
        (build / "main.aux").write_text(
            "\\newlabel{mm:body-start}{{}{2}}\n\\newlabel{mm:appendix-start}{{}{3}}\n",
            encoding="utf-8",
        )
        return 0, "mock backend completed", "mock"

    def invoke(self, *args, backend=None):
        argv = ["compile_paper.py", "--paper-dir", str(self.paper), *map(str, args)]
        with patch("sys.argv", argv), patch.object(compiler, "find_binary", side_effect=lambda name: name), \
             patch.object(compiler, "run_compile", side_effect=backend or self.fake_backend), \
             patch.object(compiler, "pdf_page_count", return_value=3), \
             patch.object(compiler, "render_preview", return_value=[]):
            code = compiler.main()
        return code, json.loads((self.paper / "compile_report.json").read_text(encoding="utf-8"))

    def full_visual(self, name="visual.json", **updates):
        data = {
            "status": "PASSED", "paper_sha256": digest(FRESH), "page_count": 3,
            "rendered_pages": [1, 2, 3], "reviewed_pages": [1, 2, 3],
            "reviewer_id": "test-reviewer", "reviewer_role": "author self-review; not independent",
        }
        data.update(updates)
        path = self.paper / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_default_publishes_only_fresh_build_and_discloses_layout(self):
        code, report = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(self.old.read_bytes(), FRESH)
        self.assertEqual(report["pdf_path"], str(self.old.resolve()))
        self.assertEqual(report["pdf_sha256"], digest(FRESH))
        self.assertEqual(report["source_pdf_sha256"], report["pdf_sha256"])
        self.assertEqual(Path(report["source_pdf_path"]).read_bytes(), FRESH)
        self.assertTrue(report["pdf_published"])
        self.assertEqual(report["status"], "COMPILED_PENDING_VISUAL_CHECK")
        self.assertEqual((report["pdf_pages"], report["body_pages"], report["appendix_pages"]), (3, 1, 1))
        self.assertEqual(report["log_checks"]["underfull_boxes"], 1)
        self.assertTrue(report["layout_notes"])

    def test_explicit_relative_save_as_leaves_old_default(self):
        code, report = self.invoke("--output-pdf", "revised.pdf")
        self.assertEqual(code, 0)
        self.assertEqual(self.old.read_bytes(), OLD)
        self.assertEqual((self.paper / "revised.pdf").read_bytes(), FRESH)
        self.assertEqual(report["pdf_path"], str((self.paper / "revised.pdf").resolve()))
        self.assertTrue(report["output_pdf_explicit"])

    def test_explicit_absolute_save_as(self):
        output = Path(self.temporary.name) / "external.pdf"
        code, report = self.invoke("--output-pdf", output)
        self.assertEqual(code, 0)
        self.assertEqual(output.read_bytes(), FRESH)
        self.assertEqual(report["pdf_path"], str(output.resolve()))

    def test_invalid_output_paths_fail_without_compiling(self):
        (self.paper / "directory.pdf").mkdir()
        (self.paper / "build").mkdir()
        for selected in ("wrong.txt", "directory.pdf", "missing/another.pdf", "build/final.pdf"):
            with self.subTest(selected=selected):
                code, report = self.invoke("--output-pdf", selected,
                                           backend=lambda *args: self.fail("invalid output compiled"))
                self.assertEqual(code, 2)
                self.assertEqual(report["status"], "OUTPUT_PATH_INVALID")
                self.assertEqual(self.old.read_bytes(), OLD)

    def test_no_fresh_build_cannot_reuse_old_delivery_or_old_build(self):
        build = self.paper / "build"
        build.mkdir()
        (build / "main.pdf").write_bytes(OLD)
        code, report = self.invoke(backend=lambda *args: (0, "nothing generated", "mock"))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "PDF_MISSING")
        self.assertEqual(self.old.read_bytes(), OLD)
        self.assertFalse(report["pdf_published"])
        self.assertNotIn("pdf_sha256", report)
        self.assertEqual(Path(report["previous_build_pdf"]["path"]).read_bytes(), OLD)

    def test_same_bytes_are_valid_when_actually_regenerated(self):
        self.old.write_bytes(FRESH)
        (self.paper / "build").mkdir()
        (self.paper / "build/main.pdf").write_bytes(FRESH)
        code, report = self.invoke()
        self.assertEqual(code, 0)
        self.assertTrue(report["pdf_published"])
        self.assertEqual(report["previous_build_pdf"]["sha256"], report["pdf_sha256"])

    def test_copy_and_replace_permission_failures_keep_old_bytes(self):
        for object_, name in ((compiler.shutil, "copy2"), (compiler.os, "replace")):
            with self.subTest(name=name), patch.object(object_, name, side_effect=PermissionError("locked test file")):
                code, report = self.invoke()
            self.assertEqual(code, 2)
            self.assertEqual(report["status"], "PDF_PUBLISH_FAILED")
            self.assertEqual(report["error_type"], "PermissionError")
            self.assertFalse(report["pdf_published"])
            self.assertNotIn("pdf_sha256", report)
            self.assertIn("--output-pdf", report["recovery"])
            self.assertEqual(self.old.read_bytes(), OLD)
            self.assertEqual((self.paper / "build/main.pdf").read_bytes(), FRESH)
            self.assertEqual(list(self.paper.glob("*.pdf")), [self.old])
            self.assertEqual(list(self.paper.glob("*.tmp")), [])

    def test_explicit_save_as_succeeds_while_default_is_locked(self):
        real_replace = compiler.os.replace

        def lock_default(source, destination):
            if Path(destination) == self.old:
                raise PermissionError("default PDF open in viewer")
            return real_replace(source, destination)

        with patch.object(compiler.os, "replace", side_effect=lock_default):
            code, report = self.invoke("--output-pdf", "user-chosen.pdf")
        self.assertEqual(code, 0)
        self.assertTrue(report["pdf_published"])
        self.assertEqual(self.old.read_bytes(), OLD)

    def test_compile_failure_keeps_old_delivery(self):
        code, report = self.invoke(backend=lambda *args: (1, "failed compiler", "mock"))
        self.assertEqual((code, report["status"]), (2, "COMPILE_FAILED"))
        self.assertEqual(self.old.read_bytes(), OLD)
        self.assertFalse(report["pdf_published"])

    def test_nocite_alone_still_requests_current_bibtex(self):
        main = self.paper / "main.tex"
        main.write_text(main.read_text(encoding="utf-8") + "\\nocite{*}\n", encoding="utf-8")

        def check_mode(paper, latexmk, xelatex, bibtex, no_citations):
            self.assertFalse(no_citations)
            return self.fake_backend(paper)

        code, report = self.invoke(backend=check_mode)
        self.assertEqual(code, 0)
        self.assertEqual(report["bibliography_mode"], "bibtex_required")

    def test_invalid_fresh_pdf_is_not_published(self):
        def broken(paper, *args):
            self.fake_backend(paper)
            (paper / "build/main.pdf").write_bytes(b"not a PDF")
            return 0, "bad artifact", "mock"
        code, report = self.invoke(backend=broken)
        self.assertEqual((code, report["status"]), (2, "PDF_INVALID"))
        self.assertEqual(self.old.read_bytes(), OLD)

    def test_stale_visual_hash_is_rejected_against_actual_new_output(self):
        visual = self.full_visual(paper_sha256=digest(OLD))
        code, report = self.invoke("--output-pdf", "new.pdf", "--visual-report", visual)
        self.assertEqual((code, report["status"]), (2, "VISUAL_CHECK_FAILED"))
        self.assertEqual(report["visual_check_status"], "VISUAL_REPORT_STALE_OR_FAILED")
        self.assertEqual(report["pdf_sha256"], digest(FRESH))
        self.assertEqual(self.old.read_bytes(), OLD)

    def test_legacy_visual_is_compatible_but_requires_review(self):
        visual = self.paper / "legacy.json"
        visual.write_text(json.dumps({"status": "PASSED", "paper_sha256": digest(FRESH)}), encoding="utf-8")
        original = visual.read_bytes()
        code, report = self.invoke("--visual-report", visual)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "COMPILED_PENDING_VISUAL_CHECK")
        self.assertEqual(report["visual_check_status"], "REVIEW_REQUIRED")
        self.assertIn("reviewed_pages", report["visual_check_details"]["missing_fields"])
        self.assertEqual(visual.read_bytes(), original)

    def test_current_complete_visual_pass_does_not_certify_independence(self):
        visual = self.full_visual(paper_pdf="new.pdf")
        code, report = self.invoke("--output-pdf", "new.pdf", "--visual-report", visual)
        self.assertEqual((code, report["status"]), (0, "PASSED"))
        self.assertFalse(report["visual_check_details"]["independence_certified"])
        self.assertEqual(report["visual_report_sha256"], compiler.sha256(visual))

    def test_wrong_visual_scope_or_output_is_rejected(self):
        cases = (
            ({"page_count": 2}, "VISUAL_REPORT_PAGE_COUNT_MISMATCH"),
            ({"reviewed_pages": [1, 2]}, "VISUAL_REPORT_COVERAGE_INCOMPLETE"),
            ({"rendered_pages": [1, 2, 2, 3]}, "VISUAL_REPORT_COVERAGE_INCOMPLETE"),
            ({"reviewed_pages": [True, 2, 3]}, "VISUAL_REPORT_COVERAGE_INCOMPLETE"),
            ({"paper_pdf": "unrelated.pdf"}, "VISUAL_REPORT_OUTPUT_PATH_MISMATCH"),
        )
        for updates, expected in cases:
            with self.subTest(updates=updates):
                code, report = self.invoke("--visual-report", self.full_visual(**updates))
                self.assertEqual(code, 2)
                self.assertEqual(report["visual_check_status"], expected)

    def test_missing_actual_page_count_cannot_pass_visual(self):
        self.old.write_bytes(FRESH)
        result = compiler.check_visual_report(self.full_visual(), self.old, None)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_hash_bound_preserved_page_images_allow_explicit_inheritance(self):
        # A deterministic PNG receipt exercises byte-identity binding, not a
        # simulated claim that a human has visually reviewed this fixture.
        png = self.paper / "page-3.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\nmock image bytes")
        images = [{"page": 3, "file": png.name, "sha256": compiler.sha256(png)}]
        previous = self.full_visual("prior-review.json", paper_sha256=digest(OLD), page_images=images)
        previous_bytes = previous.read_bytes()
        visual = self.full_visual(inherited_pages=[3], page_images=images,
                                  previous_report={"file": previous.name, "sha256": compiler.sha256(previous)})
        code, report = self.invoke("--visual-report", visual)
        self.assertEqual((code, report["status"]), (0, "PASSED"))
        self.assertEqual(report["visual_check_details"]["inherited_pages"], [3])
        self.assertEqual(previous.read_bytes(), previous_bytes)
        png.write_bytes(png.read_bytes() + b"changed pixels")
        code, report = self.invoke("--visual-report", visual)
        self.assertEqual((code, report["status"]), (2, "VISUAL_CHECK_FAILED"))
        self.assertEqual(report["visual_check_status"], "VISUAL_REPORT_INVALID")

    def test_inheritance_without_separate_preserved_report_is_rejected(self):
        visual = self.full_visual(inherited_pages=[3])
        code, report = self.invoke("--visual-report", visual)
        self.assertEqual((code, report["status"]), (2, "VISUAL_CHECK_FAILED"))

    def test_latexmk_uses_build_output_directory(self):
        with patch.object(compiler, "_run", return_value=(0, "mock")) as runner:
            code, _, route = compiler.run_compile(self.paper, "latexmk", "xelatex", "bibtex", True)
        self.assertEqual((code, route), (0, "latexmk"))
        self.assertIn("-outdir=build", runner.call_args.args[0])

    def test_preview_requests_all_pages_not_only_first_three(self):
        prefix = self.paper / "preview"

        def render(command, **kwargs):
            self.assertNotIn("-f", command)
            self.assertNotIn("-l", command)
            for page in range(1, 5):
                prefix.with_name(f"preview-{page}.png").write_bytes(b"image")
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(compiler, "find_binary", return_value="pdftoppm"), \
             patch.object(compiler.subprocess, "run", side_effect=render):
            images = compiler.render_preview(self.old, prefix)
        self.assertEqual(len(images), 4)

    def test_delivery_checker_targets_explicit_pdf_and_claims_only_container_scope(self):
        chosen = self.paper / "chosen.pdf"
        chosen.write_bytes(FRESH)
        report_path = self.paper / "delivery.json"
        with patch("sys.argv", ["final_delivery_check.py", "--paper-dir", str(self.paper),
                                "--output-pdf", "chosen.pdf", "--output", str(report_path)]):
            code = delivery.main()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(report["pdf_sha256"], digest(FRESH))
        self.assertEqual(report["pdf_path"], str(chosen.resolve()))
        self.assertEqual(report["verification_scope"], "structural_delivery_checks_only")
        self.assertFalse(report["source_package_recompiled"])
        self.assertFalse(report["experiment_reproduced"])


class ManualBibtexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="manual-bibtex-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.paper = Path(self.temporary.name)
        self.build = self.paper / "build"
        self.build.mkdir()
        self.bbl = self.build / "main.bbl"
        self.blg = self.build / "main.blg"
        self.old_bbl = self.bibliography({"a": "OLD TITLE"})
        self.bbl.write_text(self.old_bbl, encoding="utf-8")
        self.blg.write_text("old diagnostic sentinel", encoding="utf-8")
        self.calls = []

    @staticmethod
    def bibliography(entries):
        return ("\\begin{thebibliography}{9}\n"
                + "\n".join(f"\\bibitem{{{key}}} {title}" for key, title in entries.items())
                + "\n\\end{thebibliography}\n")

    def run_case(self, fresh, returncode=0, citation="a", diagnostics="current diagnostics"):
        def fake_run(command, cwd, env):
            self.calls.append(command[0])
            if command[0] == "xelatex":
                (self.build / "main.aux").write_text(f"\\citation{{{citation}}}\n", encoding="utf-8")
                return 0, "XeLaTeX mock"
            self.assertEqual(command, ["bibtex", "main"])
            self.assertFalse(self.bbl.exists(), "stale BBL must not occupy current output")
            if fresh is not None:
                self.bbl.write_text(fresh, encoding="utf-8")
            self.blg.write_text(diagnostics, encoding="utf-8")
            return returncode, diagnostics
        with patch.object(compiler, "_run", side_effect=fake_run):
            return compiler.run_manual_compile(self.paper, "xelatex", "bibtex", False, {})

    def test_same_citation_key_changed_bib_content_must_execute_bibtex(self):
        (self.paper / "references.bib").write_text("@book{a,title={NEW TITLE}}", encoding="utf-8")
        code, output = self.run_case(self.bibliography({"a": "NEW TITLE"}))
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, ["xelatex", "bibtex", "xelatex", "xelatex"])
        self.assertIn("NEW TITLE", self.bbl.read_text(encoding="utf-8"))
        self.assertNotIn("[bibtex-reuse]", output)
        attempts = list((self.build / "manual-attempts").iterdir())
        self.assertEqual(len(attempts), 1)
        self.assertEqual((attempts[0] / "previous-main.bbl").read_text(encoding="utf-8"), self.old_bbl)
        self.assertEqual((attempts[0] / "previous-main.blg").read_text(encoding="utf-8"), "old diagnostic sentinel")

    def test_crash_with_truncated_partial_bbl_is_rejected_and_retained(self):
        partial = "\\begin{thebibliography}{9}\n\\bibitem{a} partial"
        code, output = self.run_case(partial, returncode=3221226356, citation="a,b", diagnostics="heap failure")
        self.assertEqual(code, 3221226356)
        self.assertEqual(self.calls, ["xelatex", "bibtex"])
        self.assertIn("nonzero exit", output)
        attempt = next((self.build / "manual-attempts").iterdir())
        self.assertEqual((attempt / "main.bbl").read_text(encoding="utf-8"), partial)
        self.assertIn("heap failure", (attempt / "compile.log").read_text(encoding="utf-8"))
        self.assertEqual((attempt / "main.blg").read_text(encoding="utf-8"), "heap failure")

    def test_nonzero_exit_with_even_complete_bbl_is_not_tolerated(self):
        code, _ = self.run_case(self.bibliography({"a": "new"}), returncode=1)
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, ["xelatex", "bibtex"])

    def test_new_citation_and_empty_failed_bbl_never_restore_old_as_success(self):
        code, output = self.run_case("", returncode=1, citation="a,b")
        self.assertEqual(code, 1)
        self.assertEqual(self.bbl.read_bytes(), b"")
        self.assertNotIn("[bibtex-recovery]", output)
        attempt = next((self.build / "manual-attempts").iterdir())
        self.assertEqual((attempt / "previous-main.bbl").read_text(encoding="utf-8"), self.old_bbl)
        self.assertEqual((attempt / "main.bbl").read_bytes(), b"")

    def test_zero_exit_requires_fresh_complete_bbl_and_all_current_keys(self):
        for fresh in (None, "", "\\bibitem{a} incomplete", self.bibliography({"a": "missing b"})):
            with self.subTest(fresh=fresh):
                self.calls.clear()
                code, output = self.run_case(fresh, citation="a,b")
                self.assertEqual(code, 2)
                self.assertEqual(self.calls, ["xelatex", "bibtex"])
                self.assertIn("[bibtex-rejected]", output)

    def test_wildcard_nocite_is_not_treated_as_literal_bibliography_key(self):
        code, _ = self.run_case(self.bibliography({"a": "one", "b": "two"}), citation="*")
        self.assertEqual(code, 0)

    def test_included_aux_citations_are_checked(self):
        (self.build / "chapter.aux").write_text("\\citation{b,c}\n", encoding="utf-8")
        main_aux = self.build / "main.aux"
        main_aux.write_text("\\citation{a}\n\\@input{chapter.aux}\n", encoding="utf-8")
        self.assertEqual(compiler.aux_citation_keys(main_aux), {"a", "b", "c"})

    def test_repeated_attempt_keeps_previous_failure_journal(self):
        self.run_case("", returncode=1, diagnostics="first failure")
        attempt = next((self.build / "manual-attempts").iterdir())
        prior_log = (attempt / "compile.log").read_bytes()
        code, _ = self.run_case(self.bibliography({"a": "fixed"}))
        self.assertEqual(code, 0)
        self.assertEqual(len(list((self.build / "manual-attempts").iterdir())), 2)
        self.assertEqual((attempt / "compile.log").read_bytes(), prior_log)
        self.assertEqual((attempt / "main.bbl").read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
