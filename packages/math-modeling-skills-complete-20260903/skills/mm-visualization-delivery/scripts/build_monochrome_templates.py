"""Compile the two default black/white TikZ templates in a NEW output directory.

Never compiles in the installed asset directory. No auto-install or networking.
Successful compilation and achromatic pixels are not independent visual approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdftoppm", default="pdftoppm")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    xelatex = shutil.which("xelatex")
    renderer = shutil.which(args.pdftoppm) or args.pdftoppm
    if not xelatex or not Path(renderer).is_file():
        raise RuntimeError("XeLaTeX and Poppler pdftoppm must already be available")
    version = subprocess.run([xelatex, "--version"], capture_output=True, text=True, timeout=20).stdout
    flags = (["--disable-installer"] if "miktex" in version.lower() else [])
    flags += ["-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error"]
    assets = Path(__file__).resolve().parents[1] / "assets/tikz-schematics/monochrome"
    report = {"schema": "monochrome-tikz-runtime-v1", "status": "RUNTIME_VERIFIED", "actual_backend": "tikz",
              "independent_visual_review": False, "user_has_viewed_new_assets": False,
              "automatic_installation": False, "compiler_version": version.splitlines()[0],
              "builder_sha256": sha(Path(__file__)), "templates": []}
    for source in sorted(assets.glob("*.tex")):
        shutil.copyfile(source, args.output_dir / source.name)
        run = subprocess.run([xelatex, *flags, source.name], cwd=args.output_dir, capture_output=True,
                             encoding="utf-8", errors="replace", timeout=60)
        (args.output_dir / (source.stem + ".stdout.log")).write_text(run.stdout + "\n" + run.stderr, encoding="utf-8")
        log = (args.output_dir / (source.stem + ".log")).read_text(encoding="utf-8", errors="replace")
        defects = re.findall(r"Missing character:|Overfull \\[hv]box|Undefined control sequence|^!", log, re.M)
        if run.returncode or defects:
            raise RuntimeError(source.name + " compilation failed or has font/layout defects; keep logs")
        pdf = args.output_dir / (source.stem + ".pdf")
        render = subprocess.run([str(renderer), "-r", "180", "-singlefile", "-png", str(pdf), str(args.output_dir / source.stem)],
                                capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        (args.output_dir / (source.stem + ".render.log")).write_text(render.stdout + "\n" + render.stderr, encoding="utf-8")
        if render.returncode:
            raise RuntimeError(source.name + " PDF render failed")
        from PIL import Image, ImageChops
        png = args.output_dir / (source.stem + ".png")
        with Image.open(png) as image:
            red, green, blue = image.convert("RGB").split()
            achromatic = ImageChops.difference(red, green).getbbox() is None and ImageChops.difference(red, blue).getbbox() is None
        if not achromatic:
            raise RuntimeError(source.name + " rendered pixels contain chromatic color")
        report["templates"].append({"source": {"file": source.name, "sha256": sha(source)},
            "historical_colored_assets": [{"file": "../" + source.stem + suffix,
                "sha256": sha(assets.parent / (source.stem + suffix))} for suffix in (".tex", ".pdf", ".png")],
            "derivation": "Same physical construction; black line/text, white area fills; layered material uses black hatch strips. Historical assets unchanged.",
            "command": ["xelatex", *flags, source.name],
            "pdf": {"file": pdf.name, "sha256": sha(pdf)}, "preview": {"file": png.name, "sha256": sha(png)},
            "build_log_sha256": sha(args.output_dir / (source.stem + ".log")),
            "stdout_log_sha256": sha(args.output_dir / (source.stem + ".stdout.log")),
            "logs_scope": "Full logs remain in the new build output directory; not redistributed because local tool logs may contain private paths.",
            "compiler_exit_code": run.returncode, "renderer_exit_code": render.returncode,
            "font_or_overfull_defects": defects, "all_pixels_achromatic": achromatic,
            "raster_antialiasing_note": "Gray edge pixels may result from antialiasing; no intentional gray/coded fills in source."})
    (args.output_dir / "COMPILE_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
