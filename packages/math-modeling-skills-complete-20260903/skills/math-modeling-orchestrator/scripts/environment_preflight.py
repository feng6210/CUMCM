#!/usr/bin/env python3
"""Task-aware environment preflight for the math-modeling submission workflow.

The preflight is read-only with respect to installed software: it never installs
packages or mutates application settings. It may compile a tiny disposable TeX
fixture inside a temporary directory to prove the current host can actually
render the Chinese/TikZ paper stack required by ``submission_package``.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON_REQUIREMENTS = {
    "yaml": ("PyYAML", "6.0"),
    "jsonschema": ("jsonschema", "4.23"),
    "numpy": ("numpy", "1.26"),
    "pandas": ("pandas", "2.0"),
    "matplotlib": ("matplotlib", "3.8"),
    "PIL": ("Pillow", "10.0"),
    "pypdfium2": ("pypdfium2", "4.30"),
    "scipy": ("scipy", "1.11"),
    "sklearn": ("scikit-learn", "1.4"),
    "networkx": ("networkx", "3.2"),
    "openpyxl": ("openpyxl", "3.1"),
}
PAPER_BINARIES = ("xelatex", "latexmk", "bibtex", "pdftoppm")
PROFILES = ("analysis", "figures", "cumcm_latex_paper", "submission_package")
CJK_FONT_CANDIDATES = (
    "Noto Sans CJK SC", "Noto Serif CJK SC", "Source Han Sans SC", "Source Han Serif SC",
    "Microsoft YaHei", "SimHei", "SimSun", "PingFang SC", "WenQuanYi Zen Hei",
)


def _release_tuple(value: str) -> tuple[int, ...]:
    """Compare stable minimum versions without adding a packaging dependency."""
    numbers = re.findall(r"\d+", value)
    return tuple(int(part) for part in numbers[:4]) if numbers else (0,)


def _version_at_least(actual: str, minimum: str) -> bool:
    left = _release_tuple(actual)
    right = _release_tuple(minimum)
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) >= right + (0,) * (width - len(right))


def module_probe(module_name: str, distribution: str, minimum: str) -> dict:
    try:
        importable = importlib.util.find_spec(module_name) is not None
    except (ImportError, AttributeError, ValueError):
        importable = False
    version = None
    if importable:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            importable = False
    ready = bool(importable and isinstance(version, str) and _version_at_least(version, minimum))
    return {
        "distribution": distribution,
        "minimum": minimum,
        "version": version,
        "importable": importable,
        "ready": ready,
    }


def cjk_font_probe(modules: dict[str, dict]) -> dict:
    if not modules.get("matplotlib", {}).get("ready"):
        return {"ready": False, "font": None, "reason": "matplotlib unavailable"}
    try:
        from matplotlib import font_manager
        installed = {font.name for font in font_manager.fontManager.ttflist}
    except Exception as exc:  # backend/font-cache failures must fail closed for submission rendering
        return {"ready": False, "font": None, "reason": f"font probe failed: {type(exc).__name__}: {exc}"}
    for candidate in CJK_FONT_CANDIDATES:
        if candidate in installed:
            return {"ready": True, "font": candidate}
    return {"ready": False, "font": None, "reason": "no approved CJK font family found"}


def _run(command: list[str], cwd: Path, timeout: int = 45) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def latex_smoke_probe(binaries: dict[str, str | None]) -> dict:
    xelatex = binaries.get("xelatex")
    pdftoppm = binaries.get("pdftoppm")
    if not xelatex:
        return {"ready": False, "compiled": False, "page_rendered": False, "reason": "xelatex missing"}
    fixture = r"""\documentclass[UTF8,a4paper]{ctexart}
