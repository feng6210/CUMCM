#!/usr/bin/env python3
"""Render deterministic paper-style geometry/mechanism diagrams to SVG.

The spec intentionally describes semantic primitives (axes, vectors, arcs,
dimensions and projections) instead of generic flowchart nodes.  It is suited
to CUMCM mechanism figures where geometry must agree with the equations.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def color(value: str, fallback: str) -> str:
    return value if isinstance(value, str) and HEX.match(value) else fallback


def text(value) -> str:
    value = "" if value is None else str(value)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufdd0-\ufdef\ufffe\uffff]", "", value)


def xy(value, name: str):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{name} must be [x, y]")
    result = float(value[0]), float(value[1])
    if not all(math.isfinite(v) for v in result):
        raise ValueError(f"{name} must contain finite coordinates")
    return result


def marker(defs, ident: str, fill: str):
    m = SubElement(defs, "marker", {"id": ident, "markerWidth": "8", "markerHeight": "8",
                                      "refX": "7", "refY": "4", "orient": "auto",
                                      "markerUnits": "strokeWidth"})
    SubElement(m, "path", {"d": "M 0 0 L 8 4 L 0 8 z", "fill": fill})


def line(svg, a, b, stroke, width=2, dash=None, arrow=False, marker_id="arrow"):
    attrs = {"x1": f"{a[0]:.2f}", "y1": f"{a[1]:.2f}", "x2": f"{b[0]:.2f}",
             "y2": f"{b[1]:.2f}", "stroke": stroke, "stroke-width": str(width), "fill": "none"}
    if dash:
        attrs["stroke-dasharray"] = dash
    if arrow:
        attrs["marker-end"] = f"url(#{marker_id})"
    SubElement(svg, "line", attrs)


def label(svg, x, y, value, fs, fill, anchor="middle", weight="normal", rotate=None):
    attrs = {"x": f"{x:.2f}", "y": f"{y:.2f}", "font-size": str(fs), "fill": fill,
             "text-anchor": anchor, "font-weight": weight}
    if rotate is not None:
        attrs["transform"] = f"rotate({rotate:.2f} {x:.2f} {y:.2f})"
    el = SubElement(svg, "text", attrs)
    el.text = text(value)


def arc_path(cx, cy, radius, start_deg, end_deg):
    if not all(math.isfinite(v) for v in (cx, cy, radius, start_deg, end_deg)):
        raise ValueError("arc parameters must be finite")
    delta = end_deg - start_deg
    if radius <= 0 or not 0 < abs(delta) < 360:
        raise ValueError("arc requires positive radius and 0 < abs(end-start) < 360")
    a0, a1 = math.radians(start_deg), math.radians(end_deg)
    p0 = (cx + radius * math.cos(a0), cy + radius * math.sin(a0))
    p1 = (cx + radius * math.cos(a1), cy + radius * math.sin(a1))
    span = abs(delta)
    large = 1 if span > 180 else 0
    sweep = 1 if end_deg >= start_deg else 0
    return f"M {p0[0]:.2f},{p0[1]:.2f} A {radius:.2f},{radius:.2f} 0 {large} {sweep} {p1[0]:.2f},{p1[1]:.2f}", p0, p1


def validate(spec: dict):
    if not isinstance(spec, dict):
        raise ValueError("spec must be an object")
    def finite_tree(value):
        if isinstance(value, dict):
            for v in value.values(): finite_tree(v)
        elif isinstance(value, (list, tuple)):
            for v in value: finite_tree(v)
        elif isinstance(value, (float, int)) and not math.isfinite(value):
            raise ValueError("geometry numeric values must be finite")
    finite_tree(spec)
    canvas = spec.get("canvas", {})
    if canvas.get("width", 0) <= 0 or canvas.get("height", 0) <= 0:
        raise ValueError("canvas.width and canvas.height must be positive")
    for key in ("regions", "axes", "lines", "vectors", "points", "polygons", "arcs", "dimensions", "labels"):
        if not isinstance(spec.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    for i, obj in enumerate(spec.get("axes", [])):
        xy(obj.get("origin"), f"axes[{i}].origin"); xy(obj.get("x_end"), f"axes[{i}].x_end"); xy(obj.get("y_end"), f"axes[{i}].y_end")
    for group in ("lines", "vectors"):
        for i, obj in enumerate(spec.get(group, [])):
            xy(obj.get("start"), f"{group}[{i}].start"); xy(obj.get("end"), f"{group}[{i}].end")
    for group in ("vectors", "dimensions"):
        for obj in spec.get(group, []):
            if xy(obj['start'], group) == xy(obj['end'], group):
                raise ValueError(f"{group} endpoints must differ")
    for obj in spec.get('arcs', []):
        arc_path(*xy(obj['center'], 'arc.center'), float(obj['radius']), float(obj['start_deg']), float(obj['end_deg']))
    return True


def render(spec: dict) -> str:
    validate(spec)
    c = spec["canvas"]
    mode = spec.get("style", {}).get("color_mode", "monochrome")
    if mode not in {"monochrome", "color"}:
        raise ValueError("geometry style.color_mode must be monochrome or explicit color")
    st = {"font_family": "Arial, Microsoft YaHei, sans-serif", "font_size": 16,
          "bg_color": "#FFFFFF", "ink": "#263238", "axis": "#50626B",
          "accent": "#E76F51", "secondary": "#168AAD", "guide": "#90A4AE", **spec.get("style", {})}
    svg = Element("svg", {"xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {c['width']} {c['height']}",
                            "width": str(c["width"]), "height": str(c["height"]), "font-family": st["font_family"]})
    SubElement(svg, "rect", {"width": str(c["width"]), "height": str(c["height"]), "fill": color(st["bg_color"], "#FFFFFF")})
    defs = SubElement(svg, "defs")
    for hatch in ("diagonal", "cross"):
        pattern = SubElement(defs, "pattern", {"id": "hatch-" + hatch, "patternUnits": "userSpaceOnUse", "width": "10", "height": "10"})
        SubElement(pattern, "rect", {"width": "10", "height": "10", "fill": "#FFFFFF"})
        SubElement(pattern, "path", {"d": "M -2 2 L 2 -2 M 0 10 L 10 0 M 8 12 L 12 8", "fill": "none", "stroke": "#000000", "stroke-width": "0.7"})
        if hatch == "cross":
            SubElement(pattern, "path", {"d": "M -2 8 L 2 12 M 0 0 L 10 10 M 8 -2 L 12 2", "fill": "none", "stroke": "#000000", "stroke-width": "0.7"})
    marker(defs, "arrow", color(st["ink"], "#263238")); marker(defs, "arrow-accent", color(st["accent"], "#E76F51"))
    fs = float(st["font_size"])

    # Light semantic regions are drawn first, so geometry remains unobscured.
    for region in spec.get("regions", []):
        x, y, w, h = [float(region.get(k, 0)) for k in ("x", "y", "width", "height")]
        SubElement(svg, "rect", {"x": str(x), "y": str(y), "width": str(w), "height": str(h),
                                   "rx": "8", "fill": color(region.get("fill"), "#F4F8F7"),
                                   "stroke": color(region.get("stroke"), "#D5E2E0"), "stroke-width": "1",
                                   **({"data-hatch": region["hatch"]} if region.get("hatch") in {"diagonal", "cross"} else {})})
        if region.get("label"):
            label(svg, x + 10, y + 20, region["label"], fs - 2, "#60747A", "start", "bold")

    for obj in spec.get("axes", []):
        o, xe, ye = xy(obj["origin"], "origin"), xy(obj["x_end"], "x_end"), xy(obj["y_end"], "y_end")
        stroke = color(obj.get("color"), st["axis"]); line(svg, o, xe, stroke, obj.get("width", 2), arrow=True); line(svg, o, ye, stroke, obj.get("width", 2), arrow=True)
        if obj.get("x_label"): label(svg, xe[0] + 8, xe[1] + 5, obj["x_label"], fs - 1, stroke, "start")
        if obj.get("y_label"): label(svg, ye[0] - 6, ye[1] - 8, obj["y_label"], fs - 1, stroke, "end")
        if obj.get("origin_label"): label(svg, o[0] - 8, o[1] + 18, obj["origin_label"], fs - 2, stroke, "end")

    for obj in spec.get("polygons", []):
        pts = [xy(p, "polygon.point") for p in obj.get("points", [])]
        if len(pts) < 3: raise ValueError("polygon requires at least 3 points")
        SubElement(svg, "polygon", {"points": " ".join(f"{x:.2f},{y:.2f}" for x, y in pts),
                                      "fill": color(obj.get("fill"), "#D9ECE8"), "fill-opacity": str(obj.get("fill_opacity", .45)),
                                      "stroke": color(obj.get("stroke"), st["secondary"]), "stroke-width": str(obj.get("width", 2)),
                                      **({"data-hatch": obj["hatch"]} if obj.get("hatch") in {"diagonal", "cross"} else {})})

    for group in ("lines", "vectors"):
        for obj in spec.get(group, []):
            a, b = xy(obj["start"], "start"), xy(obj["end"], "end")
            stroke = color(obj.get("color"), st["accent"] if group == "vectors" else st["ink"])
            dash = {"dashed": "7,5", "dotted": "2,4"}.get(obj.get("style"))
            line(svg, a, b, stroke, obj.get("width", 2.5 if group == "vectors" else 1.8), dash, obj.get("arrow", group == "vectors"), "arrow-accent" if group == "vectors" else "arrow")
            if obj.get("label"):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                label(svg, mx + obj.get("label_dx", 0), my + obj.get("label_dy", -8), obj["label"], fs - 1, stroke)

    for obj in spec.get("dimensions", []):
        a, b = xy(obj["start"], "start"), xy(obj["end"], "end"); off = float(obj.get("offset", 14))
        dx, dy = b[0] - a[0], b[1] - a[1]; length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length * off, dx / length * off; aa, bb = (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny)
        stroke = color(obj.get("color"), st["guide"]); line(svg, a, aa, stroke, 1); line(svg, b, bb, stroke, 1); line(svg, aa, bb, stroke, 1.2, arrow=True); line(svg, bb, aa, stroke, 1.2, arrow=True)
        if obj.get("label"):
            label(svg, (aa[0] + bb[0]) / 2 + obj.get("label_dx", 0), (aa[1] + bb[1]) / 2 + obj.get("label_dy", -5), obj["label"], fs - 2, stroke)

    for obj in spec.get("arcs", []):
        cx, cy = xy(obj["center"], "center"); d, p0, p1 = arc_path(cx, cy, float(obj["radius"]), float(obj["start_deg"]), float(obj["end_deg"]))
        stroke = color(obj.get("color"), st["secondary"]); SubElement(svg, "path", {"d": d, "stroke": stroke, "stroke-width": str(obj.get("width", 2)), "fill": "none"})
        if obj.get("label"):
            mid = math.radians((float(obj["start_deg"]) + float(obj["end_deg"])) / 2); r = float(obj["radius"]) + 12
            label(svg, cx + r * math.cos(mid), cy + r * math.sin(mid), obj["label"], fs - 2, stroke)

    for obj in spec.get("points", []):
        x, y = xy(obj["xy"], "point.xy"); fill = color(obj.get("color"), st["accent"]); SubElement(svg, "circle", {"cx": str(x), "cy": str(y), "r": str(obj.get("radius", 4)), "fill": fill})
        if obj.get("label"): label(svg, x + obj.get("label_dx", 8), y + obj.get("label_dy", -8), obj["label"], fs - 1, color(obj.get("label_color"), st["ink"]), "start")

    for obj in spec.get("labels", []):
        label(svg, float(obj["x"]), float(obj["y"]), obj.get("text", ""), obj.get("font_size", fs), color(obj.get("color"), st["ink"]), obj.get("anchor", "middle"), obj.get("weight", "normal"), obj.get("rotate"))
    if mode == "monochrome":
        # Geometry-only rendering policy: imported historic colors do not leak
        # into the default. Coordinates, line styles and arrow directions stay.
        for element in svg.iter():
            if "stroke" in element.attrib and element.attrib["stroke"] != "none":
                element.set("stroke", "#000000")
            if "fill" in element.attrib and element.attrib["fill"] != "none":
                hatch = element.attrib.pop("data-hatch", None)
                fill = "url(#hatch-" + hatch + ")" if hatch else ("#FFFFFF" if element.tag in {"rect", "polygon"} else "#000000")
                element.set("fill", fill)
            element.attrib.pop("fill-opacity", None)
            element.attrib.pop("stroke-opacity", None)
            element.attrib.pop("opacity", None)
    svg.set("data-color-mode", mode)
    return tostring(svg, encoding="unicode")


def main():
    ap = argparse.ArgumentParser(description="Render paper-style geometry diagram JSON to deterministic SVG")
    ap.add_argument("spec"); ap.add_argument("--output", "-o")
    args = ap.parse_args(); spec_path = Path(args.spec); spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out = Path(args.output) if args.output else spec_path.with_suffix(".svg"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(render(spec), encoding="utf-8"); print(f"SVG written: {out}")


if __name__ == "__main__":
    main()
