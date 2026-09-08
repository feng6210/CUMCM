"""CUMCM-oriented XeLaTeX compile and static verification helper."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


MAX_BYTES = 20 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_pdf_path(paper: Path, requested: Path | None) -> Path:
    """Resolve the user's output, without choosing an alternate on failure."""
    target = requested if requested is not None else Path("main.pdf")
    target = (target if target.is_absolute() else paper / target).resolve()
    if target.suffix.lower() != ".pdf":
        raise ValueError("--output-pdf must name a .pdf file, not a directory or another format")
    if target.exists() and not target.is_file():
        raise ValueError("--output-pdf names an existing directory or non-file")
    if not target.parent.is_dir():
        raise ValueError("--output-pdf parent directory does not exist; create or select it explicitly")
    if target.is_relative_to((paper / "build").resolve()):
        raise ValueError("--output-pdf must be outside the compiler's build directory")
    return target


def prepare_build_pdf(paper: Path) -> dict | None:
    """Retain a prior build PDF so this invocation must produce a new artifact."""
    build = paper / "build"
    build.mkdir(parents=True, exist_ok=True)
    previous = build / "main.pdf"
    if not previous.exists():
        return None
    if not previous.is_file() or previous.is_symlink():
        raise OSError("build/main.pdf must be a regular, non-symlink build artifact")
    digest = sha256(previous)
    archive = build / "previous-pdfs"
    archive.mkdir(exist_ok=True)
    retained = archive / f"main-{uuid.uuid4().hex}.pdf"
    previous.rename(retained)
    return {"path": str(retained), "sha256": digest}


def publish_pdf(source: Path, destination: Path) -> None:
    """Stage in the destination directory; a locked output keeps its old bytes."""
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-", suffix=".pdf.tmp",
            dir=destination.parent, delete=False,
        ) as stream:
            staged = Path(stream.name)
        shutil.copy2(source, staged)
        if sha256(staged) != sha256(source):
            raise OSError("staged PDF hash differs from the build artifact")
        os.replace(staged, destination)
    finally:
        if staged is not None and staged.exists():
            try:
                staged.unlink()
            except OSError:
                # The fresh source remains in build/main.pdf for diagnosis.
                pass


