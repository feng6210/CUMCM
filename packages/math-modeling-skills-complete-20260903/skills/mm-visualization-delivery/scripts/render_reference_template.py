#!/usr/bin/env python3
"""Clean-room reference styles; draw supplied CSV values, never invent results.

CLI: --spec JSON --output-dir NEW_DIRECTORY. See style_reference_library.md.
Numerical transformations, fitting and uncertainty estimation belong upstream.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

from cumcm_plot_style import choose_cjk_font, configure_matplotlib, style_axis, MARKERS, LINESTYLES

PALETTES = {
    "rose-heatmap": ["#FFF5E9", "#F8C9CC", "#DF7AA1", "#9E477C", "#43235D"],
    "warm-surface-projection": ["#FFF1CB", "#F6C36B", "#EE875E", "#CF5267", "#713F72"],
    "teal-coral-inset": ["#239B96", "#EC7760", "#E3B74C", "#5681B7", "#916CB6", "#CA6792"],
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_number(value, field):
    import math
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def validate(spec, frame):
    """Validate all data before allocating any output directory."""
    import numpy as np
    import pandas as pd
    template = spec.get("template_id")
    if template not in PALETTES:
        raise ValueError("unknown template_id")
    if frame.empty or frame.columns.duplicated().any():
        raise ValueError("CSV must be nonempty with unique columns")
    if spec.get("transformations", "none") not in ("none", [], None):
        raise ValueError("precompute transformations upstream; renderer permits none only")
    if spec.get("title") or spec.get("allow_internal_title"):
        raise ValueError("put Chinese caption in LaTeX, not an internal plot title")
    if not re.fullmatch(r"[\w-]+", str(spec.get("figure_id", "")), re.UNICODE):
        raise ValueError("figure_id must be a safe basename using letters/digits/_/-")
    font_size = finite_number(spec.get("base_font_pt", 9), "base_font_pt")
    if font_size < 8.5:
        raise ValueError("base_font_pt >=8.5 required: all tick/inset text stays >=8pt")
    if any(k in spec for k in ("width_in", "height_in", "width_mm", "size_profile")):
        raise ValueError("reference templates use fixed 160mm width; no geometry overrides")

    def columns(names, numeric=True):
        if any(not isinstance(n, str) or n not in frame.columns for n in names):
            raise ValueError(f"missing source columns: {names}")
        if numeric:
            for name in names:
                values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
                if not np.isfinite(values).all():
                    raise ValueError(f"nonfinite source column: {name}")
                frame[name] = values
        elif frame[names].isna().any().any():
            raise ValueError("missing matrix category")

    details = {}
    if template == "rose-heatmap":
        row, col, value = (spec[k] for k in ("row", "column", "value"))
        if len({row, col, value}) != 3:
            raise ValueError("matrix roles must use distinct columns")
        columns([row, col], numeric=False)
        columns([value])
        for name in (row, col):
            frame[name] = frame[name].astype(str)
        orders = []
        for name, field in ((row, "row_order"), (col, "column_order")):
            order = spec.get(field)
            if not isinstance(order, list) or not order or not all(isinstance(v, str) and v for v in order):
                raise ValueError(f"{field} must list nonempty string labels")
            if len(set(order)) != len(order) or set(order) != set(frame[name]):
                raise ValueError(f"{field} must match unique source labels exactly")
            orders.append(order)
        if frame.duplicated([row, col]).any() or len(frame) != len(orders[0]) * len(orders[1]):
            raise ValueError("matrix requires complete grid with no duplicate cells")
        if max(map(len, orders)) > 24:
            raise ValueError("split matrices larger than24 labels for160mm readability")
        details = {"variables": [row, col, value], "matrix_shape": [len(x) for x in orders]}
        decimal = spec.get("decimal_places", 2)
        if isinstance(decimal, bool) or not isinstance(decimal, int) or not 0 <= decimal <= 5:
            raise ValueError("decimal_places must be integer0..5")
        if spec.get("annotate_cells", False) and max(map(len, orders)) > 12:
            raise ValueError("cell annotations require at most12 rows and12 columns at160mm")
    elif template == "warm-surface-projection":
        x, y, value = (spec[k] for k in ("x", "y", "z"))
        if len({x, y, value}) != 3:
            raise ValueError("surface roles must use distinct columns")
        columns([x, y, value])
        nx, ny = frame[x].nunique(), frame[y].nunique()
        if min(nx, ny) < 2 or len(frame) != nx * ny or frame.duplicated([x, y]).any():
            raise ValueError("surface requires a complete rectangular grid without duplicate points")
        details = {"variables": [x, y, value], "matrix_shape": [int(ny), int(nx)]}
        if "projection_z" in spec and finite_number(spec["projection_z"], "projection_z") >= frame[value].min():
            raise ValueError("projection_z must lie strictly below all supplied z values")
        for field, default in (("elev", 28), ("azim", -55)):
            finite_number(spec.get(field, default), field)
    else:
        x = spec["x"]
        series = spec.get("series")
        if not isinstance(series, list) or not 1 <= len(series) <= 6 or not all(isinstance(s, dict) for s in series):
            raise ValueError("series must contain1..6 objects")
        columns([x])
        if len(frame) < 2 or not np.all(np.diff(frame[x].to_numpy()) > 0):
            raise ValueError("x must be strictly increasing, unique and contain at least2 rows")
        if len({s.get("column") for s in series}) != len(series):
            raise ValueError("series columns must be unique")
        if len({s.get("label") for s in series}) != len(series):
            raise ValueError("series labels must be unique")
        variables = [x]
        for item in series:
            if not isinstance(item.get("label"), str) or not item["label"].strip():
                raise ValueError("each series requires a nonempty display label")
            columns([item["column"]])
            variables.append(item["column"])
            if ("lower" in item) != ("upper" in item):
                raise ValueError("band requires both lower and upper columns")
            if "lower" in item:
                if not spec.get("uncertainty_type") or not spec.get("uncertainty_source"):
                    raise ValueError("band requires uncertainty_type and uncertainty_source")
                columns([item["lower"], item["upper"]])
                lower, central, upper = (frame[item[k]].to_numpy() for k in ("lower", "column", "upper"))
                if not ((lower <= central).all() and (central <= upper).all()):
                    raise ValueError("band must satisfy lower<=supplied central value<=upper")
                variables.extend([item["lower"], item["upper"]])
        bounds = spec.get("inset_bounds")
        if not isinstance(bounds, list) or len(bounds) != 4:
            raise ValueError("inset_bounds must be[xmin,xmax,ymin,ymax]")
        xmin, xmax, ymin, ymax = [finite_number(v, "inset_bounds") for v in bounds]
        if not xmin < xmax or not ymin < ymax:
            raise ValueError("inset bounds must be strictly increasing")
        if xmin < frame[x].min() or xmax > frame[x].max():
            raise ValueError("inset x bounds must stay within supplied x range")
        selected = frame[x].between(xmin, xmax)
        if selected.sum() < 2 or not any(frame.loc[selected, s["column"]].between(ymin, ymax).any() for s in series):
            raise ValueError("inset must contain at least2 source x samples and a visible supplied value")
        details = {"variables": variables, "inset_bounds": bounds, "inset_data": "same supplied source; display zoom only"}
        return details

    lo, hi = finite_number(spec["vmin"], "vmin"), finite_number(spec["vmax"], "vmax")
    if not lo < hi or frame[value].min() < lo or frame[value].max() > hi:
        raise ValueError("fixed vmin/vmax must be ordered and include every supplied value (no clipping)")
    if spec.get("matrix_semantics") == "correlation":
        raise ValueError("rose sequential colors do not encode signed correlation; use an approved diverging card")
    details["fixed_color_range"] = [lo, hi]
    return details


def render(spec_path, output_dir, pdf_python=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager, colors
    from matplotlib.text import Text
    import numpy as np
    import pandas as pd
    from PIL import Image

    spec_path, output_dir = Path(spec_path).resolve(), Path(output_dir).resolve()
    spec_hash = sha256(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    source = Path(spec["source_csv"])
    source = source.resolve() if source.is_absolute() else (spec_path.parent / source).resolve()
    source_hash = sha256(source)
    # Detect duplicate headers before pandas silently renames them.
    import csv
    with source.open(encoding="utf-8-sig", newline="") as stream:
        headers = next(csv.reader(stream))
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate CSV header")
    frame = pd.read_csv(source)
    details = validate(spec, frame)
    if output_dir.exists():
        raise FileExistsError("output directory must be new; immutable renders never overwrite")
    font = choose_cjk_font(font_manager, str(spec.get("font_family", "")))
    if not font:
        raise RuntimeError("Chinese-capable font not installed; install a CJK font before rendering")
    base = float(spec.get("base_font_pt", 9))
    configure_matplotlib(plt, font, base)
    template = spec["template_id"]
    palette = PALETTES[template]
    height = 112 if template == "warm-surface-projection" else 100
    fig = plt.figure(figsize=(160 / 25.4, height / 25.4), layout="constrained")
    cmap = colors.LinearSegmentedColormap.from_list(template, palette)
    effects = []
    if template == "rose-heatmap":
        ax = fig.add_subplot()
        matrix = frame.pivot(index=spec["row"], columns=spec["column"], values=spec["value"]).loc[spec["row_order"], spec["column_order"]].to_numpy()
        image = ax.imshow(matrix, cmap=cmap, vmin=spec["vmin"], vmax=spec["vmax"], interpolation="nearest", aspect="auto")
        ax.set_xticks(range(len(spec["column_order"])), spec["column_order"], rotation=35, ha="right")
        ax.set_yticks(range(len(spec["row_order"])), spec["row_order"])
        ax.set_xticks(np.arange(-.5, matrix.shape[1], 1), minor=True)
        ax.set_yticks(np.arange(-.5, matrix.shape[0], 1), minor=True)
        ax.grid(which="minor", color="#FFFFFF", linewidth=.65)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        if spec.get("annotate_cells", False):
            for (r, c), value in np.ndenumerate(matrix):
                rgb = image.cmap(image.norm(value))[:3]
                luminance = sum(v * weight for v, weight in zip(rgb, (.2126, .7152, .0722)))
                ax.text(c, r, f"{value:.{spec.get('decimal_places', 2)}f}", ha="center", va="center", fontsize=base-.5, color="white" if luminance < .48 else "#382335")
        fig.colorbar(image, ax=ax, fraction=.045, pad=.025, label=spec.get("colorbar_label", "指标值"))
        effects = ["continuous_color_encoding", "cell_grid"]
    elif template == "warm-surface-projection":
        # 3D axis labels are not reliably considered by constrained_layout.
        # Reserve a real gutter for z-label + colorbar at fixed final size.
        fig.set_layout_engine("none")
        ax = fig.add_axes([.015, .10, .73, .84], projection="3d")
        x, y, z = (spec[k] for k in ("x", "y", "z"))
        xs, ys = np.sort(frame[x].unique()), np.sort(frame[y].unique())
        xx, yy = np.meshgrid(xs, ys)
        zz = frame.pivot(index=y, columns=x, values=z).loc[ys, xs].to_numpy()
        norm = colors.Normalize(spec["vmin"], spec["vmax"])
        projection_z = spec.get("projection_z", float(zz.min() - .28 * (spec["vmax"] - spec["vmin"])))
        surface = ax.plot_surface(xx, yy, zz, cmap=cmap, norm=norm, rcount=len(ys), ccount=len(xs), linewidth=.3, edgecolor=(.35,.25,.32,.25), antialiased=True, shade=False)
        # Each measured grid point is projected without interpolation or fitting.
        ax.scatter(xx.ravel(), yy.ravel(), np.full(xx.size, projection_z), c=zz.ravel(), cmap=cmap, norm=norm, marker="s", s=35, depthshade=False, alpha=1.0, edgecolors="#65505D", linewidths=.3)
        ax.scatter(xx.ravel(), yy.ravel(), zz.ravel(), c="#563845", s=5, depthshade=False)
        ax.set_zlim(projection_z, float(zz.max() + .07 * (spec["vmax"] - spec["vmin"])))
        ax.set_zlabel(spec.get("zlabel", "响应值"), labelpad=6)
        ax.view_init(elev=spec.get("elev", 28), azim=spec.get("azim", -55))
        ax.set_box_aspect((1.25, 1, .8))
        color_axis = fig.add_axes([.865, .23, .025, .59])
        fig.colorbar(surface, cax=color_axis, label=spec.get("colorbar_label", "响应值"))
        effects = ["surface_grid_connections_not_fit", "same_values_base_projection", "measured_points"]
        details["projection_z"] = float(projection_z)
        details["surface_semantics"] = "faces connect supplied rectangular grid nodes; no fitted or newly sampled values"
    else:
        # Use explicit figure coordinates: inset titles beyond parent axes can
        # be clipped differently by PDF and Agg constrained-layout passes.
        # Both panels, labels and legend stay inside the fixed 160mm canvas.
        fig.set_layout_engine("none")
        ax = fig.add_axes([.115, .155, .83, .53])
        inset = fig.add_axes([.66, .765, .285, .16])
        x = frame[spec["x"]].to_numpy()
        for i, item in enumerate(spec["series"]):
            values = frame[item["column"]].to_numpy()
            for target in (ax, inset):
                target.plot(x, values, color=palette[i], label=item["label"], linestyle=LINESTYLES[i % len(LINESTYLES)], marker=MARKERS[i], markersize=3, linewidth=1.4, markerfacecolor="white", markeredgewidth=.8)
                if "lower" in item:
                    target.fill_between(x, frame[item["lower"]].to_numpy(), frame[item["upper"]].to_numpy(), color=palette[i], alpha=.14, linewidth=0)
        xmin, xmax, ymin, ymax = spec["inset_bounds"]
        inset.set_xlim(xmin, xmax)
        inset.set_ylim(ymin, ymax)
        inset.set_title("局部放大", fontsize=base-.5, loc="left", pad=3)
        inset.tick_params(labelsize=base-.5, pad=1)
        inset.locator_params(nbins=3)
        style_axis(ax)
        style_axis(inset, show_grid=False)
        ax.indicate_inset_zoom(inset, edgecolor="#8A999C", alpha=.7)
        ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.04), fontsize=base-.5, ncol=2 if len(spec["series"]) > 3 else 1)
        effects = ["same_data_zoom", "markers_and_line_styles"] + (["precomputed_interval_fill"] if any("lower" in s for s in spec["series"]) else [])
    ax.set_xlabel(spec.get("xlabel", "参数一"))
    ax.set_ylabel(spec.get("ylabel", "参数二" if template != "teal-coral-inset" else "指标值"))
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs, render_warnings = [], []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.canvas.draw()
        for label in fig.findobj(Text):
            if label.get_text() and label.get_visible() and label.get_fontsize() < 8:
                raise RuntimeError("effective font below8pt")
        for suffix in ("pdf", "svg", "png"):
            path = output_dir / f"{spec['figure_id']}.{suffix}"
            fig.savefig(path, dpi=300 if suffix == "png" else None, metadata={"Creator": "mm-visualization-delivery"})
            outputs.append(path)
        render_warnings.extend(str(w.message) for w in caught)
    plt.close(fig)
    if sha256(source) != source_hash or sha256(spec_path) != spec_hash:
        raise RuntimeError("source or specification changed during render; outputs are ineligible")
    ET.parse(outputs[1])
    with Image.open(outputs[2]) as raster:
        raster.verify()
    pdf_ok, pdf_level = False, "header_only"
    if not outputs[0].read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("invalid PDF header")
    try:
        import fitz
        with fitz.open(outputs[0]) as pdf:
            if len(pdf) != 1:
                raise RuntimeError("expected one figure page")
            pdf[0].get_pixmap()
            pdf_ok, pdf_level = True, "page_reopened_and_rasterized"
    except ImportError:
        if pdf_python:
            import subprocess
            code = "import pypdfium2 as p,sys; d=p.PdfDocument(sys.argv[1]); assert len(d)==1; page=d[0]; bitmap=page.render(scale=1); assert bitmap.width>0 and bitmap.height>0; bitmap.close(); page.close(); d.close()"
            check = subprocess.run([str(Path(pdf_python).resolve()), "-c", code, str(outputs[0])], capture_output=True, text=True, timeout=60)
            if check.returncode != 0:
                raise RuntimeError("PDF reopen/rasterization failed: " + check.stderr[-1000:])
            pdf_ok, pdf_level = True, "external_pypdfium2_page_reopened_and_rasterized"
        else:
            render_warnings.append("PyMuPDF unavailable: PDF header checked only; use --pdf-python with pypdfium2 for full reopen")
    bad_glyph = any("Glyph" in w and "missing" in w for w in render_warnings)
    manifest = {
        "renderer": "render_reference_template", "template_id": template,
        "status": "RUNTIME_VERIFIED" if pdf_ok and not bad_glyph else "RENDERED_PENDING_REOPEN_OR_GLYPH_CHECK",
        "semantic_claim_validation": False,
        "source": {"path": source.name, "sha256": source_hash, "sha256_after": sha256(source), "rows": len(frame)},
        "spec": {"path": spec_path.name, "sha256": spec_hash, "sha256_after": sha256(spec_path)},
        "render_contract": {"chart_type": {"rose-heatmap": "heatmap", "warm-surface-projection": "surface_3d", "teal-coral-inset": "line"}[template], "source_sha256": source_hash, "spec_sha256": spec_hash, "transformations": "none", **details},
        "outputs": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in outputs],
        "style": {"style_profile": "cumcm-vivid", "palette_profile": template, "effective_palette": palette, "final_width_mm": 160, "final_height_mm": height, "base_font_pt": base, "effective_min_font_pt": base-.5, "font_family": font, "line_width_pt": 1.4 if template == "teal-coral-inset" else .65, "internal_title": False, "decorative_effects": effects, "legend_strategy": "top" if template == "teal-coral-inset" else "colorbar", "size_profile": "full-width", "series_color_mapping": {s["label"]: palette[i] for i,s in enumerate(spec.get("series", []))}},
        "environment": {"matplotlib": matplotlib.__version__, "pandas": pd.__version__, "font_family": font},
        "reopen_check": {"pdf": pdf_ok, "svg": True, "png": True},
        "pdf_reopen_level": pdf_level,
        "visual_review": "PENDING_REFERENCE_COMPARISON", "warnings": render_warnings + ["Render validity is not numerical or claim validation; review reference style at final size."],
    }
    manifest_path = output_dir / f"{spec['figure_id']}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Render supplied CSV via rose-heatmap, warm-surface-projection or teal-coral-inset; no fitting or synthetic data.")
    parser.add_argument("--spec", type=Path, required=True, help="JSON specification; relative source_csv resolves beside it")
    parser.add_argument("--output-dir", type=Path, required=True, help="New immutable output directory")
    parser.add_argument("--pdf-python", type=Path, help="Optional Python with pypdfium2 for full PDF reopen when local PyMuPDF is unavailable")
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.spec, args.output_dir, args.pdf_python), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        parser.exit(2, f"render rejected: {exc}\n")


if __name__ == "__main__":
    main()
