"""Check conservative CUMCM electronic-paper delivery invariants locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


MAX_BYTES = 20 * 1024 * 1024
IDENTITY_TOKENS = ("学号", "姓名", "school", "university", "logo")
# These are workflow-control residue, not ordinary source citations.  A paper may
# legitimately cite a public software site, so the word "GitHub" itself is not
# prohibited.
FORBIDDEN_TOKENS = ("aris_repo",)


def scan_text(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ["unreadable"]
    return [token for token in IDENTITY_TOKENS + FORBIDDEN_TOKENS if token.lower() in text]


def main() -> int:
    ap = argparse.ArgumentParser(description="Check CUMCM paper and support package delivery boundaries.")
    ap.add_argument("--paper-dir", type=Path, required=True)
    ap.add_argument("--output-pdf", type=Path, help="Actual delivered PDF, relative to paper-dir or absolute; default main.pdf")
    ap.add_argument("--support-zip", type=Path)
    ap.add_argument("--output", type=Path, default=Path("FINAL_CHECK.json"))
    args = ap.parse_args()
    paper = args.paper_dir.resolve()
    checks: list[dict] = []
    selected = args.output_pdf if args.output_pdf is not None else Path("main.pdf")
    pdf = (selected if selected.is_absolute() else paper / selected).resolve()
    checks.append({"check": "output_pdf_filename", "passed": pdf.suffix.lower() == ".pdf"})
    checks.append({"check": "main_pdf_exists", "passed": pdf.is_file()})
    if pdf.is_file():
        checks.append({"check": "main_pdf_size_le_20mb", "passed": pdf.stat().st_size <= MAX_BYTES, "bytes": pdf.stat().st_size})
    # Bibliography author/institution metadata is not an authorship declaration
    # of the contest team.  It is checked separately by the citation auditor.
    for path in sorted(paper.rglob("*.tex")):
        hits = scan_text(path)
        checks.append({"check": "source_identity_and_runtime_tokens", "path": str(path.relative_to(paper)), "passed": not hits, "hits": hits})
    if args.support_zip:
        archive = args.support_zip.resolve()
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
    report = {"status": "PASS" if all(c["passed"] for c in checks) else "FAIL", "checks": checks,
              "verification_scope": "structural_delivery_checks_only",
              "pdf_path": str(pdf),
              "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.is_file() else None,
              "support_zip_verification": "container_readability_only" if args.support_zip else "not_requested",
              "source_package_recompiled": False,
              "experiment_reproduced": False}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