def pdf_page_count(pdf: Path) -> int | None:
    """Read actual page count when pypdf or Poppler is available."""
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf).pages)
    except Exception:
        converter = find_binary("pdfinfo")
        if not converter:
            return None
        try:
            proc = subprocess.run([converter, str(pdf)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
        except OSError:
            return None
        match = re.search(r"^Pages:\s*(\d+)\s*$", proc.stdout, re.MULTILINE)
        return int(match.group(1)) if proc.returncode == 0 and match else None


def _page_set(value: object) -> set[int] | None:
    if not isinstance(value, list) or any(type(page) is not int for page in value):
        return None
    return set(value) if len(value) == len(set(value)) else None


def _relative_file(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("artifact file path must be a non-empty string")
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def check_visual_report(visual_path: Path, pdf: Path, pages: int | None) -> dict:
    """Check a manual review's binding and scope, not its claimed independence."""
    try:
        visual = json.loads(visual_path.read_text(encoding="utf-8-sig"))
        if not isinstance(visual, dict):
            raise ValueError("visual report must be an object")
        if visual.get("status") != "PASSED" or str(visual.get("paper_sha256", "")).lower() != sha256(pdf):
            return {"status": "VISUAL_REPORT_STALE_OR_FAILED"}
        if "paper_pdf" in visual and _relative_file(visual_path.parent, visual["paper_pdf"]) != pdf:
            return {"status": "VISUAL_REPORT_OUTPUT_PATH_MISMATCH"}
        required = ("page_count", "rendered_pages", "reviewed_pages", "reviewer_id", "reviewer_role")
        missing = [name for name in required if name not in visual]
        if missing or pages is None:
            return {"status": "REVIEW_REQUIRED", "missing_fields": missing,
                    "reason": "Legacy scope needs explicit full-page coverage and reviewer role, or actual PDF page count is unavailable"}
        expected = set(range(1, pages + 1))
        if type(visual["page_count"]) is not int or pages < 1 or visual["page_count"] != pages:
            return {"status": "VISUAL_REPORT_PAGE_COUNT_MISMATCH"}
        if _page_set(visual["rendered_pages"]) != expected or _page_set(visual["reviewed_pages"]) != expected:
            return {"status": "VISUAL_REPORT_COVERAGE_INCOMPLETE"}
        if any(not isinstance(visual[name], str) or not visual[name].strip()
               for name in ("reviewer_id", "reviewer_role")):
            return {"status": "REVIEW_REQUIRED", "reason": "Actual reviewer identity and role must be stated"}
        inherited = _page_set(visual.get("inherited_pages", []))
        if inherited is None or not inherited.issubset(expected):
            return {"status": "VISUAL_REPORT_INHERITANCE_INVALID"}
        if inherited:
            previous_binding = visual.get("previous_report", {})
            previous_path = _relative_file(visual_path.parent, previous_binding.get("file"))
            if previous_path == visual_path or sha256(previous_path) != previous_binding.get("sha256"):
                raise ValueError("previous review must be preserved as a separate hash-bound file")
            previous = json.loads(previous_path.read_text(encoding="utf-8-sig"))
            if previous.get("status") != "PASSED" or not inherited.issubset(_page_set(previous.get("reviewed_pages")) or set()):
                raise ValueError("previous review does not cover inherited pages")
            old_images = {row["page"]: row for row in previous.get("page_images", [])}
            images = {row["page"]: row for row in visual.get("page_images", [])}
            for page in inherited:
                row, old = images[page], old_images[page]
                image = _relative_file(visual_path.parent, row["file"])
                if image.suffix.lower() != ".png" or not image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError(f"page {page}: expected rendered PNG evidence")
                if sha256(image) != row["sha256"] or row["sha256"] != old["sha256"]:
                    raise ValueError(f"page {page}: rendered image changed; direct re-review required")
        return {"status": "PASSED", "page_count": pages,
                "reviewer_id": visual["reviewer_id"], "reviewer_role": visual["reviewer_role"],
                "inherited_pages": sorted(inherited), "independence_certified": False}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return {"status": "VISUAL_REPORT_INVALID", "error": str(exc)}


def classify_latex_log(log_path: Path) -> dict[str, int]:
    """Return fail-closed counts for reference, glyph, and layout defects."""
    if not log_path.is_file():
        return {
            "undefined_citations": 0,
            "undefined_references": 0,
            "missing_characters": 0,
            "overfull_boxes": 0,
            "underfull_boxes": 0,
        }
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return {
        "undefined_citations": len(re.findall(r"Citation [`'][^\n]+ undefined", text, flags=re.IGNORECASE)),
        "undefined_references": len(re.findall(r"Reference [`'][^\n]+ undefined", text, flags=re.IGNORECASE)),
        "missing_characters": len(re.findall(r"Missing character:", text, flags=re.IGNORECASE)),
        "overfull_boxes": len(re.findall(r"Overfull \\[hv]box", text, flags=re.IGNORECASE)),
        "underfull_boxes": len(re.findall(r"Underfull \\[hv]box", text, flags=re.IGNORECASE)),
    }


def sanitize_log_excerpt(text: str, paper: Path) -> str:
    """Keep diagnostics useful without persisting local identity-bearing paths."""
    replacements = {
        str(paper): "<PAPER_DIR>",
        str(Path.home()): "<USER_HOME>",
    }
    result = text
    for raw, marker in replacements.items():
        result = result.replace(raw, marker)
        result = result.replace(raw.replace("\\", "/"), marker)
    return result


def find_binary(name: str) -> str | None:
    """Find a TeX executable without assuming MiKTeX is already on PATH."""
    found = shutil.which(name)
    if found:
        return found
    roots = [
        Path(r"C:\\Program Files\\MiKTeX\\miktex\\bin\\x64"),
        Path(r"C:\\Program Files\\MiKTeX\\miktex\\bin"),
        Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
    ]
    executable = f"{name}.exe" if not name.lower().endswith(".exe") else name
    for root in roots:
        candidate = root / executable
        if candidate.is_file():
            return str(candidate)
    return None


def aux_page(aux: Path, label: str) -> int | None:
    if not aux.is_file():
        return None
    match = re.search(r"\\newlabel\{" + re.escape(label) + r"\}\{\{[^}]*\}\{(\d+)\}", aux.read_text(encoding="utf-8", errors="replace"))
    return int(match.group(1)) if match else None


def static_check(main: Path) -> list[dict]:
    text = main.read_text(encoding="utf-8", errors="replace")
    issues: list[dict] = []
    checks = [
        (r"\\tableofcontents", "error", "CUMCM electronic paper must not generate a table of contents"),
        (r"\\author\s*\{[^}]+\}", "error", "anonymous electronic paper must not declare an author"),
        (r"\\institute\s*\{[^}]+\}", "error", "anonymous electronic paper must not declare an institute"),
        (r"\\maketitle", "warn", "use the template's \\makeMMTitle instead of a normal author title block"),
    ]
    for pattern, severity, message in checks:
        if re.search(pattern, text):
            if "required" not in message:
                issues.append({"severity": severity, "message": message})
        elif "required" in message:
            issues.append({"severity": severity, "message": message})
    bundled_template = "\\documentclass{mm-cumcm}" in text
    # The bundled class exposes semantic marker macros. A user-provided official
    # template may instead use literal labels or omit these optional markers; in
    # that case retain the template and report a limited page-count check.
    label_severity = "error" if bundled_template else "warn"
    if not re.search(r"\\(?:label\{mm:body-start\}|mmBodyStart\b)", text):
        issues.append({"severity": label_severity, "message": "body start label is required for automatic page counting"})
    if not re.search(r"\\(?:label\{mm:appendix-start\}|mmAppendixStart\b)", text):
        issues.append({"severity": label_severity, "message": "appendix start label is required for automatic page counting"})
    if not bundled_template:
        issues.append({"severity": "warn", "message": "custom or official template in use; CUMCM source checks are limited"})
    return issues


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, proc.stdout + "\n" + proc.stderr


def aux_citation_keys(aux: Path, seen: set[Path] | None = None) -> set[str]:
    """Read BibTeX citations, including chapter AUX files and nocite wildcard."""
    seen = set() if seen is None else seen
    aux = aux.resolve()
    if aux in seen:
        return set()
    seen.add(aux)
    text = aux.read_text(encoding="utf-8", errors="replace")
    keys = {key.strip() for group in re.findall(r"\\citation\{([^}]*)\}", text)
            for key in group.split(",") if key.strip()}
    for child in re.findall(r"\\@input\{([^}]+)\}", text):
        keys.update(aux_citation_keys(aux.parent / child, seen))
    return keys


def run_manual_compile(
    paper: Path,
    xelatex: str,
    bibtex: str,
    no_citations: bool,
    env: dict[str, str],
) -> tuple[int, str]:
    """Use an argument-list fallback when latexmk cannot spawn BibTeX on Windows."""
    build = paper / "build"
    build.mkdir(parents=True, exist_ok=True)
    xelatex_command = [
        xelatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-output-directory=build",
        "main.tex",
    ]
    logs: list[str] = ["[manual-fallback]"]
    attempt = build / "manual-attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True)

    def finish(returncode: int) -> tuple[int, str]:
        text = "\n".join(logs)
        (attempt / "compile.log").write_text(text, encoding="utf-8")
        return returncode, text

    def retain_bibliography(label: str) -> None:
        for extension in ("bbl", "blg"):
            artifact = build / f"main.{extension}"
            if artifact.exists() or artifact.is_symlink():
                if not artifact.is_file() or artifact.is_symlink():
                    raise OSError(f"{artifact.name} must be a regular, non-symlink artifact")
                retained = attempt / f"{label}-main.{extension}"
                digest = sha256(artifact)
                artifact.rename(retained)
                logs.append(f"[bibliography-retained] {retained}; sha256={digest}")

    if not no_citations:
        try:
            retain_bibliography("previous")
        except OSError as exc:
            logs.append(f"[bibliography-preservation-failed] {type(exc).__name__}: {exc}")
            return finish(2)
    code, output = _run(xelatex_command, paper, env)
    logs.append("[xelatex-1]\n" + output)
    if code != 0:
        return finish(code)
    if not no_citations:
        bib_env = dict(env)
        # Preserve TeX's default search path (the trailing separator) while
        # making the paper root visible from the build directory.
        bib_env["BIBINPUTS"] = str(paper) + os.pathsep + bib_env.get("BIBINPUTS", "")
        bib_env["BSTINPUTS"] = str(paper) + os.pathsep + bib_env.get("BSTINPUTS", "")
        bbl = build / "main.bbl"
        aux = build / "main.aux"
        try:
            cited_keys = aux_citation_keys(aux)
            # Even an unexpected first-pass BBL is not a current BibTeX output.
            retain_bibliography("pre-bibtex")
            code, output = _run([bibtex, "main"], build, bib_env)
        except OSError as exc:
            logs.append(f"[bibtex-execution-failed] {type(exc).__name__}: {exc}")
            return finish(2)
        logs.append(f"[bibtex] returncode={code}\n" + output)
        # Keep every attempt's raw outputs, including empty/truncated failures.
        try:
            for extension in ("bbl", "blg"):
                artifact = build / f"main.{extension}"
                if artifact.is_file() and not artifact.is_symlink():
                    shutil.copy2(artifact, attempt / artifact.name)
        except OSError as exc:
            logs.append(f"[bibtex-evidence-preservation-failed] {type(exc).__name__}: {exc}")
            return finish(code if code != 0 else 2)
        if code != 0:
            logs.append("[bibtex-rejected] nonzero exit; old BBL is retained only as history, never restored for success")
            return finish(code)
        if not bbl.is_file() or bbl.is_symlink():
            logs.append("[bibtex-rejected] no fresh regular main.bbl produced")
            return finish(2)
        fresh_text = bbl.read_text(encoding="utf-8", errors="replace")
        fresh_keys = set(re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", fresh_text))
        missing = (cited_keys - {"*"}) - fresh_keys
        if (not fresh_keys or missing
                or not re.search(r"\\begin\s*\{thebibliography\}", fresh_text)
                or not re.search(r"\\end\s*\{thebibliography\}", fresh_text)):
            logs.append(f"[bibtex-rejected] incomplete current BBL; missing cited keys={sorted(missing)}")
            return finish(2)
        logs.append(f"[bibtex-fresh-output] sha256={sha256(bbl)}; cited-key coverage checked, not a citation-content audit")
    for pass_number in (2, 3):
        code, output = _run(xelatex_command, paper, env)
        logs.append(f"[xelatex-{pass_number}]\n" + output)
        if code != 0:
            return finish(code)
    return finish(0)


def run_compile(
    paper: Path,
    latexmk: str,
    xelatex: str,
    bibtex: str,
    no_citations: bool,
) -> tuple[int, str, str]:
    command = [latexmk, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-outdir=build", "main.tex"]
    # The starter template intentionally has an empty bibliography.  Avoid a
    # needless BibTeX run in that case; a real \cite always keeps the normal
    # BibTeX route and its failures remain visible.
    if no_citations:
        command.insert(1, "-nobibtex")
    env = dict(os.environ)
    env["PATH"] = str(Path(latexmk).parent) + os.pathsep + env.get("PATH", "")
    if os.name == "nt" and not no_citations:
        returncode, output = run_manual_compile(paper, xelatex, bibtex, no_citations, env)
        (paper / "compile.log").write_text(output, encoding="utf-8")
        return returncode, output, "manual_windows_bibtex_safe"
    returncode, output = _run(command, paper, env)
    compiler_route = "latexmk"
    if returncode != 0:
        fallback_code, fallback_output = run_manual_compile(paper, xelatex, bibtex, no_citations, env)
        output = output + "\n\n" + fallback_output
        returncode = fallback_code
        compiler_route = "manual_fallback"
    (paper / "compile.log").write_text(output, encoding="utf-8")
    return returncode, output, compiler_route


def render_preview(pdf: Path, target_prefix: Path) -> list[str]:
    """Render all pages for review; successful rendering is not manual review."""
    converter = find_binary("pdftoppm")
    if not converter:
        return []
    proc = subprocess.run(
        [converter, "-png", "-r", "144", str(pdf), str(target_prefix)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if proc.returncode != 0:
        return []
    return [str(path) for path in sorted(target_prefix.parent.glob(target_prefix.name + "-*.png")) if path.stat().st_size > 0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile and inspect a Chinese CUMCM LaTeX paper.")
    ap.add_argument("--paper-dir", type=Path, required=True)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--report", type=Path)
    ap.add_argument(
        "--output-pdf", type=Path,
        help="Explicit PDF filename, relative to --paper-dir or absolute; default main.pdf. Never selected automatically after a lock failure.",
    )
    ap.add_argument(
        "--visual-report",
        type=Path,
        help="Existing full-page visual QA JSON; accepted only when PASS and hash-bound to the compiled PDF.",
    )
    args = ap.parse_args()
    paper = args.paper_dir.resolve()
    main_tex = paper / "main.tex"
    report_path = args.report.resolve() if args.report else paper / "compile_report.json"
    if report_path.suffix.lower() == ".pdf":
        ap.error("--report must name a JSON report, not a PDF output")
    report: dict = {"profile": "cumcm-2026-electronic", "paper_dir": ".", "static_issues": [], "status": "UNKNOWN"}
    try:
        pdf = output_pdf_path(paper, args.output_pdf)
    except (OSError, ValueError) as exc:
        report.update(status="OUTPUT_PATH_INVALID", error=str(exc))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    report.update(pdf_path=str(pdf), output_pdf_explicit=args.output_pdf is not None, pdf_published=False)
    if not main_tex.is_file():
        report.update(status="INPUT_MISSING", error="main.tex is missing")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    report["static_issues"] = static_check(main_tex)
    if any(i["severity"] == "error" for i in report["static_issues"]):
        report["status"] = "STATIC_CHECK_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    latexmk, xelatex, bibtex = find_binary("latexmk"), find_binary("xelatex"), find_binary("bibtex")
    report["latexmk"] = latexmk
    report["xelatex"] = xelatex
    report["bibtex"] = bibtex
    if args.check_only:
        report["status"] = "STATIC_CHECK_PASSED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if not latexmk or not xelatex or not bibtex:
        report["status"] = "BACKEND_UNAVAILABLE"
        report["error"] = "latexmk, xelatex, and bibtex are all required for compilation"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 3
    citation_re = re.compile(r"\\(?:cite|citep|citet|parencite|textcite|nocite)\*?")
    tex_sources = [path for path in paper.rglob("*.tex") if "build" not in path.parts]
    tex_texts = [path.read_text(encoding="utf-8", errors="replace") for path in tex_sources]
    has_citations = any(citation_re.search(text) for text in tex_texts)
    manual_bibliography = any("\\begin{thebibliography}" in text for text in tex_texts)
    no_citations = not has_citations or manual_bibliography
    report["bibliography_mode"] = (
        "manual_thebibliography"
        if has_citations and manual_bibliography
        else "no_citations_skip_bibtex"
        if not has_citations
        else "bibtex_required"
    )
    try:
        report["previous_build_pdf"] = prepare_build_pdf(paper)
    except OSError as exc:
        report.update(status="BUILD_PREPARATION_FAILED", error=f"Cannot retain prior build PDF: {type(exc).__name__}: {exc}")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    returncode, output, compiler_route = run_compile(paper, latexmk, xelatex, bibtex, no_citations)
    report["compiler_returncode"] = returncode
    report["compiler_route"] = compiler_route
    report["log_tail"] = sanitize_log_excerpt(output[-4000:], paper)
    if returncode != 0:
        report["status"] = "COMPILE_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    build_dir = paper / "build"
    built_pdf, aux = build_dir / "main.pdf", build_dir / "main.aux"
    report["source_pdf_path"] = str(built_pdf)
    if not built_pdf.is_file() or built_pdf.is_symlink():
        report.update(status="PDF_MISSING", error="This invocation produced no regular build/main.pdf; an old delivery PDF is not a substitute")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    with built_pdf.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            report.update(status="PDF_INVALID", error="Fresh build artifact does not have a PDF header")
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
    report["source_pdf_sha256"] = sha256(built_pdf)
    log_counts = classify_latex_log(build_dir / "main.log")
    report["log_checks"] = log_counts
    report["layout_notes"] = (["Underfull boxes require visual inspection; they do not automatically fail or authorize source deletion"]
                              if log_counts["underfull_boxes"] else [])
    if log_counts["undefined_citations"] or log_counts["undefined_references"]:
        report["status"] = "REFERENCE_CHECK_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    if log_counts["missing_characters"]:
        report["status"] = "GLYPH_CHECK_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    if log_counts["overfull_boxes"]:
        report["status"] = "LAYOUT_CHECK_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    body_start, appendix_start = aux_page(aux, "mm:body-start"), aux_page(aux, "mm:appendix-start")
    report.update(body_start_page=body_start, appendix_start_page=appendix_start)
    if body_start is not None and appendix_start is not None:
        report["body_pages"] = appendix_start - body_start
        if report["body_pages"] > 30:
            report["status"] = "PAGE_LIMIT_FAILED"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
    report["source_pdf_bytes"] = built_pdf.stat().st_size
    report["pdf_pages"] = pdf_page_count(built_pdf)
    if report["pdf_pages"] is not None and appendix_start is not None:
        report["appendix_pages"] = report["pdf_pages"] - appendix_start + 1
    if report["source_pdf_bytes"] > MAX_BYTES:
        report["status"] = "PDF_SIZE_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    try:
        publish_pdf(built_pdf, pdf)
    except OSError as exc:
        report.update(status="PDF_PUBLISH_FAILED", error_type=type(exc).__name__,
                      error=f"Cannot publish requested PDF: {exc}",
                      recovery="Close the application locking the output, or explicitly choose --output-pdf with another filename; no alternative was published")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    report.update(pdf_published=True, pdf_bytes=pdf.stat().st_size, pdf_sha256=sha256(pdf))
    # A unique prefix prevents old, higher-numbered preview pages being reused.
    preview_pages = render_preview(pdf, build_dir / f"preview-{uuid.uuid4().hex}")
    report["visual_preview_pages"] = [str(path.relative_to(paper)) for path in map(Path, preview_pages)]
    report["visual_render_scope"] = "all_pdf_pages_requested"
    report["visual_rendered_page_count"] = len(preview_pages)
    if args.visual_report:
        visual_path = args.visual_report.resolve()
        visual_check = check_visual_report(visual_path, pdf, report["pdf_pages"])
        report["visual_check_details"] = visual_check
        report["visual_check_status"] = visual_check["status"]
        if visual_check["status"] not in {"PASSED", "REVIEW_REQUIRED"}:
            report["status"] = "VISUAL_CHECK_FAILED"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        try:
            report["visual_check_report"] = str(visual_path.relative_to(paper))
        except ValueError:
            report["visual_check_report"] = visual_path.name
        report["visual_report_sha256"] = sha256(visual_path)
        if visual_check["status"] == "PASSED":
            report["visual_check_status"] = f"PASSED_ALL_{report['pdf_pages']}_PAGES"
            report["status"] = "PASSED"
        else:
            report["status"] = "COMPILED_PENDING_VISUAL_CHECK"
    else:
        report["visual_check_status"] = "REVIEW_REQUIRED" if preview_pages else "BACKEND_UNAVAILABLE"
        report["status"] = "COMPILED_PENDING_VISUAL_CHECK"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
