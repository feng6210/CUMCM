"""Check conservative CUMCM electronic-paper delivery invariants locally.

Competition-ready mode is intentionally strict: a compiled skeleton, placeholder-
filled draft, author-only self-review, stale PDF, or missing support package must
not be reported as a final submission.
"""
from __future__ import annotations

import argparse
import hashlib
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
REQUIRED_REVIEW_DIMENSIONS = {
    "semantics_math",
    "numbers_claims",
    "figures_evidence",
    "paper_delivery",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            out.append(line[i])
            i += 1
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


def validate_subagent_review(path: Path) -> tuple[bool, dict]:
    payload = load_json(path)
    if payload is None:
        return False, {"reason": "missing_or_invalid_json"}
    reviews = payload.get("reviews")
    if payload.get("status") != "PASSED" or payload.get("competition_submission") is not True:
        return False, {"reason": "summary_not_passed_for_competition"}
    if not isinstance(reviews, list):
        return False, {"reason": "reviews_array_missing"}
    by_dimension: dict[str, dict] = {}
    reviewer_ids: set[str] = set()
    author = payload.get("author_agent_id")
    for row in reviews:
        if not isinstance(row, dict):
            continue
        dimension = row.get("dimension")
        reviewer = row.get("reviewer_id")
        if dimension not in REQUIRED_REVIEW_DIMENSIONS:
            continue
        if (
            row.get("origin") != "subagent"
            or row.get("independent_of_authorship") is not True
            or row.get("status") != "PASSED"
            or not isinstance(reviewer, str)
            or not reviewer.strip()
            or reviewer == author
            or row.get("blocking_findings") not in ([], None)
        ):
            continue
        by_dimension[dimension] = row
        reviewer_ids.add(reviewer)
    unresolved = payload.get("unresolved_p0_p1")
    ok = (
        set(by_dimension) == REQUIRED_REVIEW_DIMENSIONS
        and len(reviewer_ids) == len(REQUIRED_REVIEW_DIMENSIONS)
        and unresolved == []
    )
    return ok, {
        "covered_dimensions": sorted(by_dimension),
        "required_dimensions": sorted(REQUIRED_REVIEW_DIMENSIONS),
        "unique_subagent_reviewers": sorted(reviewer_ids),
        "unresolved_p0_p1": unresolved,
    }


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


def validate_visual_verification(path: Path, pdf: Path) -> tuple[bool, dict]:
    payload = load_json(path)
    if payload is None:
        return False, {"reason": "missing_or_invalid_json"}
    expected = sha256(pdf) if pdf.is_file() else None
    paper_pdf = payload.get("paper_pdf") if isinstance(payload.get("paper_pdf"), dict) else {}
    ok = payload.get("status") == "PASSED" and paper_pdf.get("sha256") == expected
    return ok, {"status": payload.get("status"), "paper_pdf_sha256": paper_pdf.get("sha256"), "expected": expected}


def main() -> int:
    ap = argparse.ArgumentParser(description="Check CUMCM paper and support package delivery boundaries.")
    ap.add_argument("--paper-dir", type=Path, required=True)
    ap.add_argument("--output-pdf", type=Path, help="Actual delivered PDF, relative to paper-dir or absolute; default main.pdf")
    ap.add_argument("--support-zip", type=Path)
    ap.add_argument("--output", type=Path, default=Path("FINAL_CHECK.json"))
    ap.add_argument("--competition-ready", action="store_true", help="Require a submission-ready paper, support package, no placeholders, verified PDF, and four distinct subagent review lines.")
    ap.add_argument("--compile-report", type=Path, default=Path("compile_report.json"))
    ap.add_argument("--visual-verification", type=Path, default=Path("visual_verification_report.json"))
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
    if archive is not None:
        can_open = False
        members: list[str] = []
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
        checks.append({"check": "support_zip_required_for_competition", "passed": archive is not None and archive.is_file()})

        compile_report = args.compile_report if args.compile_report.is_absolute() else paper / args.compile_report
        visual_report = args.visual_verification if args.visual_verification.is_absolute() else paper / args.visual_verification
        subagent_report = args.subagent_review if args.subagent_review.is_absolute() else paper / args.subagent_review
        compile_ok, compile_details = validate_compile_report(compile_report.resolve(), pdf)
        visual_ok, visual_details = validate_visual_verification(visual_report.resolve(), pdf)
        subagent_ok, subagent_details = validate_subagent_review(subagent_report.resolve())
        checks.extend([
            {"check": "compile_report_binds_published_pdf", "passed": compile_ok, "details": compile_details},
            {"check": "visual_verification_passes_same_pdf", "passed": visual_ok, "details": visual_details},
            {"check": "four_distinct_subagent_reviews_pass", "passed": subagent_ok, "details": subagent_details},
        ])
        competition_details = {
            "mode": "competition_ready",
            "compile_report": str(compile_report.resolve()),
            "visual_verification": str(visual_report.resolve()),
            "subagent_review": str(subagent_report.resolve()),
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
