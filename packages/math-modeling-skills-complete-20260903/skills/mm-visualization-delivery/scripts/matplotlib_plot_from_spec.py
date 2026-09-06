#!/usr/bin/env python3
"""Render traceable quantitative charts from CSV and JSON/YAML specifications."""
from __future__ import annotations

import argparse
import hashlib
import json
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cumcm_plot_style import (
    LINESTYLES,
    MARKERS,
    add_compact_legend,
    add_panel_label,
    choose_cjk_font,
    configure_matplotlib,
    get_palette,
    resolve_geometry,
    style_axis,
)


def load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML specifications require PyYAML") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("plot specification root must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_columns(frame: Any, columns: list[str]) -> None:
    missing = [column for column in columns if column and column not in frame.columns]
    if missing:
        raise ValueError(f"missing CSV columns: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a reproducible data chart from CSV and JSON/YAML.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    spec_path = args.spec.resolve()
    spec = load_spec(spec_path)
    source = Path(str(spec["source_csv"]))
    if not source.is_absolute():
        source = (spec_path.parent / source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    import pandas as pd

    if spec.get("title") and not bool(spec.get("allow_internal_title", False)):
        raise ValueError("paper figures must not contain an internal title; use the LaTeX caption")
    requested_font = str(spec.get("font_family", "")).strip()
    chosen_font = choose_cjk_font(font_manager, requested_font)
    base_font_pt = float(spec.get("base_font_pt", 9.0))
    configure_matplotlib(plt, chosen_font, base_font_pt)
    palette = get_palette(spec)
    used_palette = list(palette)

    frame = pd.read_csv(source)
    chart = str(spec["chart_type"]).strip().lower()
    x = str(spec.get("x", ""))
    ys = spec.get("y", [])
    if isinstance(ys, str):
        ys = [ys]
    ys = [str(item) for item in ys]
    series_labels = spec.get("series_labels", ys)
    if not isinstance(series_labels, list) or len(series_labels) != len(ys):
        raise ValueError("series_labels must be a list with the same length as y")
    series_labels = [str(item) for item in series_labels]
    group = str(spec.get("group", ""))
    yerr = str(spec.get("yerr", ""))
    if chart == "errorbar":
        if not yerr:
            raise ValueError("errorbar requires a precomputed yerr column")
        for field in ("uncertainty_type", "uncertainty_level", "sample_size_source"):
            if not spec.get(field):
                raise ValueError(f"errorbar requires {field}")
    require_columns(frame, [x, group, yerr] + ys)

    geometry = resolve_geometry(spec)
    fig, ax = plt.subplots(figsize=(geometry.width_in, geometry.height_in), constrained_layout=True)
    line_width = float(spec.get("line_width_pt", 1.25))
    marker_size = float(spec.get("marker_size_pt", 4.5))

    if chart in {"line", "scatter", "errorbar"}:
        if group:
            series = [(str(label), part) for label, part in frame.groupby(group, sort=False)]
        else:
            series = [(str(name), frame) for name in ys]
        if group:
            ycol = ys[0]
            for index, (label, part) in enumerate(series):
                color = palette[index % len(palette)]
                if chart == "line":
                    ax.plot(part[x], part[ycol], marker=MARKERS[index % len(MARKERS)],
                            linestyle=LINESTYLES[index % len(LINESTYLES)], color=color,
                            markerfacecolor="white", markeredgewidth=0.9,
                            linewidth=line_width, markersize=marker_size, label=label)
                elif chart == "scatter":
                    ax.scatter(part[x], part[ycol], alpha=0.78, label=label, color=color,
                               marker=MARKERS[index % len(MARKERS)], s=marker_size ** 2,
                               edgecolors="white", linewidths=0.35)
                else:
                    ax.errorbar(part[x], part[ycol], yerr=part[yerr], color=color,
                                marker=MARKERS[index % len(MARKERS)], markerfacecolor="white",
                                linewidth=line_width, markersize=marker_size, capsize=2.5,
                                elinewidth=0.9, label=label)
        else:
            for index, ycol in enumerate(ys):
                color = palette[index % len(palette)]
                if chart == "line":
                    ax.plot(frame[x], frame[ycol], marker=MARKERS[index % len(MARKERS)],
                            linestyle=LINESTYLES[index % len(LINESTYLES)], color=color,
                            markerfacecolor="white", markeredgewidth=0.9,
                            linewidth=line_width, markersize=marker_size, label=series_labels[index])
                elif chart == "scatter":
                    ax.scatter(frame[x], frame[ycol], alpha=0.78, color=color,
                               marker=MARKERS[index % len(MARKERS)], s=marker_size ** 2,
                               edgecolors="white", linewidths=0.35, label=series_labels[index])
                else:
                    ax.errorbar(frame[x], frame[ycol], yerr=frame[yerr], color=color,
                                marker=MARKERS[index % len(MARKERS)], markerfacecolor="white",
                                linewidth=line_width, markersize=marker_size, capsize=2.5,
                                elinewidth=0.9, label=series_labels[index])
    elif chart in {"bar", "horizontal_bar", "grouped_bar", "stacked_bar"}:
        positions = np.arange(len(frame))
        if chart == "horizontal_bar":
            ax.barh(positions, frame[ys[0]], color=palette[0], height=0.62, edgecolor="none")
            ax.set_yticks(positions, frame[x].astype(str))
            ax.invert_yaxis()
        elif chart == "bar" or len(ys) == 1:
            ax.bar(positions, frame[ys[0]], label=series_labels[0], color=palette[0], width=0.66, edgecolor="none")
        elif chart == "stacked_bar":
            bottom = np.zeros(len(frame))
            for index, ycol in enumerate(ys):
                ax.bar(positions, frame[ycol], bottom=bottom, label=series_labels[index],
                       color=palette[index % len(palette)], width=0.68, edgecolor="white", linewidth=0.35)
                bottom += frame[ycol].to_numpy(dtype=float)
        else:
            width_each = 0.8 / len(ys)
            for index, ycol in enumerate(ys):
                ax.bar(positions - 0.4 + width_each / 2 + index * width_each,
                       frame[ycol], width_each, label=series_labels[index],
                       color=palette[index % len(palette)], edgecolor="none")
        if chart != "horizontal_bar":
            ax.set_xticks(positions, frame[x].astype(str), rotation=float(spec.get("x_tick_rotation", 0)))
    elif chart in {"dumbbell", "slope"}:
        if len(ys) != 2:
            raise ValueError(f"{chart} requires exactly two y columns")
        positions = np.arange(len(frame))
        first = frame[ys[0]].to_numpy(dtype=float)
        second = frame[ys[1]].to_numpy(dtype=float)
        for row, (left, right) in enumerate(zip(first, second)):
            ax.plot([left, right], [row, row], color="#AAB5BD", linewidth=1.4, zorder=1)
        ax.scatter(first, positions, facecolors="white", s=marker_size ** 2 * 1.55,
                   edgecolors=palette[0], linewidths=1.15, marker="o",
                   label=series_labels[0], zorder=2)
        ax.scatter(second, positions, color=palette[1], s=marker_size ** 2 * 1.55,
                   edgecolors="white", linewidths=0.5, marker="D",
                   label=series_labels[1], zorder=3)
        category_labels = spec.get("category_labels")
        if category_labels is None:
            prefix = str(spec.get("category_prefix", ""))
            category_labels = [f"{prefix}{value}" for value in frame[x].astype(str)]
        if not isinstance(category_labels, list) or len(category_labels) != len(frame):
            raise ValueError("category_labels must match the number of source rows")
        ax.set_yticks(positions, [str(value) for value in category_labels])
        ax.invert_yaxis()
    elif chart == "histogram":
        for index, ycol in enumerate(ys):
            ax.hist(frame[ycol].dropna(), bins=int(spec.get("bins", 20)), alpha=0.48,
                    color=palette[index % len(palette)], label=series_labels[index], edgecolor="white", linewidth=0.4)
    elif chart == "box":
        if spec.get("precomputed_box"):
            summary_fields = ["q1", "median", "q3", "whislo", "whishi"]
            require_columns(frame, summary_fields + [x])
            values = frame[summary_fields].to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError("precomputed box summaries must be finite")
            if not ((frame.whislo <= frame.q1) & (frame.q1 <= frame["median"]) &
                    (frame["median"] <= frame.q3) & (frame.q3 <= frame.whishi)).all():
                raise ValueError("invalid precomputed quartile/whisker order")
            if not spec.get("summary_definition"):
                raise ValueError("precomputed_box requires upstream summary_definition")
            summaries = [{**{k:float(row[k]) for k in summary_fields},
                          "med":float(row["median"]), "label":str(row[x]),"fliers":[]} for _,row in frame.iterrows()]
            boxes = ax.bxp(summaries, showfliers=False, patch_artist=True,
                           medianprops={"color":"#20272C","linewidth":1.1})
        else:
            boxes = ax.boxplot([frame[ycol].dropna() for ycol in ys], tick_labels=series_labels,
                           showmeans=True, patch_artist=True,
                           medianprops={"color": "#20272C", "linewidth": 1.1},
                           meanprops={"marker": "D", "markerfacecolor": "white",
                                      "markeredgecolor": "#20272C", "markersize": 3.5},
                           flierprops={"marker": "o", "markerfacecolor": "#5F6B73",
                                      "markeredgecolor": "none", "markersize": 2.5, "alpha": 0.55})
        for index, patch in enumerate(boxes["boxes"]):
            cycle = int(spec.get("box_color_cycle", len(palette)))
            if cycle < 1 or cycle > len(palette):
                raise ValueError("box_color_cycle outside palette")
            patch.set_facecolor(palette[index % cycle])
            patch.set_alpha(0.72)
            patch.set_edgecolor("#39434A")
    elif chart == "violin":
        parts = ax.violinplot([frame[ycol].dropna() for ycol in ys], showmeans=False,
                              showmedians=True, showextrema=False)
        for index, body in enumerate(parts["bodies"]):
            body.set_facecolor(palette[index % len(palette)])
            body.set_edgecolor("#39434A")
            body.set_alpha(0.65)
        ax.set_xticks(range(1, len(ys) + 1), series_labels)
    elif chart == "heatmap":
        if spec.get("correlation"):
            raise ValueError(
                "correlation must be precomputed and validated; the renderer only draws supplied values"
            )
        matrix = frame[ys]
        matrix_values = matrix.to_numpy(dtype=float)
        if not np.isfinite(matrix_values).all():
            raise ValueError("heatmap values must all be finite")
        matrix_semantics = str(spec.get("matrix_semantics", "generic")).strip().lower()
        default_cmap = "coolwarm" if matrix_semantics == "correlation" else "cividis"
        vmin = spec.get("vmin")
        vmax = spec.get("vmax")
        if matrix_semantics == "correlation" and (vmin != -1 or vmax != 1):
            raise ValueError("correlation heatmaps require fixed vmin=-1 and vmax=1")
        if matrix_semantics == "correlation" and np.any(np.abs(matrix_values) > 1 + 1e-12):
            raise ValueError("correlation heatmap values must be within [-1, 1]")
        actual_cmap = str(spec.get("cmap", default_cmap))
        used_palette = [actual_cmap]
        image = ax.imshow(matrix_values, aspect="auto", cmap=actual_cmap, vmin=vmin, vmax=vmax)
        ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(matrix.index)), matrix.index)
        fig.colorbar(image, ax=ax, label=str(spec.get("colorbar_label", "")))
        if bool(spec.get("annotate_cells", False)) and matrix.size <= 100:
            decimals = int(spec.get("decimal_places", 2))
            for row in range(matrix.shape[0]):
                for column in range(matrix.shape[1]):
                    value = float(matrix.iloc[row, column])
                    ax.text(column, row, f"{value:.{decimals}f}", ha="center", va="center", fontsize=base_font_pt - 1)
    elif chart == "area":
        if spec.get("area_mode") == "single_outline":
            if len(ys) != 1:
                raise ValueError("single_outline area requires exactly one supplied series")
            ax.fill_between(frame[x], 0, frame[ys[0]], color=palette[0], alpha=0.22)
            ax.plot(frame[x], frame[ys[0]], color=palette[0], linewidth=line_width,
                    label=series_labels[0])
        else:
            ax.stackplot(frame[x], *[frame[ycol] for ycol in ys], labels=series_labels,
                         colors=palette[:len(ys)], alpha=0.72, linewidth=0.35)
    else:
        raise ValueError(f"unsupported chart_type: {chart}")

    ax.set_xlabel(str(spec.get("xlabel", x)))
    ax.set_ylabel(str(spec.get("ylabel", "")))
    if bool(spec.get("zero_baseline", False)):
        ax.set_ylim(bottom=0)
    grid_axis = "x" if chart in {"horizontal_bar", "dumbbell", "slope"} else "y"
    style_axis(ax, grid_axis=grid_axis, show_grid=bool(spec.get("grid", True)))
    add_panel_label(ax, str(spec.get("panel_label", "")))
    if (group or len(ys) > 1) and chart != "heatmap":
        add_compact_legend(ax, n_series=(frame[group].nunique() if group else len(ys)),
                           location=str(spec.get("legend_strategy", "top")))

    if bool(spec.get("direct_labels", False)) and chart in {"bar", "horizontal_bar"}:
        decimals = int(spec.get("decimal_places", 2))
        for patch in ax.patches:
            if chart == "horizontal_bar":
                ax.annotate(f"{patch.get_width():.{decimals}f}",
                            (patch.get_width(), patch.get_y() + patch.get_height() / 2),
                            xytext=(3, 0), textcoords="offset points", va="center", ha="left",
                            fontsize=base_font_pt - 0.5, color="#39434A")
            else:
                ax.annotate(f"{patch.get_height():.{decimals}f}",
                            (patch.get_x() + patch.get_width() / 2, patch.get_height()),
                            xytext=(0, 3), textcoords="offset points", va="bottom", ha="center",
                            fontsize=base_font_pt - 0.5, color="#39434A")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = str(spec.get("figure_id", spec_path.stem))
    outputs = []
    render_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for suffix in ("pdf", "svg", "png"):
            output = args.output_dir / f"{stem}.{suffix}"
            fig.savefig(output, dpi=300 if suffix == "png" else None, metadata={"Creator": "mm-visualization-delivery"})
            outputs.append(output)
        render_warnings.extend(str(item.message) for item in caught)
    plt.close(fig)

    if outputs[0].read_bytes()[:4] != b"%PDF":
        raise RuntimeError("PDF output cannot be reopened")
    ET.parse(outputs[1])
    raster = plt.imread(outputs[2])
    if raster.size == 0:
        raise RuntimeError("PNG output cannot be reopened")

    manifest_path = args.manifest or (args.output_dir / f"{stem}.manifest.json")
    style_to_palette = {
        "cumcm-clean": "cumcm-muted",
        "cumcm-highlight": "cumcm-highlight",
        "cumcm-data-dense": "cumcm-cool",
        "cumcm-vivid": "cumcm-vivid",
    }
    style_profile = str(spec.get("style_profile", "cumcm-vivid"))
    palette_profile = str(spec.get("palette_profile", style_to_palette.get(style_profile, "cumcm-muted")))
    effective_line_width = {
        "line": line_width, "line_chart": line_width, "errorbar": line_width,
        "scatter": 0.35, "bar": 0.35, "horizontal_bar": 0.35,
        "grouped_bar": 0.35, "stacked_bar": 0.35, "dumbbell": 1.4,
        "slope": 1.4, "histogram": 0.4, "box": 1.1, "boxplot": 1.1,
        "violin": 1.0, "heatmap": 0.8, "area": 0.35,
    }.get(chart, line_width)
    if chart == "area" and spec.get("area_mode") == "single_outline":
        effective_line_width = line_width
    actual_effects = ["transparent_fill"] if chart in {
        "scatter", "histogram", "box", "boxplot", "violin", "area"
    } else ["none"]
    series_color_mapping = {str(label): palette[index % len(palette)]
                            for index, label in enumerate(series_labels)}
    if chart == "box" and spec.get("precomputed_box"):
        series_color_mapping = {
            str(label): palette[index % int(spec.get("box_color_cycle", len(palette)))]
            for index, label in enumerate(frame[x])}
    manifest = {
        "renderer": "matplotlib_plot_from_spec",
        "semantic_claim_validation": False,
        "status": "RUNTIME_VERIFIED",
        "spec": {"path": spec_path.name, "sha256": sha256(spec_path)},
        "source": {"path": source.name, "sha256": sha256(source), "rows": int(len(frame))},
        "render_contract": {
            "chart_type": chart,
            "variables": [str(x)] + ([str(group)] if group else []) + [str(name) for name in ys],
            "transformations": spec.get("transformations", "none"),
            "source_sha256": sha256(source),
            "spec_sha256": sha256(spec_path),
        },
        "outputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in outputs],
        "style": {
            "style_profile": style_profile,
            "palette_profile": palette_profile,
            "effective_palette": used_palette,
            "series_color_mapping": {} if chart == "heatmap" else series_color_mapping,
            "size_profile": str(spec.get("size_profile", "full-width")),
            "base_font_pt": base_font_pt,
            "effective_min_font_pt": base_font_pt - (1.0 if chart == "heatmap" else 0.5),
            "font_family": chosen_font or "",
            "final_width_mm": round(geometry.width_in * 25.4, 3),
            "line_width_pt": effective_line_width,
            "decorative_effects": actual_effects,
            "legend_strategy": (
                str(spec.get("legend_strategy", "top"))
                if (group or len(ys) > 1) and chart != "heatmap" else "none"
            ),
            "internal_title": False,
        },
        "environment": {"matplotlib": matplotlib.__version__, "pandas": pd.__version__, "font_family": chosen_font or None},
        "reopen_check": {"pdf": True, "svg": True, "png": True},
        "warnings": render_warnings + (["No installed CJK font was selected."] if not chosen_font else []) + [
            "RUNTIME_VERIFIED is not EVIDENCE_ELIGIBLE; run claim, numeric, and visual audits."
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
