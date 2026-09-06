#!/usr/bin/env python3
"""Original, data-preserving renderer for the full local-corpus family index.

--schema describes the JSON contract. --generate-demos NEW_DIR creates clearly
labelled synthetic DEMO_ONLY fixtures; ordinary --spec never creates input data.
No original corpus code, images, fitting, random samples or statistics are used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

from cumcm_plot_style import choose_cjk_font, configure_matplotlib, style_axis

FAMILIES = (
    "scatter_2d", "scatter_3d", "line", "log_x", "log_y", "log_xy", "bar",
    "grouped_bar", "stacked_bar", "dual_axis", "line_interval", "contour",
    "surface_wireframe", "area_3d", "pie", "donut", "radar", "vector_field",
    "step", "stem", "bubble", "parallel_coordinates",
)
PALETTE = ["#219C96", "#EC7964", "#DBAE4C", "#577BB5", "#986CB5", "#CB6C99"]
FAMILY_SCHEMA = {
    "schema_version": 1,
    "required_common": ["family", "figure_id", "source_csv", "xlabel", "ylabel", "units"],
    "units": "Object mapping every used numeric CSV column to its unit, or 无量纲; no inference.",
    "series": "1..6 objects {column: CSV field, label: Chinese display label}; interval also lower/upper; area_3d also position.",
    "style_options": {"palette": "2..12 valid colors; first six are categorical default", "markers": "1..6 Matplotlib marker strings", "line_styles": "1..6 values from -,--,-.,:", "elev": "3D view elevation degrees", "azim": "3D azimuth degrees", "base_font_pt": ">=9; all text >=9", "width_mm": "fixed 160", "height_mm": "90..140; default105"},
    "families": {
        "scatter_2d": "x,y numeric columns; optional group category column (<=6); all source points retained",
        "scatter_3d": "x,y,z numeric columns; optional group; spatial_explanation and companion=source_csv required",
        "line": "x strictly increasing; series; supplied points connected without smoothing",
        "log_x": "line schema and all x>0; display logarithm only, source values unchanged",
        "log_y": "line schema and all series values>0",
        "log_xy": "line schema and positive x and series values",
        "bar": "x unique category labels; exactly one series; zero baseline",
        "grouped_bar": "x unique category labels; 2..6 series; zero baseline",
        "stacked_bar": "x unique labels; >=2 nonnegative series; additive_semantics explaining common total required",
        "dual_axis": "x ordered; exactly two series each axis left/right; ylabel_right, relationship and aligned_alternative_check required; both units explicit",
        "line_interval": "x ordered; each series column/lower/upper; uncertainty_definition and uncertainty_source; lower<=column<=upper",
        "contour": "x,y,z complete rectangular grid; explicit strictly increasing levels enclosing all z; colorbar_label; lines are display interpolation, not estimated grid values",
        "surface_wireframe": "x,y,z complete rectangular grid; spatial_explanation and companion=source_csv; no fit or interpolation",
        "area_3d": "x ordered; series each has numeric distinct position; position_unit, z_baseline<=all supplied values; spatial_explanation and companion=source_csv",
        "pie": "x unique category column; value percentage column; <=6 mutually exclusive categories; sum=100 within1e-6; composition_semantics and display_decimals0..4; no normalization",
        "donut": "same as pie; no fabricated central total",
        "radar": "x unique metric labels3..8; series; shared range [vmin,vmax]; normalization_definition and positive_direction=true; upstream already normalized",
        "vector_field": "x,y,u,v numeric; vector_scale>0, vector_scale_definition; explicit units, no normalization or subsampling",
        "step": "line schema plus step_where pre/post/mid explicitly selected",
        "stem": "line schema; exactly one series; zero baseline",
        "bubble": "x,y,size numeric; size>=0; size_scale_pt2>0 (area proportional to size); size_label; size_legend_values supplied positive values covering observed range",
        "parallel_coordinates": "x unique metrics3..8; series1..6; fixed vmin/vmax; normalization_definition and positive_direction=true; no in-render normalization",
    },
    "invariants": ["finite numeric inputs", "all used fields recorded", "no fitting/statistics/filtering", "no overwrite", "source/spec hashes before and after", "PDF/SVG/PNG actual reopen", "visual review remains PENDING", "color/axis limits cannot clip data"],
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name}: finite number required")
    return result


def load(spec_path):
    import pandas as pd
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    if not isinstance(spec, dict):
        raise ValueError("JSON object required")
    source = Path(spec["source_csv"])
    if not source.is_absolute():
        source = spec_path.parent / source
    source = source.resolve()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream))
    if len(set(header)) != len(header) or any(not x for x in header):
        raise ValueError("CSV header must be nonempty and unique")
    source_hash_before = sha256(source)
    frame = pd.read_csv(source, encoding="utf-8-sig")
    if sha256(source) != source_hash_before:
        raise RuntimeError("source changed while CSV was being parsed")
    return spec, source, frame


def validate(spec, frame):
    import numpy as np
    import pandas as pd
    from matplotlib.colors import is_color_like
    from matplotlib.markers import MarkerStyle
    family = spec.get("family")
    if family not in FAMILIES or frame.empty:
        raise ValueError("known family and nonempty CSV required")
    if not re.fullmatch(r"[\w-]+", str(spec.get("figure_id", ""))):
        raise ValueError("figure_id must be a safe basename")
    if spec.get("transformations", "none") not in ("none", [], None):
        raise ValueError("precompute transformations upstream")
    if any(k in spec for k in ("xlim", "ylim", "zlim", "filter", "fit", "smooth", "normalize", "title")):
        raise ValueError("axis clipping/filtering/fitting/normalizing/internal titles are not supported")
    if number(spec.get("width_mm", 160), "width_mm") != 160:
        raise ValueError("fixed160mm width required")
    if number(spec.get("base_font_pt", 9), "font") < 9:
        raise ValueError("font must be>=9pt")
    if not 90 <= number(spec.get("height_mm", 105), "height") <= 140:
        raise ValueError("height90..140mm required")
    for key in ("xlabel", "ylabel"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f"{key} is required")
    palette = spec.get("palette", PALETTE)
    if not isinstance(palette, list) or not 2 <= len(palette) <= 12 or not all(is_color_like(c) for c in palette):
        raise ValueError("palette needs2..12 valid colors")
    markers = spec.get("markers", ["o", "s", "^", "D", "v", "P"])
    if not isinstance(markers, list) or not 1 <= len(markers) <= 6:
        raise ValueError("markers must contain1..6 marker strings")
    for marker in markers:
        MarkerStyle(marker)
    styles = spec.get("line_styles", ["-", "--", "-.", ":"])
    if not isinstance(styles, list) or not styles or any(s not in ("-", "--", "-.", ":") for s in styles):
        raise ValueError("unsupported line_styles")
    used, numeric = [], []

    def col(name, is_numeric=True):
        if not isinstance(name, str) or name not in frame:
            raise ValueError(f"missing column:{name}")
        if name not in used:
            used.append(name)
        if is_numeric:
            values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(f"nonfinite data:{name}")
            frame[name] = values
            if name not in numeric:
                numeric.append(name)
        elif frame[name].isna().any() or (frame[name].astype(str).str.strip() == "").any():
            raise ValueError(f"missing category:{name}")
        return frame[name].to_numpy()

    categories = family in {"bar", "grouped_bar", "stacked_bar", "pie", "donut", "radar", "parallel_coordinates"}
    x = col(spec.get("x"), not categories)
    if categories:
        if len(set(map(str, x))) != len(x):
            raise ValueError("category/metric labels must be unique")
        if len(x) > 16:
            raise ValueError("more than16 labels requires a wider or split chart")
    series_families = {"line", "log_x", "log_y", "log_xy", "bar", "grouped_bar", "stacked_bar", "dual_axis", "line_interval", "area_3d", "radar", "step", "stem", "parallel_coordinates"}
    series = spec.get("series", [])
    if family in series_families:
        if not isinstance(series, list) or not 1 <= len(series) <= 6 or not all(isinstance(s, dict) for s in series):
            raise ValueError("series requires1..6 objects")
        if len({s.get("column") for s in series}) != len(series):
            raise ValueError("series columns must be unique")
        labels = [s.get("label") for s in series]
        if any(not isinstance(label, str) or not label.strip() for label in labels) or len(set(labels)) != len(labels):
            raise ValueError("series display labels must be unique and nonempty")
        for s in series:
            col(s.get("column"))
        if not categories and (len(x) < 2 or not np.all(np.diff(x) > 0)):
            raise ValueError("line x must be strictly increasing with>=2 samples; renderer will not sort")
    if family in {"log_x", "log_xy"} and not np.all(x > 0):
        raise ValueError("log x requires positive source values")
    if family in {"log_y", "log_xy"} and any(not (frame[s["column"]] > 0).all() for s in series):
        raise ValueError("log y requires positive source values")
    if family in {"bar", "stem"} and len(series) != 1:
        raise ValueError("single series required")
    if family in {"grouped_bar", "stacked_bar"} and len(series) < 2:
        raise ValueError("multiple series required")
    if family == "stacked_bar":
        if not spec.get("additive_semantics") or any((frame[s["column"]] < 0).any() for s in series):
            raise ValueError("stacked bars require additive semantics and nonnegative components")
    if family == "dual_axis":
        if len(series) != 2 or [s.get("axis") for s in series] != ["left", "right"]:
            raise ValueError("dual_axis exactly left then right series required")
        for key in ("ylabel_right", "relationship", "aligned_alternative_check"):
            if not spec.get(key):
                raise ValueError(f"dual_axis requires {key}")
    if family == "line_interval":
        if not spec.get("uncertainty_definition") or not spec.get("uncertainty_source"):
            raise ValueError("interval definition and source required")
        for s in series:
            lo, hi = col(s.get("lower")), col(s.get("upper"))
            if not ((lo <= frame[s["column"]]).all() and (frame[s["column"]] <= hi).all()):
                raise ValueError("lower<=supplied center<=upper required")
    if family in {"scatter_2d", "scatter_3d", "bubble", "vector_field", "contour", "surface_wireframe"}:
        col(spec.get("y"))
    if family in {"scatter_3d", "contour", "surface_wireframe"}:
        col(spec.get("z"))
    if family in {"scatter_2d", "scatter_3d"} and "group" in spec:
        groups = col(spec["group"], False)
        if len(set(groups)) > min(6, len(palette)):
            raise ValueError("scatter groups exceed palette/readable count")
    if family in {"contour", "surface_wireframe"}:
        nx, ny = frame[spec["x"]].nunique(), frame[spec["y"]].nunique()
        if min(nx, ny) < 2 or len(frame) != nx * ny or frame.duplicated([spec["x"], spec["y"]]).any():
            raise ValueError("complete rectangular grid with no duplicates required")
    if family == "contour":
        levels = spec.get("levels")
        if not isinstance(levels, list) or not 2 <= len(levels) <= 32:
            raise ValueError("explicit2..32 contour levels required")
        levels = np.array([number(v, "levels") for v in levels])
        if not (np.diff(levels) > 0).all() or frame[spec["z"]].min() < levels[0] or frame[spec["z"]].max() > levels[-1]:
            raise ValueError("ordered contour levels must enclose all values")
        if not spec.get("colorbar_label"):
            raise ValueError("colorbar_label required")
    if family in {"scatter_3d", "surface_wireframe", "area_3d"}:
        if not spec.get("spatial_explanation") or spec.get("companion") != "source_csv":
            raise ValueError("3D needs spatial explanation and source_csv exact-table companion")
        if not spec.get("zlabel"):
            raise ValueError("zlabel required")
        if not -89 <= number(spec.get("elev", 26), "elev") <= 89:
            raise ValueError("elev must be-89..89deg")
        number(spec.get("azim", -58), "azim")
    if family == "area_3d":
        positions = [number(s.get("position"), "position") for s in series]
        baseline = number(spec.get("z_baseline"), "z_baseline")
        if len(set(positions)) != len(positions) or not spec.get("position_unit"):
            raise ValueError("area_3d needs distinct true positions and position_unit")
        if any((frame[s["column"]] < baseline).any() for s in series):
            raise ValueError("z_baseline may not exceed any supplied value")
    if family in {"pie", "donut"}:
        values = col(spec.get("value"))
        if len(values) > 6 or (values < 0).any() or abs(float(values.sum()) - 100) > 1e-6 or not spec.get("composition_semantics"):
            raise ValueError("<=6 nonnegative mutually exclusive percentages with sum100 required")
        d = spec.get("display_decimals", 1)
        if isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 4:
            raise ValueError("display_decimals0..4 required")
    if family in {"radar", "parallel_coordinates"}:
        lo, hi = number(spec.get("vmin"), "vmin"), number(spec.get("vmax"), "vmax")
        if not 3 <= len(x) <= 8 or not spec.get("normalization_definition") or spec.get("positive_direction") is not True or not lo < hi:
            raise ValueError("3..8 pre-normalized positive-direction metrics and common range required")
        if family == "radar" and lo != 0:
            raise ValueError("radar requires zero radial baseline")
        if any(frame[s["column"]].min() < lo or frame[s["column"]].max() > hi for s in series):
            raise ValueError("fixed common range may not clip values")
    if family == "vector_field":
        col(spec.get("u")); col(spec.get("v"))
        if number(spec.get("vector_scale"), "vector_scale") <= 0 or not spec.get("vector_scale_definition"):
            raise ValueError("explicit positive vector_scale and definition required")
    if family == "bubble":
        sizes = col(spec.get("size"))
        if (sizes < 0).any() or number(spec.get("size_scale_pt2"), "size_scale_pt2") <= 0 or not spec.get("size_label"):
            raise ValueError("nonnegative bubble values with explicit area scale/label required")
        legend_values = spec.get("size_legend_values")
        if not isinstance(legend_values, list) or not 1 <= len(legend_values) <= 3:
            raise ValueError("1..3 explicit bubble size legend values required")
        vv = [number(v, "size_legend_values") for v in legend_values]
        if any(v <= 0 for v in vv) or max(vv) < max(sizes):
            raise ValueError("positive size legend must cover largest observed size")
    if family == "step" and spec.get("step_where") not in ("pre", "post", "mid"):
        raise ValueError("explicit step_where pre/post/mid required")
    units = spec.get("units")
    if not isinstance(units, dict) or any(not isinstance(units.get(c), str) or not units[c].strip() for c in numeric):
        raise ValueError("units must explicitly cover every numeric source field")
    if len(series) > len(palette):
        raise ValueError("palette must cover all series")
    return {"variables": used, "numeric_variables": numeric, "units": {c: units[c] for c in numeric}, "source_rows": len(frame)}


def reopen_pdf(path, pdf_python):
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        if len(doc) != 1:
            raise RuntimeError("one PDF page required")
        page = doc[0]; bitmap = page.render(scale=1)
        if bitmap.width < 1 or bitmap.height < 1:
            raise RuntimeError("empty PDF raster")
        bitmap.close(); page.close(); doc.close()
        return True
    except ImportError:
        if not pdf_python:
            return False
        code = "import pypdfium2 as p,sys; d=p.PdfDocument(sys.argv[1]); assert len(d)==1; pg=d[0]; b=pg.render(scale=1); assert b.width>0 and b.height>0; b.close(); pg.close(); d.close()"
        result = subprocess.run([str(pdf_python), "-c", code, str(path)], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError("PDF reopen failed:" + result.stderr[-600:])
        return True


def render(spec_path, output_dir, pdf_python=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import colors, font_manager
    from matplotlib.text import Text
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np
    from PIL import Image
    spec_path, output_dir = Path(spec_path).resolve(), Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError("output directory must be new; no overwrites")
    spec_hash = sha256(spec_path)
    spec, source, frame = load(spec_path)
    source_hash = sha256(source)
    details = validate(spec, frame)
    font = choose_cjk_font(font_manager, spec.get("font_family", ""))
    if not font:
        raise RuntimeError("Chinese font unavailable")
    base = float(spec.get("base_font_pt", 9))
    configure_matplotlib(plt, font, base)
    plt.rcParams.update({"xtick.labelsize": base, "ytick.labelsize": base, "legend.fontsize": base})
    family = spec["family"]
    palette = spec.get("palette", PALETTE)
    markers = spec.get("markers", ["o", "s", "^", "D", "v", "P"])
    linestyles = spec.get("line_styles", ["-", "--", "-.", ":"])
    height = float(spec.get("height_mm", 112 if family in {"scatter_3d", "surface_wireframe", "area_3d", "radar"} else 105))
    fig = plt.figure(figsize=(160 / 25.4, height / 25.4), layout="constrained")
    fig.get_layout_engine().set(h_pad=.10, w_pad=.08)
    is3d = family in {"scatter_3d", "surface_wireframe", "area_3d"}
    if is3d:
        fig.set_layout_engine("none")
        ax = fig.add_axes([.035, .09, .85, .82], projection="3d")
    elif family == "radar":
        # Polar outer metric labels occupy space beyond axes. Reserve a
        # separate legend band so the north metric cannot collide with it.
        fig.set_layout_engine("none")
        ax = fig.add_axes([.16, .12, .68, .70], projection="polar")
    else:
        ax = fig.add_subplot(projection="polar" if family == "radar" else None)
    x, series = frame[spec["x"]].to_numpy(), spec.get("series", [])
    geometry = []
    legend = "none"
    handles = []

    def line(target, xx, values, index, label):
        return target.plot(xx, values, color=palette[index], marker=markers[index % len(markers)], linestyle=linestyles[index % len(linestyles)], markersize=4, markerfacecolor="white", markeredgewidth=.9, linewidth=1.45, label=label)[0]

    if family in {"line", "log_x", "log_y", "log_xy", "line_interval", "step", "stem", "dual_axis"}:
        for i, s in enumerate(series):
            target = ax
            if family == "dual_axis" and i == 1:
                target = ax.twinx()
                target.set_ylabel(spec["ylabel_right"], color=palette[i]); target.tick_params(axis="y", colors=palette[i])
                target.spines["top"].set_visible(False)
            y = frame[s["column"]].to_numpy()
            if family == "step":
                handle = target.step(x, y, where=spec["step_where"], color=palette[i], marker=markers[i % len(markers)], linewidth=1.45, label=s["label"])[0]
                geometry.append("explicit_step_position:" + spec["step_where"])
            elif family == "stem":
                stem = target.stem(x, y, basefmt="k-", label=s["label"])
                plt.setp(stem.markerline, color=palette[i], markerfacecolor="white", markersize=5)
                plt.setp(stem.stemlines, color=palette[i], linewidth=1.3)
                plt.setp(stem.baseline, color="#B1BCC1", linewidth=.6)
                handle = stem
            else:
                handle = line(target, x, y, i, s["label"])
            handles.append(handle)
            if family == "line_interval":
                target.fill_between(x, frame[s["lower"]].to_numpy(), frame[s["upper"]].to_numpy(), color=palette[i], alpha=.18, linewidth=0)
                geometry.append("supplied_interval_bounds")
        if family in {"log_x", "log_xy"}:
            ax.set_xscale("log"); geometry.append("logarithmic_display_x")
        if family in {"log_y", "log_xy"}:
            ax.set_yscale("log"); geometry.append("logarithmic_display_y")
        if family == "dual_axis":
            ax.yaxis.label.set_color(palette[0]); ax.tick_params(axis="y", colors=palette[0])
            geometry.append("two_explicitly_labeled_scales_not_trend_agreement")
        legend = "top"
    elif family in {"scatter_2d", "scatter_3d"}:
        groups = list(dict.fromkeys(frame[spec["group"]])) if "group" in spec else [None]
        for i, group in enumerate(groups):
            sub = frame if group is None else frame[frame[spec["group"]] == group]
            args = [sub[spec["x"]], sub[spec["y"]]]
            if is3d:
                args.append(sub[spec["z"]])
            kwargs = {"depthshade": False} if is3d else {}
            ax.scatter(*args, color=palette[i], marker=markers[i % len(markers)], s=27, alpha=.88, edgecolors="white", linewidths=.45, label=str(group) if group is not None else "数据点", **kwargs)
        legend = "top" if "group" in spec else "none"
    elif family in {"bar", "grouped_bar", "stacked_bar"}:
        pos = np.arange(len(x)); bottom = np.zeros(len(x)); n = len(series)
        for i, s in enumerate(series):
            values = frame[s["column"]].to_numpy()
            offset = (i - (n - 1) / 2) * .76 / n if family == "grouped_bar" else 0
            ax.bar(pos + offset, values, width=.76/n if family == "grouped_bar" else .64, bottom=bottom if family == "stacked_bar" else None, color=palette[i], edgecolor="white", linewidth=.65, hatch=["", "//", "..", "xx", "\\\\", "++"][i], label=s["label"])
            if family == "stacked_bar":
                bottom += values
        ax.set_xticks(pos, list(map(str, x)), rotation=25 if len(x) > 8 else 0)
        ax.axhline(0, color="#53646A", linewidth=.7)
        if family == "stacked_bar":
            geometry.append("additive_component_offsets; no totals reported as new results")
        legend = "top" if n > 1 else "none"
    elif family in {"contour", "surface_wireframe"}:
        xs, ys = np.sort(frame[spec["x"]].unique()), np.sort(frame[spec["y"]].unique())
        xx, yy = np.meshgrid(xs, ys)
        zz = frame.pivot(index=spec["y"], columns=spec["x"], values=spec["z"]).loc[ys, xs].to_numpy()
        if family == "contour":
            cmap = colors.LinearSegmentedColormap.from_list("corpus_continuous", spec.get("palette", ["#FFF1CF", "#F4B16C", "#DE6F75", "#8E4779", "#443365"]))
            filled = ax.contourf(xx, yy, zz, levels=spec["levels"], cmap=cmap, vmin=spec["levels"][0], vmax=spec["levels"][-1])
            ax.contour(xx, yy, zz, levels=spec["levels"], colors="#573C53", linewidths=.5, alpha=.6)
            ax.scatter(xx.ravel(), yy.ravel(), s=4, color="#3D3046", alpha=.4)
            fig.colorbar(filled, ax=ax, pad=.025, label=spec["colorbar_label"])
            geometry.append("contour_segments_between_supplied_grid_nodes_are_display_interpolation_not_estimates")
            legend = "colorbar"
        else:
            ax.plot_wireframe(xx, yy, zz, rstride=1, cstride=1, color=palette[0], linewidth=.8, alpha=.85)
            ax.scatter(xx.ravel(), yy.ravel(), zz.ravel(), s=6, c=palette[1], depthshade=False)
            geometry.append("connections_between_supplied_grid_nodes_no_fit")
    elif family == "area_3d":
        baseline = spec["z_baseline"]
        for i, s in enumerate(series):
            pos = s["position"]; y = frame[s["column"]].to_numpy()
            vertices = [(x[0], pos, baseline)] + list(zip(x, np.repeat(pos, len(x)), y)) + [(x[-1], pos, baseline)]
            ax.add_collection3d(Poly3DCollection([vertices], facecolors=palette[i], edgecolors=palette[i], alpha=.30, linewidth=.8))
            ax.plot(x, np.repeat(pos, len(x)), y, color=palette[i], marker=markers[i % len(markers)], markersize=3, linewidth=1.4, label=s["label"])
        positions = [s["position"] for s in series]
        ax.set_xlim(min(x), max(x)); ax.set_ylim(min(positions)-.25, max(positions)+.25)
        all_z = np.concatenate([frame[s["column"]].to_numpy() for s in series])
        ax.set_zlim(baseline, float(max(all_z)) + .05 * max(float(max(all_z))-baseline, 1))
        ax.set_yticks(positions, [str(p) for p in positions])
        geometry.append("supplied_sequence_filled_to_explicit_baseline_at_true_positions")
        legend = "top"
    elif family in {"pie", "donut"}:
        values = frame[spec["value"]].to_numpy()
        # Values are prevalidated percentages; converting percent to a fraction
        # is geometric angle encoding, not an inferred normalization.
        wedges, _ = ax.pie(values / 100, normalize=False, colors=palette[:len(values)], startangle=90, counterclock=False, wedgeprops={"edgecolor": "white", "linewidth": 1.1, **({"width": .34} if family == "donut" else {})})
        labels = [f"{label}  {val:.{spec.get('display_decimals', 1)}f}%" for label, val in zip(x, values)]
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(.98, .5), frameon=False)
        ax.set_aspect("equal"); legend = "right"
        geometry.append("supplied_percent_to_angle_no_renormalization")
    elif family in {"radar", "parallel_coordinates"}:
        positions = np.linspace(0, 2*np.pi, len(x), endpoint=False) if family == "radar" else np.arange(len(x))
        for i, s in enumerate(series):
            values = frame[s["column"]].to_numpy()
            xx, yy = (np.r_[positions, positions[0]], np.r_[values, values[0]]) if family == "radar" else (positions, values)
            line(ax, xx, yy, i, s["label"])
        ax.set_xticks(positions, list(map(str, x))); ax.set_ylim(spec["vmin"], spec["vmax"])
        if family == "radar":
            ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1); ax.tick_params(axis="x", pad=9)
        else:
            for p in positions:
                ax.axvline(p, color="#B9C8CD", linewidth=.65, zorder=0)
        legend = "top"; geometry.append("pre_normalized_values_no_renderer_normalization")
    elif family == "vector_field":
        ax.quiver(x, frame[spec["y"]], frame[spec["u"]], frame[spec["v"]], color=palette[0], angles="xy", scale_units="xy", scale=spec["vector_scale"], width=.005)
        # Include complete vector endpoints in axis bounds, not only origins.
        xe = x + frame[spec["u"]].to_numpy()/spec["vector_scale"]
        ye = frame[spec["y"]].to_numpy() + frame[spec["v"]].to_numpy()/spec["vector_scale"]
        ax.update_datalim(np.c_[xe, ye]); ax.autoscale_view(); ax.set_aspect("equal", adjustable="datalim")
        geometry.append("explicit_vector_scale_no_normalization")
    elif family == "bubble":
        ax.scatter(x, frame[spec["y"]], s=frame[spec["size"]]*spec["size_scale_pt2"], color=palette[0], edgecolors=palette[1], linewidth=.8, alpha=.6)
        handles = [ax.scatter([], [], s=v*spec["size_scale_pt2"], facecolors="none", edgecolors=palette[1], label=str(v)) for v in spec["size_legend_values"]]
        ax.legend(handles=handles, title=spec["size_label"], loc="lower center", bbox_to_anchor=(.5, 1.04), ncol=len(handles), frameon=False, labelspacing=1.3)
        legend = "top"; geometry.append("bubble_area_proportional_to_supplied_size")
    if family not in {"pie", "donut", "radar"}:
        ax.set_xlabel(spec["xlabel"]); ax.set_ylabel(spec["ylabel"])
    if is3d:
        ax.set_zlabel(spec["zlabel"], labelpad=6)
        ax.view_init(spec.get("elev", 26), spec.get("azim", -58)); ax.set_box_aspect((1.15, 1, .78))
        ax.tick_params(labelsize=base, pad=2)
    elif family not in {"pie", "donut", "radar"}:
        style_axis(ax)
        if family == "dual_axis":
            ax.yaxis.label.set_color(palette[0]); ax.tick_params(axis="y", colors=palette[0])
    if family == "radar" or (is3d and legend == "top"):
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .975), ncol=min(3, len(series) or 3), frameon=False)
    elif legend == "top" and family != "bubble":
        kwargs = {"handles": handles, "labels": [s["label"] for s in series]} if family == "dual_axis" else {}
        ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.03), ncol=min(3, len(series) or 3), frameon=False, **kwargs)
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.canvas.draw()
        for text in fig.findobj(Text):
            if text.get_visible() and text.get_text() and text.get_fontsize() < 9:
                raise RuntimeError("effective font below9pt")
        for suffix in ("pdf", "svg", "png"):
            out = output_dir / (spec["figure_id"] + "." + suffix)
            fig.savefig(out, dpi=300, metadata={"Creator": "mm-visualization-delivery clean-room corpus renderer"})
            outputs.append(out)
        warning_text = [str(w.message) for w in caught]
    plt.close(fig)
    if sha256(source) != source_hash or sha256(spec_path) != spec_hash:
        raise RuntimeError("source/spec changed during rendering")
    ET.parse(outputs[1])
    with Image.open(outputs[2]) as image:
        image.verify()
    pdf_ok = reopen_pdf(outputs[0], pdf_python)
    # Preserve an exact, hash-identical CSV companion for every3D figure.
    if is3d:
        companion = output_dir / "source_values.csv"
        companion.write_bytes(source.read_bytes()); outputs.append(companion)
    if family == "contour" and "palette" not in spec:
        palette = ["#FFF1CF", "#F4B16C", "#DE6F75", "#8E4779", "#443365"]
    manifest = {
        "renderer": "render_corpus_chart", "family": family, "schema_version": 1,
        "status": "RUNTIME_VERIFIED" if pdf_ok and not warning_text else "RENDERED_PENDING_WARNING_OR_PDF_CHECK",
        "semantic_claim_validation": False, "visual_review": "PENDING_REFERENCE_COMPARISON",
        "data_status": spec.get("data_status", "USER_SUPPLIED_UNVERIFIED_BY_RENDERER"),
        "source": {"path": source.name, "sha256": source_hash, "sha256_after": sha256(source), "rows": len(frame)},
        "spec": {"path": spec_path.name, "sha256": spec_hash, "sha256_after": sha256(spec_path)},
        "render_contract": {"chart_type": family, "variables": details["variables"], "numeric_variables": details["numeric_variables"], "units": details["units"], "source_sha256": source_hash, "spec_sha256": spec_hash, "transformations": "none", "geometry_encoding": geometry, "row_filter": "none", "statistics_computed": False},
        "style": {"style_profile": "cumcm-vivid", "effective_palette": palette, "font_family": font, "base_font_pt": base, "effective_min_font_pt": base, "final_width_mm": 160, "final_height_mm": height, "line_width_pt": 1.45, "legend_strategy": legend, "internal_title": False, "decorative_effects": [], "markers": markers, "line_styles": linestyles, "view": {"elev": spec.get("elev", 26), "azim": spec.get("azim", -58)} if is3d else None},
        "outputs": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in outputs],
        "reopen_check": {"pdf": pdf_ok, "svg": True, "png": True},
        "pdf_reopen_level": "page_reopened_and_rasterized" if pdf_ok else "NOT_REOPENED_INSTALL_PYPDFIUM2_OR_PASS_PDF_PYTHON",
        "warnings": warning_text, "environment": {"matplotlib": matplotlib.__version__},
    }
    (output_dir / (spec["figure_id"] + ".manifest.json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def demo_spec(family):
    """Explicit handmade synthetic fixtures; never invoked in ordinary render."""
    spec = {"family": family, "figure_id": "demo-"+family, "source_csv": "data.csv", "xlabel": "时间 / s", "ylabel": "响应 / m", "units": {"t": "s", "a": "m", "b": "m", "lower": "m", "upper": "m", "x": "m", "y": "m", "z": "m", "u": "m/s", "v": "m/s", "size": "个", "percent": "%"}, "data_status": "DEMO_ONLY_SYNTHETIC_NOT_EXPERIMENT_EVIDENCE"}
    spec.update(x="t", series=[{"column": "a", "label": "方案甲"}, {"column": "b", "label": "方案乙"}])
    rows = [{"t": i+1, "a": v, "b": w, "lower": lo, "upper": hi} for i,(v,w,lo,hi) in enumerate([(2,1.3,1.5,2.5),(3.1,2.5,2.6,3.6),(3.7,3.1,3.2,4.2),(4.8,3.9,4.3,5.3),(5.2,4.7,4.7,5.7),(6,5.2,5.5,6.5)])]
    if family in {"scatter_2d", "scatter_3d", "bubble"}:
        rows = [{"x": x,"y": y,"z": z,"group": g,"size": size} for x,y,z,g,size in [(1,2,3,"组甲",2),(2,2.8,3.8,"组甲",4),(3,3.1,4.1,"组甲",6),(1.5,3.2,2.8,"组乙",3),(2.5,4.1,3.2,"组乙",5),(3.5,4.8,4,"组乙",7)]]
        spec.update(x="x", y="y", z="z", xlabel="位置一 / m", ylabel="位置二 / m", group="group")
        spec.pop("series")
        if family == "bubble":
            spec.pop("group"); spec.update(size="size", size_scale_pt2=32, size_label="数量 / 个", size_legend_values=[2,4,7])
    if family in {"bar", "grouped_bar", "stacked_bar", "radar", "parallel_coordinates"}:
        for row, label in zip(rows, ["指标一", "指标二", "指标三", "指标四", "指标五", "指标六"]):
            row["metric"] = label
        spec.update(x="metric", xlabel="评价指标", ylabel="原始量 / m")
        if family == "bar":
            spec["series"] = spec["series"][:1]
        if family == "stacked_bar":
            spec["additive_semantics"] = "DEMO_ONLY：两个可相加部件长度组成总长度"
            spec["series"][0]["label"] = "构件甲"
            spec["series"][1]["label"] = "构件乙"
        if family in {"radar", "parallel_coordinates"}:
            spec.update(vmin=0, vmax=7, normalization_definition="DEMO_ONLY人工同尺度示例，非实际评价", positive_direction=True, ylabel="同尺度演示分值")
            spec["units"]["a"] = spec["units"]["b"] = "无量纲"
    if family == "line_interval":
        spec["series"] = [{"column": "a", "label": "预计算中心值", "lower": "lower", "upper": "upper"}]
        spec.update(uncertainty_definition="DEMO_ONLY手工给定上下界，非真实置信区间", uncertainty_source="本脚本演示fixture；不是统计结果")
    if family == "dual_axis":
        spec["series"][0]["axis"] = "left"; spec["series"][1]["axis"] = "right"
        spec["units"]["b"] = "J"
        spec.update(ylabel_right="能耗 / J", relationship="DEMO_ONLY共同时间轴上的两种给定测量", aligned_alternative_check="真实使用须与上下对齐子图核对；演示仅展示双轴能力")
    if family in {"contour", "surface_wireframe"}:
        matrix = [[2,2.5,3,3.2],[2.4,3.4,4,3.8],[3.1,4.2,5.2,4.7],[3.8,4.8,5.8,5.3]]
        rows = [{"x": i, "y": j, "z": matrix[j][i]} for j in range(4) for i in range(4)]
        spec.pop("series"); spec.update(x="x", y="y", z="z", xlabel="参数一 / m", ylabel="参数二 / m", levels=[2,2.5,3,3.5,4,4.5,5,5.5,6], colorbar_label="预给定响应 / m")
    if family in {"scatter_3d", "surface_wireframe", "area_3d"}:
        spec.update(zlabel="响应 / m", spatial_explanation="DEMO_ONLY三维真实坐标/多位置响应接口示范", companion="source_csv")
    if family == "area_3d":
        spec["series"][0]["position"] = 1; spec["series"][1]["position"] = 2
        spec.update(z_baseline=0, position_unit="m", ylabel="位置 / m")
    if family in {"pie", "donut"}:
        rows = [{"part": name, "percent": value} for name,value in [("构件甲",35),("构件乙",28),("构件丙",22),("构件丁",15)]]
        spec.pop("series"); spec.update(x="part", value="percent", composition_semantics="DEMO_ONLY互斥构件占比总和100%", display_decimals=0)
    if family == "vector_field":
        rows = [{"x": x, "y": y, "u": u, "v": v} for x,y,u,v in [(0,0,.7,.3),(1,0,.5,.6),(2,0,.3,.8),(0,1,.8,.2),(1,1,.5,.5),(2,1,.2,.6),(0,2,.7,-.1),(1,2,.4,-.2),(2,2,.2,-.4)]]
        spec.pop("series"); spec.update(x="x", y="y", u="u", v="v", xlabel="位置一 / m", ylabel="位置二 / m", vector_scale=1, vector_scale_definition="DEMO_ONLY一秒位移长度")
    if family == "step":
        spec["step_where"] = "post"
    if family == "stem":
        spec["series"] = spec["series"][:1]
    return spec, rows


def generate_demos(output_dir, pdf_python=None):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    reports = []
    for family in FAMILIES:
        folder = output_dir/family; folder.mkdir()
        spec, rows = demo_spec(family)
        with (folder/"data.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        spec_path = folder/"spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        report = render(spec_path, folder/"preview", pdf_python)
        reports.append({"family": family, "status": report["status"], "spec": str(spec_path.relative_to(output_dir)), "preview": f"{family}/preview/demo-{family}.png", "preview_sha256": sha256(folder/"preview"/f"demo-{family}.png"), "visual_review": report["visual_review"], "warnings": report["warnings"]})
    summary = {"data_status": "DEMO_ONLY_SYNTHETIC_NOT_EXPERIMENT_EVIDENCE", "families": reports}
    (output_dir/"DEMO_MANIFEST.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--schema", action="store_true", help="Print the per-family JSON field contract")
    mode.add_argument("--generate-demos", type=Path, metavar="NEW_DIR", help="Generate explicitly synthetic fixtures and previews for all families")
    mode.add_argument("--spec", type=Path, help="JSON spec; source_csv relative to its directory")
    parser.add_argument("--output-dir", type=Path, help="New immutable render directory")
    parser.add_argument("--pdf-python", type=Path, help="Python with pypdfium2 for actual PDF reopen")
    args = parser.parse_args()
    try:
        if args.schema:
            result = FAMILY_SCHEMA
        elif args.generate_demos:
            result = generate_demos(args.generate_demos, args.pdf_python)
        else:
            if not args.output_dir:
                parser.error("--spec requires --output-dir")
            result = render(args.spec, args.output_dir, args.pdf_python)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        parser.exit(2, f"render rejected: {exc}\n")


if __name__ == "__main__":
    main()
