"""Offline citation-key consistency checker for CUMCM LaTeX papers.

It does not invent bibliographic facts or decide whether a source supports a
claim.  Those two checks remain mandatory review tasks and are explicitly
reported as pending when local metadata alone is insufficient.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.I)
CITE_RE = re.compile(r"\\(?:cite|citep|citet|parencite|textcite)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Check LaTeX citation keys against a BibTeX database.")
    ap.add_argument("--tex-dir", type=Path, required=True)
    ap.add_argument("--bib", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("CITATION_AUDIT.json"))
    args = ap.parse_args()
    tex_dir, bib = args.tex_dir.resolve(), args.bib.resolve()
    if not tex_dir.is_dir() or not bib.is_file():
        print("tex directory or bibliography is missing")
        return 2
    bib_text = bib.read_text(encoding="utf-8", errors="replace")
    keys = ENTRY_RE.findall(bib_text)
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    defined = set(keys)
    used: set[str] = set()
    source_files = sorted(tex_dir.rglob("*.tex"))
    for tex in source_files:
        for group in CITE_RE.findall(tex.read_text(encoding="utf-8", errors="replace")):
            used.update(key.strip() for key in group.split(",") if key.strip())
    undefined = sorted(used - defined)
    unused = sorted(defined - used)
    status = "FAILED" if duplicate_keys or undefined else "STRUCTURAL_PASS_REVIEW_REQUIRED"
    report = {
        "status": status,
        "bibliography": str(bib),
        "tex_files": [str(path) for path in source_files],
        "defined_keys": sorted(defined),
        "used_keys": sorted(used),
        "duplicate_keys": duplicate_keys,
        "undefined_citations": undefined,
        "unreferenced_entries": unused,
        "metadata_verification": "REVIEW_REQUIRED",
        "claim_context_verification": "REVIEW_REQUIRED",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 2 if status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
