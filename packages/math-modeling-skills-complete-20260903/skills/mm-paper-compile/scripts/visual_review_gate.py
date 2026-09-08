"""Bind and verify a reviewed CUMCM PDF without rebuilding it."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
COMPILE_SCRIPT = SCRIPT_DIR / "compile_paper.py"
DEFAULT_VISUAL_REPORT = "PDF_VISUAL_CHECK.json"
DEFAULT_VERIFICATION_REPORT = "visual_verification_report.json"
DEFAULT_BINDING = "VISUAL_REVIEW_BINDING.json"
VERIFICATION_MODE = "existing_published_artifact_no_recompile"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


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


def _optional_artifact(base: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def _looks_like_visual_report(payload: dict) -> bool:
    return (
        isinstance(payload.get("status"), str)
        and _is_sha256(payload.get("paper_sha256"))
        and (
            isinstance(payload.get("reviewed_pages"), list)
            or isinstance(payload.get("page_images"), list)
            or payload.get("status") != "PASSED"
        )
    )


def _looks_like_verification_report(payload: dict) -> bool:
    return payload.get("verification_mode") == VERIFICATION_MODE and isinstance(payload.get("status"), str)


def _looks_like_binding(payload: dict) -> bool:
    return (
        payload.get("schema_version") == "1.0"
        and payload.get("status") == "READY_FOR_VISUAL_REVIEW"
        and isinstance(payload.get("compile_report"), dict)
        and isinstance(payload.get("paper_pdf"), dict)
        and isinstance(payload.get("source_snapshot"), dict)
        and isinstance(payload.get("source_snapshot", {}).get("files"), list)
    )


def _validated_reference(
    base: Path,
    row: object,
    suffix: str,
    payload_kind: str | None = None,
) -> Path | None:
    """Resolve a hash-bound review reference; invalid references are not exclusions."""
    if not isinstance(row, dict) or not _is_sha256(row.get("sha256")):
        return None
    path = _optional_artifact(base, row.get("file"))
    if path is None or path.suffix.lower() != suffix or not path.is_file() or path.is_symlink():
        return None
    if sha256(path).lower() != str(row["sha256"]).lower():
        return None
    if payload_kind is not None:
        try:
            payload = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError):
            return None
        if payload_kind == "visual" and not _looks_like_visual_report(payload):
            return None
        if payload_kind == "verification" and not _looks_like_verification_report(payload):
            return None
    return path


def visual_evidence_paths(roots: set[Path]) -> set[Path]:
    """Follow only validated visual-review JSON and hash-bound PNG evidence."""
    pending = [root.resolve() for root in roots]
    seen: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        # A root is an explicitly designated visual-review artifact.  Transitive
        # references are added only after type/role/hash validation below.
        seen.add(current)
        if current.suffix.lower() != ".json" or not current.is_file() or current.is_symlink():
            continue
        try:
            payload = read_json(current)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError):
            continue
        if not _looks_like_visual_report(payload):
            continue

        for row in payload.get("page_images", []):
            image = _validated_reference(current.parent, row, ".png")
            if image is not None:
                seen.add(image)

        previous = _validated_reference(current.parent, payload.get("previous_report"), ".json", "visual")
        if previous is not None:
            pending.append(previous)
    return seen


def discover_verification_reports(
    paper: Path,
    explicit_output: Path | None = None,
) -> tuple[set[Path], set[Path]]:
    """Find gate-owned verification reports and their validated visual reports."""
    reports: set[Path] = {(paper / DEFAULT_VERIFICATION_REPORT).resolve()}
    if explicit_output is not None:
        reports.add(explicit_output.resolve())

    for candidate in paper.rglob("*.json"):
        rel = candidate.relative_to(paper)
        if rel.parts and rel.parts[0] == "build":
            continue
        if not candidate.is_file() or candidate.is_symlink():
            continue
        try:
            payload = read_json(candidate)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError):
            continue
        if _looks_like_verification_report(payload):
            reports.add(candidate.resolve())

    visual_roots: set[Path] = set()
    for report_path in list(reports):
        if not report_path.is_file() or report_path.is_symlink():
            continue
        try:
            payload = read_json(report_path)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError):
            continue
        if not _looks_like_verification_report(payload):
            continue
        visual = _validated_reference(report_path.parent, payload.get("visual_report"), ".json", "visual")
        if visual is not None:
            visual_roots.add(visual)
    return reports, visual_roots


def bound_source_paths(paper: Path, binding: dict) -> set[Path]:
    """Return paper-relative paths that the binding already classified as source."""
    result: set[Path] = set()
    source = binding.get("source_snapshot")
    if not isinstance(source, dict) or not isinstance(source.get("files"), list):
        raise ValueError("binding source_snapshot.files is missing")
    paper = paper.resolve()
    for row in source["files"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise ValueError("binding source snapshot contains an invalid path row")
        rel = Path(row["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("binding source snapshot contains a non-relative path")
        resolved = (paper / rel).resolve()
        if not resolved.is_relative_to(paper):
            raise ValueError("binding source snapshot escapes paper directory")
        result.add(resolved)
    return result


def review_artifact_paths(
    paper: Path,
    binding_path: Path,
    visual_path: Path | None = None,
    output_report: Path | None = None,
    follow_transitive: bool = True,
    source_guard: set[Path] | None = None,
) -> set[Path]:
    """Return gate/review evidence that may be excluded from a paper-source hash.

    Any candidate already classified as a paper input by the prior/current binding
    is retained as source, even if a review JSON tries to reference it.
    """
    reports, report_visual_roots = discover_verification_reports(paper, output_report)
    roots: set[Path] = {(paper / DEFAULT_VISUAL_REPORT).resolve()} | report_visual_roots
    if visual_path is not None:
        roots.add(visual_path.resolve())

    artifacts: set[Path] = {binding_path.resolve()} | reports | roots
    if follow_transitive:
        artifacts |= visual_evidence_paths(roots)
    if source_guard:
        guarded = {path.resolve() for path in source_guard}
        artifacts = {path for path in artifacts if path.resolve() not in guarded}
    return artifacts


def source_snapshot(paper: Path, excluded: set[Path]) -> dict:
    """Hash paper inputs while excluding compiler outputs and validated review evidence.

    Symlinked paper inputs are rejected rather than silently omitted: otherwise a
    target change after binding could evade the source snapshot.
    """
    excluded = {path.resolve() for path in excluded}
    generated_suffixes = {".aux", ".log", ".out", ".toc", ".blg", ".bbl", ".fls", ".fdb_latexmk"}
    files: list[dict] = []
    for path in sorted(paper.rglob("*"), key=lambda item: item.relative_to(paper).as_posix()):
        rel = path.relative_to(paper)
        if rel.parts and rel.parts[0] == "build":
            continue
        resolved = path.resolve()
        if resolved in excluded:
            continue
        if path.is_symlink():
            raise ValueError(f"symlinked paper input is not supported by visual review snapshot: {rel.as_posix()}")
        if not path.is_file():
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


def _in_build(paper: Path, path: Path) -> bool:
    return path.resolve().is_relative_to((paper / "build").resolve())


def validate_binding_destination(
    paper: Path,
    binding_path: Path,
    compile_report_path: Path,
    pdf: Path,
) -> dict | None:
    if binding_path.suffix.lower() != ".json":
        raise ValueError("visual review binding must be a .json file")
    if binding_path in {compile_report_path, pdf}:
        raise ValueError("visual review binding must not overwrite compile report or published PDF")
    if _in_build(paper, binding_path):
        raise ValueError("visual review binding must be outside the compiler build directory")
    if binding_path.is_symlink():
        raise ValueError("visual review binding destination must not be a symlink")
    if not binding_path.exists():
        return None
    if not binding_path.is_file():
        raise ValueError("visual review binding destination is not a regular file")
    payload = read_json(binding_path)
    if not _looks_like_binding(payload):
        raise ValueError("visual review binding destination collides with an existing non-binding paper artifact")
    return payload


def validate_verification_destination(
    paper: Path,
    output_report: Path,
    protected: set[Path],
) -> None:
    if output_report.suffix.lower() != ".json":
        raise ValueError("visual verification report must be a .json file")
    if _in_build(paper, output_report):
        raise ValueError("visual verification report must be outside the compiler build directory")
    if output_report.resolve() in {path.resolve() for path in protected}:
        raise ValueError("visual verification report path collides with source or review evidence")
    if output_report.is_symlink():
        raise ValueError("visual verification report destination must not be a symlink")
    if not output_report.exists():
        return
    if not output_report.is_file():
        raise ValueError("visual verification report destination is not a regular file")
    payload = read_json(output_report)
    if not _looks_like_verification_report(payload):
        raise ValueError("visual verification report destination collides with an existing non-verification paper artifact")


def prepare(args) -> tuple[int, dict]:
    paper, compile_report_path, pdf, binding_path = resolve_paths(args)
    prior_binding = validate_binding_destination(paper, binding_path, compile_report_path, pdf)
    prior_source = bound_source_paths(paper, prior_binding) if prior_binding is not None else set()
    if binding_path in prior_source:
        raise ValueError("binding destination was previously classified as a paper input")

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
    excluded = {compile_report_path, pdf} | review_artifact_paths(
        paper,
        binding_path,
        follow_transitive=prior_binding is not None,
        source_guard=prior_source,
    )
    snapshot = source_snapshot(paper, excluded)
    binding = {
        "schema_version": "1.0",
        "status": "READY_FOR_VISUAL_REVIEW",
        "paper_dir": str(paper),
        "compile_report": {"file": str(compile_report_path), "sha256": sha256(compile_report_path)},
        "paper_pdf": {"file": str(pdf), "sha256": current_pdf_hash, "page_count": pages},
        "source_snapshot": snapshot,
        "review_artifact_policy": {
            "default_visual_report": DEFAULT_VISUAL_REPORT,
            "default_verification_report": DEFAULT_VERIFICATION_REPORT,
            "binding": binding_path.name,
            "transitive_references_require_type_role_and_hash": True,
        },
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
        "verification_mode": VERIFICATION_MODE,
        "paper_dir": str(paper),
        "status": "UNKNOWN",
    }

    if not binding_path.is_file() or binding_path.is_symlink():
        # The destination is not yet trusted, so only a safe verification-report
        # path may receive this failure result.
        protected = {compile_report_path, pdf, binding_path, visual_path}
        try:
            validate_verification_destination(paper, output_report, protected)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
            result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_MISSING", report_error=str(exc))
            return 2, result
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_MISSING")
        write_json(output_report, result)
        return 2, result

    try:
        binding = read_json(binding_path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        binding = None
        binding_error = str(exc)
    else:
        binding_error = None

    if not isinstance(binding, dict) or not _looks_like_binding(binding):
        protected = {compile_report_path, pdf, binding_path, visual_path}
        try:
            validate_verification_destination(paper, output_report, protected)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
            result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID", error=binding_error, report_error=str(exc))
            return 2, result
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID", error=binding_error)
        write_json(output_report, result)
        return 2, result

    source_guard = bound_source_paths(paper, binding)
    # Protect the current visual report, every validated inherited report/page
    # image, every bound paper source, and the primary compile/PDF/binding inputs.
    review_inputs = visual_evidence_paths({visual_path, (paper / DEFAULT_VISUAL_REPORT).resolve()})
    protected_outputs = {compile_report_path, pdf, binding_path} | review_inputs | source_guard
    try:
        validate_verification_destination(paper, output_report, protected_outputs)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        result.update(status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="OUTPUT_REPORT_PATH_CONFLICT", error=str(exc))
        return 2, result

    def finish(code: int, **updates) -> tuple[int, dict]:
        result.update(updates)
        write_json(output_report, result)
        return code, result

    compile_binding = binding.get("compile_report")
    pdf_binding = binding.get("paper_pdf")
    source_binding = binding.get("source_snapshot")
    if not all(isinstance(item, dict) for item in (compile_binding, pdf_binding, source_binding)):
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID")
    if not compile_report_path.is_file() or sha256(compile_report_path) != compile_binding.get("sha256"):
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="COMPILE_REPORT_CHANGED")
    try:
        recorded_compile_report = _artifact(binding_path.parent, compile_binding.get("file"))
    except ValueError as exc:
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID", error=str(exc))
    if recorded_compile_report != compile_report_path:
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="COMPILE_REPORT_PATH_CHANGED")
    if not pdf.is_file() or pdf.is_symlink():
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="PUBLISHED_PDF_MISSING")
    try:
        recorded_pdf = _artifact(binding_path.parent, pdf_binding.get("file"))
    except ValueError as exc:
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="BINDING_INVALID", error=str(exc))
    if recorded_pdf != pdf or sha256(pdf) != pdf_binding.get("sha256"):
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="PUBLISHED_PDF_CHANGED")

    excluded = {compile_report_path, pdf} | review_artifact_paths(
        paper,
        binding_path,
        visual_path=visual_path,
        output_report=output_report,
        follow_transitive=True,
        source_guard=source_guard,
    )
    current_snapshot = source_snapshot(paper, excluded)
    result["source_snapshot"] = {"expected": source_binding.get("sha256"), "current": current_snapshot["sha256"]}
    if current_snapshot["sha256"] != source_binding.get("sha256"):
        return finish(2, status="VISUAL_VERIFICATION_REQUIRES_RECOMPILE", visual_check_status="SOURCE_SNAPSHOT_CHANGED")

    pages = compile_paper.pdf_page_count(pdf)
    visual_check = compile_paper.check_visual_report(visual_path, pdf, pages)
    result["paper_pdf"] = {"file": str(pdf), "sha256": sha256(pdf), "page_count": pages}
    result["compile_report"] = {"file": str(compile_report_path), "sha256": sha256(compile_report_path)}
    if visual_path.is_file():
        result["visual_report"] = {"file": str(visual_path), "sha256": sha256(visual_path)}
    else:
        result["visual_report"] = {"file": str(visual_path), "sha256": None}
    result["visual_check_details"] = visual_check
    result["visual_check_status"] = visual_check["status"]
    if visual_check["status"] == "PASSED":
        return finish(0, status="PASSED", visual_check_status=f"PASSED_ALL_{pages}_PAGES")
    if visual_check["status"] == "REVIEW_REQUIRED":
        return finish(0, status="COMPILED_PENDING_VISUAL_CHECK")
    return finish(2, status="VISUAL_CHECK_FAILED")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--paper-dir", type=Path, required=True)
        p.add_argument("--compile-report", type=Path, default=Path("compile_report.json"))
        p.add_argument("--output-pdf", type=Path, default=Path("main.pdf"))
        p.add_argument("--binding", type=Path, default=Path(DEFAULT_BINDING))
        if name == "verify":
            p.add_argument("--visual-report", type=Path, required=True)
            p.add_argument("--report", type=Path, default=Path(DEFAULT_VERIFICATION_REPORT))
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = prepare(args) if args.command == "prepare" else verify(args)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError, KeyError, TypeError) as exc:
        code, payload = 2, {"schema_version": "1.0", "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        if args.command == "verify":
            try:
                paper, compile_report, pdf, binding = resolve_paths(args)
                visual = (args.visual_report if args.visual_report.is_absolute() else paper / args.visual_report).resolve()
                report_path = (args.report if args.report.is_absolute() else paper / args.report).resolve()
                direct_protected = {compile_report, pdf, binding, visual}
                if report_path not in direct_protected and report_path.suffix.lower() == ".json":
                    if not report_path.exists():
                        write_json(report_path, {**payload, "verification_mode": VERIFICATION_MODE})
                    elif report_path.is_file() and not report_path.is_symlink():
                        existing = read_json(report_path)
                        if _looks_like_verification_report(existing):
                            write_json(report_path, {**payload, "verification_mode": VERIFICATION_MODE})
            except (OSError, ValueError, json.JSONDecodeError, UnicodeError, TypeError):
                pass
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