\usepackage{amsmath,booktabs,longtable,graphicx,tikz}
\begin{document}
中文环境预检 $E=mc^2$。
\begin{tikzpicture}\draw[->] (0,0)--(1,0);\node at (.5,.25){测试};\end{tikzpicture}
\end{document}
"""
    with tempfile.TemporaryDirectory(prefix="cumcm-preflight-") as tmp:
        root = Path(tmp)
        (root / "preflight.tex").write_text(fixture, encoding="utf-8")
        try:
            version_proc = _run([xelatex, "--version"], root, timeout=20)
            version_text = (version_proc.stdout + version_proc.stderr)[:1200]
            command = [xelatex]
            if "MiKTeX" in version_text:
                command.append("--disable-installer")
            command.extend([
                "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error",
                "preflight.tex",
            ])
            compiled = _run(command, root)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ready": False, "compiled": False, "page_rendered": False,
                    "reason": f"XeLaTeX smoke test failed to run: {type(exc).__name__}: {exc}"}
        pdf = root / "preflight.pdf"
        if compiled.returncode != 0 or not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
            tail = (compiled.stdout + "\n" + compiled.stderr)[-1600:]
            return {"ready": False, "compiled": False, "page_rendered": False,
                    "reason": "XeLaTeX Chinese/TikZ fixture did not compile", "log_tail": tail}

        page_rendered = False
        render_reason = None
        if pdftoppm:
            try:
                rendered = _run([
                    pdftoppm, "-f", "1", "-singlefile", "-png", "-r", "72",
                    str(pdf), str(root / "preview"),
                ], root)
                page_rendered = rendered.returncode == 0 and (root / "preview.png").is_file()
                if not page_rendered:
                    render_reason = (rendered.stdout + "\n" + rendered.stderr)[-800:]
            except (OSError, subprocess.TimeoutExpired) as exc:
                render_reason = f"pdftoppm smoke test failed: {type(exc).__name__}: {exc}"
        else:
            render_reason = "pdftoppm missing"
        return {
            "ready": bool(page_rendered),
            "compiled": True,
            "page_rendered": page_rendered,
            "xelatex_version": version_text.splitlines()[0] if version_text.strip() else None,
            "reason": render_reason,
            "fixture": "ctexart + amsmath + booktabs + longtable + graphicx + tikz",
            "automatic_installation": False,
        }


def probe(profile: str) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    python_ok = sys.version_info >= (3, 10)
    modules = {
        name: module_probe(name, distribution, minimum)
        for name, (distribution, minimum) in PYTHON_REQUIREMENTS.items()
    }
    binaries = {name: shutil.which(name) for name in PAPER_BINARIES}
    cjk_font = cjk_font_probe(modules)

    numeric_names = ("yaml", "jsonschema", "numpy", "pandas", "scipy", "sklearn", "networkx", "openpyxl")
    numeric_ready = python_ok and all(modules[name]["ready"] for name in numeric_names)
    rendering_ready = numeric_ready and all(modules[name]["ready"] for name in ("matplotlib", "PIL", "pypdfium2")) and cjk_font["ready"]
    latex_binary_ready = all(bool(binaries[name]) for name in ("xelatex", "latexmk", "bibtex"))
    page_binary_ready = bool(binaries["pdftoppm"])
    need_latex = profile in {"cumcm_latex_paper", "submission_package"}
    latex_smoke = latex_smoke_probe(binaries) if need_latex else {"ready": None, "compiled": None, "page_rendered": None}
    latex_ready = latex_binary_ready and (latex_smoke.get("compiled") is True if need_latex else True)
    paper_review_ready = page_binary_ready and (latex_smoke.get("page_rendered") is True if need_latex else True)

    if profile == "analysis":
        required_ready = numeric_ready
    elif profile == "figures":
        required_ready = rendering_ready
    elif profile == "cumcm_latex_paper":
        required_ready = rendering_ready and latex_ready
    else:
        required_ready = rendering_ready and latex_ready and paper_review_ready and latex_smoke.get("ready") is True

    missing: list[str] = []
    if not python_ok:
        missing.append("python>=3.10")
    required_modules = set(numeric_names)
    if profile in {"figures", "cumcm_latex_paper", "submission_package"}:
        required_modules.update(("matplotlib", "PIL", "pypdfium2"))
    for name in sorted(required_modules):
        if not modules[name]["ready"]:
            distribution, minimum = PYTHON_REQUIREMENTS[name]
            actual = modules[name]["version"]
            missing.append(f"{distribution}>={minimum}" + (f" (found {actual})" if actual else ""))
    if profile in {"figures", "cumcm_latex_paper", "submission_package"} and not cjk_font["ready"]:
        missing.append("CJK font for deterministic figures")
    if need_latex:
        missing.extend(name for name in ("xelatex", "latexmk", "bibtex") if not binaries[name])
        if not latex_smoke.get("compiled"):
            missing.append("working ctex/TikZ XeLaTeX stack")
    if profile == "submission_package":
        if not binaries["pdftoppm"]:
            missing.append("pdftoppm")
        elif not latex_smoke.get("page_rendered"):
            missing.append("working pdftoppm PDF page rendering")

    return {
        "schema_version": "1.1",
        "profile": profile,
        "status": "PASS" if required_ready else "FAIL",
        "full_submission_ready": bool(profile == "submission_package" and required_ready),
        "python": {"version": platform.python_version(), "executable": sys.executable, "ready": python_ok},
        "modules": modules,
        "cjk_font": cjk_font,
        "capabilities": {
            "numeric": numeric_ready,
            "deterministic_rendering": rendering_ready,
            "latex_compile": latex_ready,
            "paper_page_rendering": paper_review_ready,
            "latex_smoke": latex_smoke,
        },
        "binaries": binaries,
        "missing": sorted(set(missing)),
        "installation_performed": False,
        "note": "Read-only host preflight. Disposable fixture compilation is allowed; no package installation or host configuration is performed.",
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
