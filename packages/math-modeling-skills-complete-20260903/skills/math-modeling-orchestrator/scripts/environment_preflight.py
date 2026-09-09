#!/usr/bin/env python3
"""Task-aware environment preflight for the math-modeling submission workflow.

This script is intentionally read-only with respect to the host environment. It
never installs software. For ``submission_package`` it fail-closes unless the
full local paper toolchain is present before substantive work starts.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

PYTHON_MODULES = {
    "yaml": "PyYAML",
    "jsonschema": "jsonschema",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "PIL": "Pillow",
    "pypdfium2": "pypdfium2",
    "scipy": "scipy",
    "sklearn": "scikit-learn",
    "networkx": "networkx",
    "openpyxl": "openpyxl",
}
PAPER_BINARIES = ("xelatex", "latexmk", "bibtex", "pdftoppm")
PROFILES = ("analysis", "figures", "cumcm_latex_paper", "submission_package")


def available_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def probe(profile: str) -> dict:
    python_ok = sys.version_info >= (3, 10)
    modules = {name: available_module(name) for name in PYTHON_MODULES}
    binaries = {name: shutil.which(name) for name in PAPER_BINARIES}

    numeric_ready = python_ok and all(modules[name] for name in (
        "yaml", "jsonschema", "numpy", "pandas", "scipy", "sklearn", "networkx", "openpyxl"
    ))
    rendering_ready = numeric_ready and all(modules[name] for name in (
        "matplotlib", "PIL", "pypdfium2"
    ))
    latex_ready = all(bool(binaries[name]) for name in ("xelatex", "latexmk", "bibtex"))
    paper_review_ready = bool(binaries["pdftoppm"])

    if profile == "analysis":
        required_ready = numeric_ready
    elif profile == "figures":
        required_ready = rendering_ready
    elif profile == "cumcm_latex_paper":
        required_ready = rendering_ready and latex_ready
    else:
        required_ready = rendering_ready and latex_ready and paper_review_ready

    missing: list[str] = []
    if not python_ok:
        missing.append("python>=3.10")
    if profile in {"analysis", "figures", "cumcm_latex_paper", "submission_package"}:
        missing.extend(PYTHON_MODULES[name] for name, ok in modules.items()
                       if not ok and (profile != "analysis" or name not in {"matplotlib", "PIL", "pypdfium2"}))
    if profile in {"cumcm_latex_paper", "submission_package"}:
        missing.extend(name for name in ("xelatex", "latexmk", "bibtex") if not binaries[name])
    if profile == "submission_package" and not binaries["pdftoppm"]:
        missing.append("pdftoppm")

    return {
        "schema_version": "1.0",
        "profile": profile,
        "status": "PASS" if required_ready else "FAIL",
        "full_submission_ready": bool(profile == "submission_package" and required_ready),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "ready": python_ok,
        },
        "modules": {name: {"distribution": PYTHON_MODULES[name], "ready": ok}
                    for name, ok in modules.items()},
        "capabilities": {
            "numeric": numeric_ready,
            "deterministic_rendering": rendering_ready,
            "latex_compile": latex_ready,
            "paper_page_rendering": paper_review_ready,
        },
        "binaries": binaries,
        "missing": sorted(set(missing)),
        "installation_performed": False,
        "note": "Read-only preflight. Missing dependencies must be resolved explicitly, then preflight rerun.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="submission_package")
    parser.add_argument("--output", type=Path, default=Path("ENVIRONMENT_PREFLIGHT.json"))
    args = parser.parse_args()
    report = probe(args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
