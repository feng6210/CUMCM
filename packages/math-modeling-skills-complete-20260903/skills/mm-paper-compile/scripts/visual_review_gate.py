"""Bind and verify a reviewed CUMCM PDF without rebuilding it."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
COMPILE_SCRIPT = SCRIPT_DIR / "compile_paper.py"


def _load_compile_module():
    spec = importlib.util.spec_from_file_location("mm_compile_paper_for_visual_gate", COMPILE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {COMPILE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compile_paper = _load_compile_module()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: JSON object required")
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _artifact(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("artifact path must be a non-empty string")
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def review_evidence_paths(visual_path: Path | None) -> set[Path]:
    """Exclude review-only JSON/PNGs from the frozen paper-source snapshot."""
    if visual_path is None:
        return set()
    pending = [visual_path.resolve()]
    seen: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            payload = read_json(current)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError):
            continue
        for row in payload.get("page_images", []):
            if isinstance(row, dict) and isinstance(row.get("file"), str) and row["file"].strip():
                pending.append(_artifact(current.parent, row["file"]))
        previous = payload.get("previous_report")
        if isinstance(previous, dict) and isinstance(previous.get("file"), str) and previous["file"].strip():
            pending.append(_artifact(current.parent, previous["file"]))
    return seen


def source_snapshot(paper: Path, excluded: set[Path]) -> dict:
    """Hash paper inputs while excluding compiler outputs and review evidence."""
    excluded = {path.resolve() for path in excluded}
    generated_suffixes = {".aux", ".log", ".out", ".toc", ".blg", ".bbl", ".fls", ".fdb_latexmk"}
    files: list[dict] = []
    for path in sorted(paper.rglob("*"), key=lambda item: item.relative_to(paper).as_posix()):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(paper)
        if rel.parts and rel.parts[0] == "build":
            continue
        if path.resolve() in excluded:
            continue
        if path.name == "compile.log" or path.name.endswith(".synctex.gz") or path.suffix.lower() in generated_suffixes:
            continue
        files.append({"path": rel.as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": "1.0",
        "file_count": len(files),
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "files": files,
    }


def resolve_paths(args) -> tuple[Path, Path, Path, Path]:
    paper = args.paper_dir.resolve()
    compile_report = (args.compile_report if args.compile_report.is_absolute() else paper / args.compile_report).resolve()
    output_pdf = (args.output_pdf if args.output_pdf.is_absolute() else paper / args.output_pdf).resolve()
    binding = (args.binding if args.binding.is_absolute() else paper / args.binding).resolve()
    return paper, compile_report, output_pdf, binding


def prepare(args) -> tuple[int, dict]:
    paper, compile_report_path, pdf, binding_path = resolve_paths(args)
    if not compile_report_path.is_file():
        return 2, {"status": "COMPILE_REPORT_MISSING", "compile_report": str(compile_report_path)}
    report = read_json(compile_report_path)
    if report.get("pdf_published") is not True:
        return 2, {"status": "COMPILE_REPORT_NOT_PUBLISHED", "compile_report": str(compile_report_path)}
    try:
        recorded_pdf = Path(report["pdf_path"]).resolve()
    except (KeyError, TypeError):
        return 2, {"status": "COMPILE_REPORT_INVALID", "reason": "pdf_path missing"}
    if recorded_pdf != pdf:
        return 2, {"status": "COMPILE_REPORT_OUTPUT_MISMATCH", "recorded_pdf": str(recorded_pdf), "requested_pdf": str(pdf)}
    if not pdf.is_file() or pdf.is_symlink():
        return 2, {"status": "PUBLISHED_PDF_MISSING", "pdf": str(pdf)}
    current_pdf_hash = sha256(pdf)
    if str(report.get("pdf_sha256", "")).lower() != current_pdf_hash:
        return 2, {"status": "PUBLISHED_PDF_CHANGED", "pdf": str(pdf)}
    pages = compile_paper.pdf_page_count(pdf)
    excluded = {compile_report_path, pdf, binding_path}
    snapshot = source_snapshot(paper, excluded)
    binding = {
        "schema_version": "1.0",
        "status": "READY_FOR_VISUAL_REVIEW",
        "paper_dir": str(paper),
        "compile_report": {"file": str(compile_report_path), "sha256": sha256(compile_report_path)},
        "paper_pdf": {"file": str(pdf), "sha256": current_pdf_hash, "page_count": pages},
        "source_snapshot": snapshot,
        "scope": "Binds the already published PDF and paper inputs for later no-recompile visual verification.",
    }
    write_json(binding_path, binding)
    return 0, binding


def verify(args) -> tuple[int, dict]:
    paper, compile_report_path, pdf, binding_path = resolve_paths(args)
    visual_path = (args.visual_report if args.visual_report.is_absolute() else paper / args.visual_report).resolve()
    output_report = (args.report if args.report.is_absolute() else paper / args.report).resolve()
    result = {
        "schema_version": "1.0",
        "verification_mode": "existing_published_artifact_no_recompile",
        "paper_dir": str(paper),
        "status": "UNKNOWN",
    }
    if not binding_path.is_file():
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_MISSING")
        return 2, result
    try:
        binding = read_json(binding_path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID", error=str(exc))
        return 2, result
    compile_binding = binding.get("compile_report")
    pdf_binding = binding.get("paper_pdf")
    source_binding = binding.get("source_snapshot")
    if not all(isinstance(item, dict) for item in (compile_binding, pdf_binding, source_binding)):
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID")
        return 2, result
    if not compile_report_path.is_file() or sha256(compile_report_path) != compile_binding.get("sha256"):
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="COMPILE_REPORT_CHANGED")
        return 2, result
    if _artifact(binding_path.parent, compile_binding.get("file")) != compile_report_path:
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="COMPILE_REPORT_PATH_CHANGED")
        return 2, result
    if not pdf.is_file() or pdf.is_symlink():
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="PUBLISHED_PDF_MISSING")
        return 2, result
    if _artifact(binding_path.parent, pdf_binding.get("file")) != pdf or sha256(pdf) != pdf_binding.get("sha256"):
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="PUBLISHED_PDF_CHANGED")
        return 2, result
    excluded = {compile_report_path, pdf, binding_path, output_report} | review_evidence_paths(visual_path)
    current_snapshot = source_snapshot(paper, excluded)
    result["source_snapshot"] = {"expected": source_binding.get("sha256"), "current": current_snapshot["sha256"]}
    if current_snapshot["sha256"] != source_binding.get("sha256"):
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="SOURCE_SNAPSHOT_CHANGED")
        return 2, result
    pages = compile_paper.pdf_page_count(pdf)
    visual_check = compile_paper.check_visual_report(visual_path, pdf, pages)
    result["paper_pdf"] = {"file": str(pdf), "sha256": sha256(pdf), "page_count": pages}
    result["compile_report"] = {"file": str(compile_report_path), "sha256": sha256(compile_report_path)}
    result["visual_report"] = {"file": str(visual_path), "sha256": sha256(visual_path)}
    result["visual_check_details"] = visual_check
    result["visual_check_status"] = visual_check["status"]
    if visual_check["status"] == "PASSED":
        result["status"] = "PASSED"
        result["visual_check_status"] = f"PASSED_ALL_{pages}_PAGES"
        code = 0
    elif visual_check["status"] == "REVIEW_REQUIRED":
        result["status"] = "COMPILED_PENDING_VISUAL_CHECK"
        code = 0
    else:
        result["status"] = "VISUAL_CHECK_FAILED"
        code = 2
    write_json(output_report, result)
    return code, result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--paper-dir", type=Path, required=True)
        p.add_argument("--compile-report", type=Path, default=Path("compile_report.json"))
        p.add_argument("--output-pdf", type=Path, default=Path("main.pdf"))
        p.add_argument("--binding", type=Path, default=Path("VISUAL_REVIEW_BINDING.json"))
        if name == "verify":
            p.add_argument("--visual-report", type=Path, required=True)
            p.add_argument("--report", type=Path, default=Path("visual_verification_report.json"))
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = prepare(args) if args.command == "prepare" else verify(args)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError, KeyError, TypeError) as exc:
        code, payload = 2, {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
