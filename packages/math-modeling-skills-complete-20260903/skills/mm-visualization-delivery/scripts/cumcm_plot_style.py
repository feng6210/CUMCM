#!/usr/bin/env python3
"""Deterministic CUMCM publication style helpers for Matplotlib.

This module is an original local implementation distilled from visual review of
the user's plotting corpus.  It intentionally contains no copied third-party
source code and has no runtime dependency on that corpus.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PALETTES: dict[str, list[str]] = {
    "cumcm-muted": ["#2F5D7C", "#D9822B", "#4C956C", "#8A6FB0", "#C65D57", "#5F6B73"],
    "cumcm-cool": ["#244B6B", "#4F86A6", "#7DB7C5", "#91A88A", "#C0A35A", "#8C6D62"],
    "cumcm-highlight": ["#AAB4BD", "#3C8D6B", "#D9822B", "#2F5D7C", "#8A6FB0", "#C65D57"],
    "cumcm-diverging": ["#2F5D7C", "#7FA6BF", "#E9EEF2", "#F3D0AE", "#C6652D"],
    "cumcm-vivid": ["#2A9D8F", "#E76F51", "#E9C46A", "#457B9D", "#9B5DE5", "#F15BB5"],
}

MARKERS = ["o", "s", "^", "D", "v", "P"]
LINESTYLES = ["-", "--", "-.", ":"]


@dataclass(frozen=True)
class FigureGeometry:
    width_in: float
    height_in: float


GEOMETRIES: dict[str, FigureGeometry] = {
    "single-column": FigureGeometry(3.35, 2.35),
    "medium": FigureGeometry(4.80, 3.10),
    "full-width": FigureGeometry(6.30, 3.75),
    "wide": FigureGeometry(6.30, 3.10),
    "square": FigureGeometry(4.20, 4.20),
}


def choose_cjk_font(font_manager: Any, requested: str = "") -> str:
    """Choose an installed Chinese-capable font without network access."""
    candidates = [
        requested.strip(),
        "Microsoft YaHei",
        "Microsoft JhengHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Arial Unicode MS",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    return next((name for name in candidates if name and name in available), "")


def resolve_geometry(spec: dict[str, Any]) -> FigureGeometry:
    profile = str(spec.get("size_profile", "full-width"))
    base = GEOMETRIES.get(profile, GEOMETRIES["full-width"])
    width = float(spec.get("width_in", base.width_in))
    height = float(spec.get("height_in", base.height_in))
    if width <= 0 or height <= 0:
        raise ValueError("figure width and height must be positive")
    return FigureGeometry(width, height)


def configure_matplotlib(plt: Any, font_name: str, base_font_pt: float = 9.0) -> None:
    """Apply restrained, print-safe defaults before creating a figure."""
    base_font_pt = max(float(base_font_pt), 7.0)
    if font_name:
        plt.rcParams["font.sans-serif"] = [font_name]
        plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.size": base_font_pt,
            "axes.labelsize": base_font_pt,
            "xtick.labelsize": base_font_pt - 0.5,
            "ytick.labelsize": base_font_pt - 0.5,
            "legend.fontsize": base_font_pt - 0.5,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.25,
            "lines.markersize": 4.5,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def get_palette(spec: dict[str, Any]) -> list[str]:
    custom = spec.get("palette")
    if isinstance(custom, list) and custom:
        return [str(color) for color in custom]
    style_to_palette = {
        "cumcm-clean": "cumcm-muted",
        "cumcm-highlight": "cumcm-highlight",
        "cumcm-data-dense": "cumcm-cool",
        "cumcm-vivid": "cumcm-vivid",
    }
    style_profile = str(spec.get("style_profile", "cumcm-clean"))
    profile = str(spec.get("palette_profile", style_to_palette.get(style_profile, "cumcm-muted")))
    return PALETTES.get(profile, PALETTES["cumcm-muted"])


def style_axis(ax: Any, *, grid_axis: str = "y", show_grid: bool = True) -> None:
    """Create a quiet visual hierarchy while retaining readable axes."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#39434A")
    ax.spines["bottom"].set_color("#39434A")
    ax.tick_params(colors="#39434A", pad=3)
    ax.xaxis.label.set_color("#20272C")
    ax.yaxis.label.set_color("#20272C")
    ax.set_axisbelow(True)
    if show_grid:
        ax.grid(axis=grid_axis, color="#D9E0E5", linewidth=0.55, alpha=0.75)
    else:
        ax.grid(False)


def add_panel_label(ax: Any, label: str) -> None:
    if label:
        ax.text(
            -0.11,
            1.04,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=ax.xaxis.label.get_size(),
            fontweight="bold",
            color="#20272C",
        )


def add_compact_legend(ax: Any, *, n_series: int, location: str = "top") -> None:
    if n_series <= 0:
        return
    if location == "none":
        return
    if location == "direct":
        raise ValueError("direct legend strategy requires chart-specific end labels")
    ncol = min(max(n_series, 1), 3)
    if location == "right":
        ax.legend(frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5), borderaxespad=0)
    elif location == "inside":
        ax.legend(frameon=False, loc="best", handlelength=1.8, handletextpad=0.5)
    else:
        ax.legend(
            frameon=False,
            loc="lower center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=ncol,
            borderaxespad=0,
            handlelength=1.8,
            columnspacing=1.2,
            handletextpad=0.5,
        )
