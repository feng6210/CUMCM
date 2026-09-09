"""Check conservative CUMCM electronic-paper delivery invariants locally.

Competition-ready mode is intentionally strict: a compiled skeleton, placeholder-
filled draft, author-only self-review, stale visual report, or missing support
package must not be reported as a final submission.
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
IDENTITY_TOKENS = ("学号", "姓名", "school", "university", "logo")
FORBIDDEN_TOKENS = ("aris_repo",)
PLACEHOLDER_PATTERNS = (
    r"待填写", r"待补(?:充|写|全)?", r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b",
    r"\bPLACEHOLDER\b", r"\[待.*?\]",
)
REQUIRED_REVIEW_DIMENSIONS = (
    "semantics_math",
    "numbers_claims",
    "figures_evidence",
    "paper_delivery",
)
VISUAL_GATE_PATH = Path(__file__).resolve().with_name("visual_review_gate.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_visual_gate():
    spec = importlib.util.spec_from_file_location("mm_visual_review_gate_for_final_delivery", VISUAL_GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import visual_review_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_text(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ["unreadable"]
    return [token for token in IDENTITY_TOKENS + FORBIDDEN_TOKENS if token.lower() in text]


def strip_tex_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        out: list[str] = []
        for i, char in enumerate(line):
            if char == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            out.append(char)
        lines.append("".join(out))
    return "\n".join(lines)


def placeholder_hits(paper: Path) -> list[dict]:
    hits: list[dict] = []
    for path in sorted(paper.rglob("*.tex")):
        if "build" in path.parts:
            continue
        try:
            text = strip_tex_comments(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            hits.append({"path": str(path.relative_to(paper)), "pattern": "unreadable"})
            continue
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append({"path": str(path.relative_to(paper)), "pattern": pattern})
    return hits


def load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def resolve_artifact(base: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def validate_compile_report(path: Path, pdf: Path) -> tuple[bool, dict]:
    payload = load_json(path)
    if payload is None:
        return False, {"reason": "missing_or_invalid_json"}
    expected = sha256(pdf) if pdf.is_file() else None
    ok = (
        payload.get("pdf_published") is True
        and isinstance(payload.get("pdf_sha256"), str)
        and payload.get("pdf_sha256") == expected
        and payload.get("status") in {"PASSED", "COMPILED_PENDING_VISUAL_CHECK"}
    )
    return ok, {"status": payload.get("status"), "pdf_sha256": payload.get("pdf_sha256"), "expected": expected}


def validate_visual_provenance(
    paper: Path,
    verification_path: Path,
    binding_path: Path,
    compile_report_path: Path,
    pdf: Path,
    post_binding_review_paths: set[Path],
) -> tuple[bool, dict]:
    verification = load_json(verification_path)
    binding = load_json(binding_path)
    if verification is None or binding is None:
        return False, {"reason": "verification_or_binding_missing_or_invalid"}
    if verification.get("verification_mode") != "existing_published_artifact_no_recompile" or verification.get("status") != "PASSED":
        return False, {"reason": "visual_verification_not_gate_pass", "status": verification.get("status")}
    if binding.get("schema_version") != "1.0" or binding.get("status") != "READY_FOR_VISUAL_REVIEW":
        return False, {"reason": "visual_binding_invalid"}
    if not compile_report_path.is_file() or not pdf.is_file():
        return False, {"reason": "compile_report_or_pdf_missing"}

    compile_hash = sha256(compile_report_path)
    pdf_hash = sha256(pdf)
    b_compile = binding.get("compile_report") if isinstance(binding.get("compile_report"), dict) else {}
    b_pdf = binding.get("paper_pdf") if isinstance(binding.get("paper_pdf"), dict) else {}
    if b_compile.get("sha256") != compile_hash or b_pdf.get("sha256") != pdf_hash:
        return False, {"reason": "binding_no_longer_matches_compile_or_pdf"}

    v_compile = verification.get("compile_report") if isinstance(verification.get("compile_report"), dict) else {}
    v_pdf = verification.get("paper_pdf") if isinstance(verification.get("paper_pdf"), dict) else {}
    if v_compile.get("sha256") != compile_hash or v_pdf.get("sha256") != pdf_hash:
        return False, {"reason": "verification_no_longer_matches_compile_or_pdf"}

    visual_row = verification.get("visual_report") if isinstance(verification.get("visual_report"), dict) else {}
    visual_path = resolve_artifact(verification_path.parent, visual_row.get("file"))
    if visual_path is None or not visual_path.is_file() or visual_path.is_symlink() or visual_row.get("sha256") != sha256(visual_path):
        return False, {"reason": "visual_report_artifact_not_hash_bound"}

    gate = load_visual_gate()
    try:
        source_guard = gate.bound_source_paths(paper, binding)
        normalized_post = {path.resolve() for path in post_binding_review_paths}
        if source_guard & normalized_post:
            return False, {"reason": "review_artifact_collides_with_bound_paper_source"}
        prior_reviews = gate.bound_review_artifacts(paper, binding)
        excluded = {
            compile_report_path.resolve(), pdf.resolve(), binding_path.resolve(), verification_path.resolve(), visual_path.resolve(),
        } | set(prior_reviews) | normalized_post
        current_snapshot = gate.source_snapshot(paper, excluded)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, TypeError) as exc:
        return False, {"reason": "visual_gate_revalidation_failed", "error": str(exc)}

    b_source = binding.get("source_snapshot") if isinstance(binding.get("source_snapshot"), dict) else {}
    v_source = verification.get("source_snapshot") if isinstance(verification.get("source_snapshot"), dict) else {}
    expected_source = b_source.get("sha256")
    if current_snapshot.get("sha256") != expected_source:
        return False, {"reason": "paper_source_changed_after_visual_review", "expected": expected_source, "current": current_snapshot.get("sha256")}
    if v_source.get("expected") != expected_source or v_source.get("current") != expected_source:
        return False, {"reason": "verification_source_snapshot_not_bound_to_binding"}
    return True, {
        "verification_mode": verification.get("verification_mode"),
        "paper_pdf_sha256": pdf_hash,
        "compile_report_sha256": compile_hash,
        "source_snapshot_sha256": expected_source,
        "visual_report_sha256": visual_row.get("sha256"),
    }


def submission_digest(pdf: Path, compile_report: Path, visual_verification: Path, binding: Path, support_zip: Path) -> str:
    payload = {
        "pdf_sha256": sha256(pdf),
        "compile_report_sha256": sha256(compile_report),
        "visual_verification_sha256": sha256(visual_verification),
        "visual_binding_sha256": sha256(binding),
        "support_zip_sha256": sha256(support_zip),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_subagent_review(path: Path, paper: Path, expected_digest: str) -> tuple[bool, dict, set[Path]]:
    payload = load_json(path)
    if payload is None:
        return False, {"reason": "missing_or_invalid_json"}, {path.resolve()}
    author = payload.get("author_agent_id")
    reviews = payload.get("reviews")
    if not isinstance(author, str) or not author.strip():
        return False, {"reason": "author_agent_id_required"}, {path.resolve()}
    author_norm = author.strip().casefold()
    if payload.get("status") != "PASSED" or payload.get("competition_submission") is not True or payload.get("submission_digest") != expected_digest:
        return False, {"reason": "summary_not_passed_or_not_bound_to_current_submission"}, {path.resolve()}
    if not isinstance(reviews, list):
        return False, {"reason": "reviews_array_missing"}, {path.resolve()}

    selected: dict[str, dict] = {}
    reviewer_ids: dict[str, str] = {}
    evidence_paths: set[Path] = {path.resolve()}
    duplicate_dimensions: set[str] = set()
    for row in reviews:
        if not isinstance(row, dict):
            continue
        dimension = row.get("dimension")
        if dimension not in REQUIRED_REVIEW_DIMENSIONS:
            continue
        if dimension in selected:
            duplicate_dimensions.add(dimension)
            continue
        selected[dimension] = row

    valid = not duplicate_dimensions and set(selected) == set(REQUIRED_REVIEW_DIMENSIONS)
    for dimension in REQUIRED_REVIEW_DIMENSIONS:
        row = selected.get(dimension)
        if not isinstance(row, dict):
            valid = False
            continue
        reviewer = row.get("reviewer_id")
        reviewer_norm = reviewer.strip().casefold() if isinstance(reviewer, str) else ""
        report_path = resolve_artifact(path.parent, row.get("report_file"))
        report_sha = row.get("report_sha256")
        if not reviewer_norm or reviewer_norm == author_norm or reviewer_norm in reviewer_ids:
            valid = False
        else:
            reviewer_ids[reviewer_norm] = dimension
        if report_path is None or not report_path.is_file() or report_path.is_symlink():
            valid = False
            continue
        evidence_paths.add(report_path.resolve())
        if not isinstance(report_sha, str) or report_sha != sha256(report_path):
            valid = False
            continue
        report = load_json(report_path)
        invocation = report.get("invocation") if isinstance(report, dict) and isinstance(report.get("invocation"), dict) else {}
        if not isinstance(report, dict) or not (
            report.get("status") == "PASSED"
            and report.get("dimension") == dimension
            and isinstance(report.get("reviewer_id"), str)
            and report.get("reviewer_id").strip().casefold() == reviewer_norm
            and report.get("origin") == "subagent"
            and report.get("independent_of_authorship") is True
            and report.get("submission_digest") == expected_digest
            and report.get("blocking_findings") in ([], None)
            and invocation.get("kind") == "subagent"
            and isinstance(invocation.get("run_id"), str)
            and invocation.get("run_id").strip()
        ):
            valid = False
    if payload.get("unresolved_p0_p1") != []:
        valid = False
    return valid, {
        "covered_dimensions": sorted(selected),
        "required_dimensions": sorted(REQUIRED_REVIEW_DIMENSIONS),
        "duplicate_dimensions": sorted(duplicate_dimensions),
        "unique_normalized_subagent_reviewers": sorted(reviewer_ids),
        "unresolved_p0_p1": payload.get("unresolved_p0_p1"),
        "submission_digest": payload.get("submission_digest"),
        "expected_submission_digest": expected_digest,
    }, evidence_paths


def main() -> int:
    ap = argparse.ArgumentParser(description="Check CUMCM paper and support package delivery boundaries.")
    ap.add_argument("--paper-dir", type=Path, required=True)
    ap.add_argument("--output-pdf", type=Path, help="Actual delivered PDF, relative to paper-dir or absolute; default main.pdf")
    ap.add_argument("--support-zip", type=Path)
    ap.add_argument("--output", type=Path, default=Path("FINAL_CHECK.json"))
    ap.add_argument("--competition-ready", action="store_true", help="Require a submission-ready paper, support package, no placeholders, verified PDF provenance, and four distinct provenance-bound subagent reviews.")
    ap.add_argument("--compile-report", type=Path, default=Path("compile_report.json"))
    ap.add_argument("--visual-verification", type=Path, default=Path("visual_verification_report.json"))
    ap.add_argument("--visual-binding", type=Path, default=Path("VISUAL_REVIEW_BINDING.json"))
    ap.add_argument("--subagent-review", type=Path, default=Path("SUBAGENT_REVIEW_SUMMARY.json"))
    args = ap.parse_args()
    paper = args.paper_dir.resolve()
    checks: list[dict] = []
    selected = args.output_pdf if args.output_pdf is not None else Path("main.pdf")
    pdf = (selected if selected.is_absolute() else paper / selected).resolve()
    checks.append({"check": "output_pdf_filename", "passed": pdf.suffix.lower() == ".pdf"})
    checks.append({"check": "main_pdf_exists", "passed": pdf.is_file()})
    if pdf.is_file():
        checks.append({"check": "main_pdf_size_le_20mb", "passed": pdf.stat().st_size <= MAX_BYTES, "bytes": pdf.stat().st_size})
    for path in sorted(paper.rglob("*.tex")):
        hits = scan_text(path)
        checks.append({"check": "source_identity_and_runtime_tokens", "path": str(path.relative_to(paper)), "passed": not hits, "hits": hits})

    archive = args.support_zip.resolve() if args.support_zip else None
    members: list[str] = []
    if archive is not None:
        can_open = False
        try:
            with zipfile.ZipFile(archive) as zf:
                members = zf.namelist()
                can_open = zf.testzip() is None
        except (OSError, zipfile.BadZipFile):
            pass
        checks.extend([
            {"check": "support_zip_exists", "passed": archive.is_file()},
            {"check": "support_zip_size_le_20mb", "passed": archive.is_file() and archive.stat().st_size <= MAX_BYTES, "bytes": archive.stat().st_size if archive.is_file() else None},
            {"check": "support_zip_reopens", "passed": can_open},
            {"check": "support_zip_nonempty", "passed": bool(members), "members": members},
        ])

    competition_details: dict | None = None
    if args.competition_ready:
        placeholders = placeholder_hits(paper)
        checks.append({"check": "no_template_or_todo_placeholders", "passed": not placeholders, "hits": placeholders})
        checks.append({"check": "support_zip_required_for_competition", "passed": archive is not None and archive.is_file() and bool(members)})

        compile_report = (args.compile_report if args.compile_report.is_absolute() else paper / args.compile_report).resolve()
        visual_report = (args.visual_verification if args.visual_verification.is_absolute() else paper / args.visual_verification).resolve()
        binding = (args.visual_binding if args.visual_binding.is_absolute() else paper / args.visual_binding).resolve()
        subagent_report = (args.subagent_review if args.subagent_review.is_absolute() else paper / args.subagent_review).resolve()

        compile_ok, compile_details = validate_compile_report(compile_report, pdf)
        checks.append({"check": "compile_report_binds_published_pdf", "passed": compile_ok, "details": compile_details})

        digest_ready = all(path.is_file() for path in (pdf, compile_report, visual_report, binding)) and archive is not None and archive.is_file()
        digest = submission_digest(pdf, compile_report, visual_report, binding, archive) if digest_ready else None
        subagent_ok, subagent_details, subagent_paths = (
            validate_subagent_review(subagent_report, paper, digest) if isinstance(digest, str)
            else (False, {"reason": "submission_digest_inputs_missing"}, {subagent_report})
        )
        visual_ok, visual_details = validate_visual_provenance(
            paper, visual_report, binding, compile_report, pdf, subagent_paths,
        ) if compile_ok else (False, {"reason": "compile_report_not_valid"})
        checks.extend([
            {"check": "visual_verification_and_binding_match_current_submission", "passed": visual_ok, "details": visual_details},
            {"check": "four_distinct_provenance_bound_subagent_reviews_pass", "passed": subagent_ok, "details": subagent_details},
        ])
        competition_details = {
            "mode": "competition_ready",
            "compile_report": str(compile_report),
            "visual_verification": str(visual_report),
            "visual_binding": str(binding),
            "subagent_review": str(subagent_report),
            "submission_digest": digest,
            "skeleton_or_placeholder_delivery_allowed": False,
            "author_only_self_review_allowed": False,
        }

    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "checks": checks,
        "verification_scope": "competition_submission_gate" if args.competition_ready else "structural_delivery_checks_only",
        "pdf_path": str(pdf),
        "pdf_sha256": sha256(pdf) if pdf.is_file() else None,
        "support_zip_verification": "container_readability_only" if archive else "not_requested",
        "source_package_recompiled": False,
        "experiment_reproduced": False,
        "competition_ready": competition_details,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
