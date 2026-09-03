#!/usr/bin/env python3
"""Forward regression for the local CUMCM Matplotlib style and renderer."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


RENDERER = Path(__file__).with_name("matplotlib_plot_from_spec.py")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mm-cumcm-style-") as temp:
        root = Path(temp)
        source = root / "values.csv"
        source.write_text("item,old,new\nM1,15.2248,18.8837\nM2,14.0999,14.0069\nM3,10.0168,6.9255\n", encoding="utf-8")
        spec = {
            "figure_id": "forward_style",
            "source_csv": str(source),
            "chart_type": "dumbbell",
            "x": "item",
            "y": ["old", "new"],
            "series_labels": ["旧版", "现行"],
            "xlabel": "时长 / s",
            "ylabel": "对象",
            "style_profile": "cumcm-highlight",
            "palette_profile": "cumcm-highlight",
            "size_profile": "full-width",
            "base_font_pt": 9,
        }
        spec_path = root / "plot.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        output = root / "rendered"
        run = subprocess.run(
            [sys.executable, str(RENDERER), str(spec_path), "--output-dir", str(output)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if run.returncode != 0:
            raise AssertionError(run.stderr or run.stdout)
        pdf = output / "forward_style.pdf"
        svg = output / "forward_style.svg"
        png = output / "forward_style.png"
        manifest = json.loads((output / "forward_style.manifest.json").read_text(encoding="utf-8"))
        if pdf.read_bytes()[:4] != b"%PDF" or not svg.is_file() or not png.is_file():
            raise AssertionError("renderer did not create reopenable PDF/SVG/PNG outputs")
        if manifest["status"] != "RUNTIME_VERIFIED" or manifest["semantic_claim_validation"] is not False:
            raise AssertionError("runtime status must remain separate from semantic evidence status")
        if manifest["style"]["style_profile"] != "cumcm-highlight":
            raise AssertionError("style profile was not recorded")
        if manifest["source"]["rows"] != 3:
            raise AssertionError("source row count changed")

        bad = dict(spec)
        bad["figure_id"] = "bad_title"
        bad["title"] = "不应进入论文图内的标题"
        bad_path = root / "bad.json"
        bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        rejected = subprocess.run(
            [sys.executable, str(RENDERER), str(bad_path), "--output-dir", str(root / "bad")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if rejected.returncode == 0 or "LaTeX caption" not in (rejected.stderr + rejected.stdout):
            raise AssertionError("internal paper title should be rejected")

    print("PASS: CUMCM style forward render, manifest boundary, and title rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
