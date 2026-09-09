#!/usr/bin/env python3
"""Fail-closed gate for a competition-ready CUMCM submission package.

A compiled skeleton is not a submission. This gate requires a complete question
coverage manifest, no template placeholders in source or rendered PDF, current
compile/visual bindings, five fresh subagent reviews, and a real support ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
PLACEHOLDER_PATTERNS = (
    re.compile(r"待填写"), re.compile(r"待补(?:充|全|写|完善)?"),
    re.compile(r"\bTODO\b", re.IGNORECASE), re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE), re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
    re.compile(r"\bTO\s+FILL\b", re.IGNORECASE), re.compile(r"INSERT\s+HERE", re.IGNORECASE),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON object required")
    return value


def resolve(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("artifact file must be a non-empty string")
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def artifact_ok(base: Path, row: object) -> tuple[bool, str]:
    if not isinstance(row, dict):
        return False, "artifact row is not an object"
    try:
        path = resolve(base, row.get("file"))
    except ValueError as exc:
        return False, str(exc)
    if not path.is_file() or path.is_symlink():
        return False, f"artifact missing/not regular: {path}"
    if sha256(path).lower() != str(row.get("sha256", "")).lower():
        return False, f"artifact hash mismatch: {path}"
    return True, str(path)


def placeholder_hits(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append(match.group(0))
    return sorted(set(hits))


def source_placeholder_checks(paper: Path) -> list[dict]:
    checks: list[dict] = []
    files = [p for p in paper.rglob("*") if p.is_file() and "build" not in p.parts
             and p.suffix.lower() in {".tex", ".bib"}]
    if not files:
        return [{"check": "paper_source_exists", "passed": False, "reason": "no .tex/.bib source files"}]
    for path in sorted(files):
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = placeholder_hits(text)
        checks.append({"check": "no_source_placeholders", "path": str(path.relative_to(paper)),
                       "passed": not hits, "hits": hits})
    return checks


def pdf_text_and_pages(pdf: Path) -> tuple[str, int]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError("pypdfium2 is required for final PDF text/page verification") from exc
    doc = pdfium.PdfDocument(pdf)
    texts: list[str] = []
    try:
        for index in range(len(doc)):
            page = doc[index]
            try:
                textpage = page.get_textpage()
                try:
                    texts.append(textpage.get_text_range())
                finally:
                    textpage.close()
            finally:
                page.close()
        return "\n".join(texts), len(doc)
    finally:
        doc.close()


def normalized_question_ids(value: object, source: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty list")
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            qid = item.get("question_id", item.get("id"))
            if isinstance(qid, str) and qid.strip():
                result.append(qid.strip())
            else:
                raise ValueError(f"{source} objects require question_id or id")
        else:
            raise ValueError(f"{source} entries must be strings or objects")
    if len(result) != len(set(result)):
        raise ValueError(f"duplicate question ids in {source}")
    return result


def load_subagent_validator():
    package = Path(__file__).resolve().parents[3]
    script = package / "skills" / "math-modeling-orchestrator" / "scripts" / "subagent_review_gate.py"
    spec = importlib.util.spec_from_file_location("submission_subagent_gate", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load subagent review gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_submission(paper: Path, state_path: Path, manifest_path: Path,
                     subagent_manifest_path: Path, compile_report_path: Path,
                     visual_report_path: Path, support_zip: Path) -> dict:
    paper = paper.resolve(); state_path = state_path.resolve(); manifest_path = manifest_path.resolve()
    subagent_manifest_path = subagent_manifest_path.resolve(); compile_report_path = compile_report_path.resolve()
    visual_report_path = visual_report_path.resolve(); support_zip = support_zip.resolve()
    state = load_json(state_path); manifest = load_json(manifest_path); checks: list[dict] = []

    checks.append({"check": "deliverable_mode_submission_package", "passed": state.get("deliverable_mode") == "submission_package"})
    checks.append({"check": "workflow_evidence_pass", "passed": state.get("evidence_status") == "PASS", "value": state.get("evidence_status")})
    checks.append({"check": "result_to_claim_yes", "passed": state.get("result_to_claim_status") == "YES", "value": state.get("result_to_claim_status")})
    checks.append({"check": "manifest_ready", "passed": manifest.get("schema_version") == "1.0" and manifest.get("status") == "READY" and manifest.get("deliverable_mode") == "submission_package"})

    manifest_base = manifest_path.parent
    decomposition_ok, decomposition_detail = artifact_ok(manifest_base, manifest.get("question_decomposition"))
    checks.append({"check": "question_decomposition_hash", "passed": decomposition_ok, "detail": decomposition_detail})
    decomposition_path = resolve(manifest_base, manifest.get("question_decomposition", {}).get("file")) if decomposition_ok else None
    authoritative_questions: list[str] = []
    if decomposition_path is not None:
        try:
            decomposition = load_json(decomposition_path)
            field = manifest.get("expected_question_ids_field")
            authoritative_questions = normalized_question_ids(decomposition.get(field), f"QUESTION_DECOMPOSITION.{field}")
            checks.append({"check": "authoritative_question_list", "passed": field == "expected_question_ids",
                           "questions": authoritative_questions})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            checks.append({"check": "authoritative_question_list", "passed": False, "error": str(exc)})

    try:
        state_questions = normalized_question_ids(state.get("problem_parts"), "workflow_state.problem_parts")
    except ValueError as exc:
        state_questions = []
        checks.append({"check": "workflow_problem_parts_match_decomposition", "passed": False, "error": str(exc)})
    else:
        checks.append({"check": "workflow_problem_parts_match_decomposition",
                       "passed": bool(authoritative_questions) and state_questions == authoritative_questions,
                       "state": state_questions, "authoritative": authoritative_questions})

    paper_ok, paper_value = artifact_ok(manifest_base, manifest.get("paper_pdf"))
    checks.append({"check": "manifest_paper_pdf_hash", "passed": paper_ok, "detail": paper_value})
    pdf = resolve(manifest_base, manifest.get("paper_pdf", {}).get("file")) if paper_ok else (paper / "main.pdf")
    checks.append({"check": "paper_pdf_under_20mb", "passed": pdf.is_file() and pdf.stat().st_size <= MAX_BYTES,
                   "bytes": pdf.stat().st_size if pdf.is_file() else None})

    zip_ok, zip_value = artifact_ok(manifest_base, manifest.get("support_zip"))
    checks.append({"check": "manifest_support_zip_hash", "passed": zip_ok, "detail": zip_value})
    declared_zip = resolve(manifest_base, manifest.get("support_zip", {}).get("file")) if zip_ok else support_zip
    checks.append({"check": "support_zip_argument_matches_manifest", "passed": declared_zip == support_zip})
    zip_members: list[str] = []; zip_reopens = False
    try:
        with zipfile.ZipFile(support_zip) as archive:
            zip_members = archive.namelist(); zip_reopens = archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        pass
    checks.extend([
        {"check": "support_zip_exists_nonempty", "passed": support_zip.is_file() and bool(zip_members)},
        {"check": "support_zip_reopens", "passed": zip_reopens},
        {"check": "support_zip_under_20mb", "passed": support_zip.is_file() and support_zip.stat().st_size <= MAX_BYTES,
         "bytes": support_zip.stat().st_size if support_zip.is_file() else None},
    ])

    checks.extend(source_placeholder_checks(paper))
    if pdf.is_file():
        try:
            pdf_text, pages = pdf_text_and_pages(pdf); hits = placeholder_hits(pdf_text)
            checks.append({"check": "final_pdf_text_reopens", "passed": pages > 0, "pages": pages})
            checks.append({"check": "no_pdf_placeholders", "passed": not hits, "hits": hits})
        except (OSError, RuntimeError, ValueError) as exc:
            checks.append({"check": "final_pdf_text_reopens", "passed": False, "error": str(exc)})
    else:
        checks.append({"check": "final_pdf_text_reopens", "passed": False, "error": "final PDF missing"})

    all_tex = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                        for path in paper.rglob("*.tex") if "build" not in path.parts)
    completion = manifest.get("question_completion"); completion = completion if isinstance(completion, list) else []
    by_id = {row.get("question_id"): row for row in completion if isinstance(row, dict) and isinstance(row.get("question_id"), str)}
    checks.append({"check": "all_problem_parts_declared_complete",
                   "passed": bool(authoritative_questions) and set(by_id) == set(authoritative_questions),
                   "expected": authoritative_questions, "declared": sorted(by_id)})
    for qid in authoritative_questions:
        row = by_id.get(qid, {}); label = row.get("paper_label")
        label_count = len(re.findall(r"\\label\{" + re.escape(str(label)) + r"\}", all_tex)) if isinstance(label, str) and label else 0
        result_rows = row.get("result_artifacts") if isinstance(row.get("result_artifacts"), list) else []
        validation_rows = row.get("validation_artifacts") if isinstance(row.get("validation_artifacts"), list) else []
        result_checks = [artifact_ok(manifest_base, item)[0] for item in result_rows]
        validation_checks = [artifact_ok(manifest_base, item)[0] for item in validation_rows]
        checks.extend([
            {"check": "question_status_pass", "question_id": qid, "passed": row.get("status") == "PASS"},
            {"check": "question_paper_anchor_unique", "question_id": qid, "passed": label_count == 1, "paper_label": label, "occurrences": label_count},
            {"check": "question_result_evidence", "question_id": qid, "passed": bool(result_rows) and all(result_checks)},
            {"check": "question_validation_evidence", "question_id": qid, "passed": bool(validation_rows) and all(validation_checks)},
        ])

    compile_report = load_json(compile_report_path)
    compile_hash_ok = pdf.is_file() and str(compile_report.get("pdf_sha256", "")).lower() == sha256(pdf).lower()
    checks.extend([
        {"check": "compile_report_published", "passed": compile_report.get("pdf_published") is True},
        {"check": "compile_report_bound_to_final_pdf", "passed": compile_hash_ok},
        {"check": "compile_report_not_failed", "passed": compile_report.get("status") in {"COMPILED_PENDING_VISUAL_CHECK", "PASSED"}},
    ])

    visual = load_json(visual_report_path); visual_pdf = visual.get("paper_pdf") if isinstance(visual.get("paper_pdf"), dict) else {}
    visual_hash = visual_pdf.get("sha256", visual.get("paper_sha256"))
    visual_compile = visual.get("compile_report") if isinstance(visual.get("compile_report"), dict) else {}
    try:
        visual_compile_path = resolve(visual_report_path.parent, visual_compile.get("file"))
    except ValueError:
        visual_compile_path = None
    checks.extend([
        {"check": "visual_verification_pass", "passed": visual.get("status") == "PASSED"},
        {"check": "visual_verification_bound_to_final_pdf", "passed": pdf.is_file() and str(visual_hash or "").lower() == sha256(pdf).lower()},
        {"check": "visual_verification_no_recompile_mode", "passed": visual.get("verification_mode") == "existing_published_artifact_no_recompile"},
        {"check": "visual_verification_bound_to_compile_report",
         "passed": visual_compile_path == compile_report_path and str(visual_compile.get("sha256", "")).lower() == sha256(compile_report_path).lower()},
    ])

    try:
        subagent_report = load_subagent_validator().validate_manifest(subagent_manifest_path)
        subagent_pass = subagent_report.get("status") == "PASS" and subagent_report.get("distinct_subagents", 0) >= 5
        checks.append({"check": "five_fresh_subagent_reviews", "passed": subagent_pass,
                       "distinct_subagents": subagent_report.get("distinct_subagents")})
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        checks.append({"check": "five_fresh_subagent_reviews", "passed": False, "error": str(exc)})

    passed = all(check.get("passed") is True for check in checks)
    return {
        "schema_version": "1.0", "status": "PASS" if passed else "FAIL", "competition_ready": passed,
        "checks": checks,
        "paper_dir": str(paper),
        "paper_pdf": str(pdf), "paper_pdf_sha256": sha256(pdf) if pdf.is_file() else None,
        "support_zip": str(support_zip), "support_zip_sha256": sha256(support_zip) if support_zip.is_file() else None,
        "workflow_state": str(state_path), "workflow_state_sha256_at_gate": sha256(state_path),
        "question_decomposition": str(decomposition_path) if decomposition_path else None,
        "question_decomposition_sha256": sha256(decomposition_path) if decomposition_path and decomposition_path.is_file() else None,
        "submission_manifest": str(manifest_path), "submission_manifest_sha256": sha256(manifest_path),
        "subagent_manifest": str(subagent_manifest_path), "subagent_manifest_sha256": sha256(subagent_manifest_path),
        "compile_report": str(compile_report_path), "compile_report_sha256": sha256(compile_report_path),
        "visual_verification_report": str(visual_report_path), "visual_verification_report_sha256": sha256(visual_report_path),
        "placeholder_gate": "zero_tolerance", "subagent_gate": "five_distinct_fresh_subagents_required",
        "completion_rule": "COMPLETE is forbidden unless this report is PASS and remains hash-current",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-dir", type=Path, required=True)
    parser.add_argument("--workflow-state", type=Path, required=True)
    parser.add_argument("--submission-manifest", type=Path, required=True)
    parser.add_argument("--subagent-manifest", type=Path, required=True)
    parser.add_argument("--compile-report", type=Path, required=True)
    parser.add_argument("--visual-verification-report", type=Path, required=True)
    parser.add_argument("--support-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("FINAL_SUBMISSION_GATE.json"))
    args = parser.parse_args()
    try:
        report = check_submission(args.paper_dir, args.workflow_state, args.submission_manifest,
                                  args.subagent_manifest, args.compile_report, args.visual_verification_report,
                                  args.support_zip)
        code = 0 if report["status"] == "PASS" else 2
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        report = {"schema_version": "1.0", "status": "FAIL", "competition_ready": False,
                  "error": f"{type(exc).__name__}: {exc}"}; code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return code


if __name__ == "__main__":
    raise SystemExit(main())
