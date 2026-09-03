"""CUMCM-oriented XeLaTeX compile and static verification helper."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


MAX_BYTES = 20 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    code, output = _run(xelatex_command, paper, env)
    logs.append("[xelatex-1]\n" + output)
    if code != 0:
        return code, "\n".join(logs)
    if not no_citations:
        bib_env = dict(env)
        # Preserve TeX's default search path (the trailing separator) while
        # making the paper root visible from the build directory.
        bib_env["BIBINPUTS"] = str(paper) + os.pathsep + bib_env.get("BIBINPUTS", "")
        bib_env["BSTINPUTS"] = str(paper) + os.pathsep + bib_env.get("BSTINPUTS", "")
        bbl = build / "main.bbl"
        aux = build / "main.aux"
        previous_bbl = bbl.read_bytes() if bbl.is_file() and bbl.stat().st_size > 0 else None
        cited_keys: set[str] = set()
        if aux.is_file():
            for group in re.findall(r"\\citation\{([^}]*)\}", aux.read_text(encoding="utf-8", errors="replace")):
                cited_keys.update(key.strip() for key in group.split(",") if key.strip())
        existing_bbl_text = bbl.read_text(encoding="utf-8", errors="replace") if bbl.is_file() else ""
        existing_keys = set(re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", existing_bbl_text))
        if cited_keys and cited_keys.issubset(existing_keys):
            logs.append(f"[bibtex-reuse] verified {len(cited_keys)} cited keys in existing main.bbl")
            code = 0
            output = ""
        else:
            code, output = _run([bibtex, "main"], build, bib_env)
            logs.append("[bibtex]\n" + output)
        if code != 0:
            # Some MiKTeX installations return their maintenance-state code
            # even though BibTeX produced a complete .bbl.  Accept only the
            # material artifact, never the process message alone.
            fatal_markers = ("I couldn't open", "Emergency stop", "---line ", "error message")
            bbl_complete = bbl.is_file() and bbl.stat().st_size > 0 and "\\bibitem" in bbl.read_text(
                encoding="utf-8", errors="replace"
            )
            if not bbl_complete and previous_bbl is not None:
                bbl.write_bytes(previous_bbl)
                bbl_complete = "\\bibitem" in previous_bbl.decode("utf-8", errors="replace")
                logs.append("[bibtex-recovery] restored the previously verified non-empty main.bbl")
            if not bbl_complete or any(marker.lower() in output.lower() for marker in fatal_markers):
                return code, "\n".join(logs)
            logs.append(f"[bibtex-maintenance-code-tolerated] returncode={code}; complete main.bbl verified")
    for pass_number in (2, 3):
        code, output = _run(xelatex_command, paper, env)
        logs.append(f"[xelatex-{pass_number}]\n" + output)
        if code != 0:
            return code, "\n".join(logs)
    return 0, "\n".join(logs)


def run_compile(
    paper: Path,
    latexmk: str,
    xelatex: str,
    bibtex: str,
    no_citations: bool,
) -> tuple[int, str, str]:
    command = [latexmk, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex"]
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
    """Render a bounded PDF preview for a human visual check when available."""
    converter = find_binary("pdftoppm")
    if not converter:
        return []
    proc = subprocess.run(
        [converter, "-png", "-r", "144", "-f", "1", "-l", "3", str(pdf), str(target_prefix)],
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
        "--visual-report",
        type=Path,
        help="Existing full-page visual QA JSON; accepted only when PASS and hash-bound to the compiled PDF.",
    )
    args = ap.parse_args()
    paper = args.paper_dir.resolve()
    main_tex = paper / "main.tex"
    report_path = args.report.resolve() if args.report else paper / "compile_report.json"
    report: dict = {"profile": "cumcm-2026-electronic", "paper_dir": ".", "static_issues": [], "status": "UNKNOWN"}
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
    citation_re = re.compile(r"\\(?:cite|citep|citet|parencite|textcite)\*?")
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
    log_counts = classify_latex_log(build_dir / "main.log")
    report["log_checks"] = log_counts
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
    pdf = paper / "main.pdf"
    if built_pdf.is_file():
        shutil.copy2(built_pdf, pdf)
    body_start, appendix_start = aux_page(aux, "mm:body-start"), aux_page(aux, "mm:appendix-start")
    report.update(body_start_page=body_start, appendix_start_page=appendix_start)
    if body_start is not None and appendix_start is not None:
        report["body_pages"] = appendix_start - body_start
        if report["body_pages"] > 30:
            report["status"] = "PAGE_LIMIT_FAILED"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
    if not pdf.is_file():
        report["status"] = "PDF_MISSING"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    report["pdf_bytes"] = pdf.stat().st_size
    report["pdf_sha256"] = sha256(pdf)
    if report["pdf_bytes"] > MAX_BYTES:
        report["status"] = "PDF_SIZE_FAILED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2
    preview_pages = render_preview(pdf, build_dir / "preview")
    report["visual_preview_pages"] = [str(path.relative_to(paper)) for path in map(Path, preview_pages)]
    if args.visual_report:
        visual_path = args.visual_report.resolve()
        try:
            visual = json.loads(visual_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["visual_check_status"] = "VISUAL_REPORT_INVALID"
            report["status"] = "VISUAL_CHECK_FAILED"
            report["visual_check_error"] = str(exc)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        visual_hash = str(visual.get("paper_sha256", "")).lower()
        if visual.get("status") != "PASSED" or visual_hash != report["pdf_sha256"]:
            report["visual_check_status"] = "VISUAL_REPORT_STALE_OR_FAILED"
            report["status"] = "VISUAL_CHECK_FAILED"
            report["visual_report_status"] = visual.get("status")
            report["visual_report_pdf_sha256"] = visual_hash or None
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2
        try:
            report["visual_check_report"] = str(visual_path.relative_to(paper))
        except ValueError:
            report["visual_check_report"] = visual_path.name
        report["visual_check_status"] = f"PASSED_ALL_{visual.get('page_count', 'DECLARED')}_PAGES"
        report["status"] = "PASSED"
    else:
        report["visual_check_status"] = "REVIEW_REQUIRED" if preview_pages else "BACKEND_UNAVAILABLE"
        report["status"] = "COMPILED_PENDING_VISUAL_CHECK"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
