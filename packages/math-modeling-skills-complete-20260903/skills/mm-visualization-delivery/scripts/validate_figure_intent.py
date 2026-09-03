#!/usr/bin/env python3
"""Validate FIGURE_INTENT JSON/YAML without judging scientific claims."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "figure_id",
    "question_id",
    "purpose",
    "claim_id",
    "source_data",
    "variables",
    "units",
    "transformations",
    "chart_or_diagram_type",
    "backend_preference",
    "editable_output",
    "latex_output",
    "caption_zh",
    "narrative_role",
    "reader_takeaway",
    "exact_values_location",
    "visual_grammar_group",
    "visual_grammar",
    "placement",
)

NARRATIVE_ROLES = {"orientation", "mechanism", "evidence", "validation"}
PLACEMENTS = {"body", "appendix"}
EXACT_VALUE_LOCATIONS = {
    "result_table", "machine_readable_table", "figure_annotation", "caption", "not_applicable"
}
VISUAL_GRAMMAR_FIELDS = {
    "font_family", "base_font_pt", "palette", "line_width_pt", "style_profile",
    "final_width_mm", "legend_strategy", "precision_policy", "decorative_effects",
}
STYLE_PROFILES = {
    "cumcm-clean", "cumcm-highlight", "cumcm-data-dense", "cumcm-vivid", "cumcm-mechanism"
}
LEGEND_STRATEGIES = {"top", "right", "inside", "direct", "none"}
PATH_KEYS = {"file", "path", "source", "source_file", "files", "paths", "source_files"}
SINGULAR_PATH_KEYS = {"file", "path", "source", "source_file"}
COVERAGE_SLOTS = {
    "data_diagnosis", "mechanism", "main_result", "comparison", "validation", "robustness"
}
MANDATORY_COVERAGE_SLOTS = {"main_result", "validation"}
MIN_DISTINCT_FIGURES_PER_QUESTION = 4
SLOT_ALLOWED_ROLES = {
    "data_diagnosis": {"orientation", "evidence"},
    "mechanism": {"mechanism"},
    "main_result": {"evidence"},
    "comparison": {"evidence"},
    "validation": {"validation"},
    "robustness": {"validation"},
}

DATA_TYPES = {
    "line", "line_chart", "scatter", "scatter_plot", "bar", "bar_chart",
    "horizontal_bar", "grouped_bar", "stacked_bar", "box", "boxplot",
    "violin", "histogram", "density", "heatmap", "trajectory", "map", "contour",
    "errorbar", "area", "scatter_matrix", "vector_field", "pareto",
    "dumbbell", "slope", "interval_band",
    "radar", "pie", "donut", "dual_axis", "surface_3d", "bar_3d",
    "sensitivity", "convergence", "data_plot",
}
DIAGRAM_TYPES = {
    "flowchart", "workflow", "architecture", "structural", "state_machine",
    "sequence", "network", "topology", "decision_tree", "mechanism", "diagram",
}
DATA_BACKENDS = {"origin", "matlab", "python", "python/matplotlib", "matplotlib"}
DIAGRAM_BACKENDS = {
    "visio", "figurespec", "figurespec/svg", "svg", "mermaid",
}
ZH_RE = re.compile(r"[\u3400-\u9fff]")


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "YAML input requires PyYAML; use JSON or install PyYAML in the active environment."
        ) from exc
    return yaml.safe_load(text)


def normalize_entries(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        entries = document
    elif isinstance(document, dict) and isinstance(document.get("figures"), list):
        entries = document["figures"]
    elif isinstance(document, dict) and "figure_id" in document:
        entries = [document]
    else:
        raise ValueError("Root must be a figure object, a list, or an object with a 'figures' list.")
    if not all(isinstance(item, dict) for item in entries):
        raise ValueError("Every figure entry must be an object.")
    return entries


def collect_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        found: list[str] = []
        for child in value:
            found.extend(collect_string_values(child))
        return found
    return []


def collect_paths(value: Any) -> list[str]:
    """Collect only values under explicit path keys, never hashes or metadata."""
    found: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            if str(child_key).lower() in PATH_KEYS:
                found.extend(collect_string_values(child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_paths(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                found.extend(collect_paths(child))
    return found


def declared_hash_for_path(value: Any, source_path: str, total_paths: int) -> str:
    """Return the hash colocated with a source path or mapped by exact path text."""
    if not isinstance(value, (dict, list)):
        return ""
    if isinstance(value, list):
        for child in value:
            declared = declared_hash_for_path(child, source_path, total_paths)
            if declared:
                return declared
        return ""

    direct_paths: list[str] = []
    for key, child in value.items():
        if str(key).lower() in SINGULAR_PATH_KEYS:
            direct_paths.extend(collect_string_values(child))
    if source_path in direct_paths:
        declared = value.get("sha256", "")
        if isinstance(declared, str):
            return declared.strip().lower()

    declared_map = value.get("sha256")
    if isinstance(declared_map, dict):
        mapped = declared_map.get(source_path, "")
        if isinstance(mapped, str):
            return mapped.strip().lower()
    hash_map = value.get("hashes")
    if isinstance(hash_map, dict):
        mapped = hash_map.get(source_path, "")
        if isinstance(mapped, str):
            return mapped.strip().lower()

    if total_paths == 1 and isinstance(value.get("sha256"), str):
        return str(value["sha256"]).strip().lower()

    for child in value.values():
        if isinstance(child, (dict, list)):
            declared = declared_hash_for_path(child, source_path, total_paths)
            if declared:
                return declared
    return ""


def nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def specific_reason(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) >= 8 and text.lower() not in {"n/a", "na", "none", "not applicable", "不适用"}


def normalized_claim_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return {stripped} if stripped else set()
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def figure_content_signature(entry: dict[str, Any]) -> str:
    """Build a deterministic proxy for detecting main/validation duplicate plots."""
    source_data = entry.get("source_data")
    source_paths = collect_paths(source_data)
    source_hashes = sorted(
        declared_hash_for_path(source_data, source, len(source_paths))
        for source in source_paths
    )
    payload = {
        "source_hashes": source_hashes,
        "variables": entry.get("variables"),
        "transformations": entry.get("transformations"),
        "chart_or_diagram_type": str(entry.get("chart_or_diagram_type", "")).lower(),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def basic_output_reopen_error(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        data = path.read_bytes()
        if len(data) < 256 or not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            return "does not contain a complete PDF header/body/EOF structure"
    elif suffix == ".png":
        data = path.read_bytes()
        if len(data) < 64 or not data.startswith(b"\x89PNG\r\n\x1a\n") or b"IEND" not in data[-64:]:
            return "does not contain a complete PNG signature/IEND structure"
    elif suffix == ".vsdx":
        if not zipfile.is_zipfile(path):
            return "is not a reopenable OOXML ZIP package"
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or "visio/document.xml" not in archive.namelist():
                return "has a corrupt or incomplete Visio package"
    elif suffix == ".opju":
        data = path.read_bytes()
        if len(data) < 1024 or not data.startswith(b"CPYUA"):
            return "does not resemble a complete Origin project"
    elif suffix == ".fig":
        data = path.read_bytes()
        if len(data) < 1024 or not (data.startswith(b"MATLAB") or data.startswith(b"\x89HDF")):
            return "does not resemble a complete MATLAB figure"
    return None


def report_output_hashes(report: Any) -> set[str]:
    hashes: set[str] = set()
    if not isinstance(report, dict):
        return hashes
    for key in ("opju_sha256", "vsdx_sha256", "pdf_sha256"):
        value = report.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
            hashes.add(value.lower())
    outputs = report.get("outputs")
    if isinstance(outputs, list):
        for item in outputs:
            if isinstance(item, dict):
                value = item.get("sha256")
                if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
                    hashes.add(value.lower())
    spec = report.get("spec")
    if isinstance(spec, dict):
        value = spec.get("sha256")
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
            hashes.add(value.lower())
    return hashes


def validate_backend_report(
    entry: dict[str, Any], prefix: str, base_dir: Path,
    editable_hash: str, latex_hash: str,
) -> list[str]:
    errors: list[str] = []
    report_value = entry.get("backend_report")
    if not isinstance(report_value, str) or not report_value.strip():
        return [f"{prefix}.backend_report: required in final output mode"]
    report_path = Path(report_value)
    if not report_path.is_absolute():
        report_path = base_dir / report_path
    if not report_path.is_file():
        return [f"{prefix}.backend_report: missing file {report_path}"]
    declared_report_hash = str(entry.get("backend_report_sha256", "")).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", declared_report_hash):
        errors.append(f"{prefix}.backend_report_sha256: required as 64 hexadecimal characters")
    elif file_sha256(report_path) != declared_report_hash:
        errors.append(f"{prefix}.backend_report_sha256: does not match {report_path}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"{prefix}.backend_report: unreadable JSON: {type(exc).__name__}: {exc}")
        return errors

    backend = str(entry.get("backend_preference", "")).strip().lower()
    status = str(report.get("status", "")).upper()
    allowed_statuses = {"PASSED", "RUNTIME_VERIFIED"}
    if status not in allowed_statuses:
        errors.append(f"{prefix}.backend_report.status: expected {sorted(allowed_statuses)}, got '{status}'")
    hashes = report_output_hashes(report)
    for label, output_hash in (("editable", editable_hash), ("latex", latex_hash)):
        if output_hash and output_hash not in hashes:
            errors.append(
                f"{prefix}.backend_report: {label} output hash is not recorded by the runtime report"
            )

    grammar = entry.get("visual_grammar") if isinstance(entry.get("visual_grammar"), dict) else {}
    declared_style = str(grammar.get("style_profile", "")).strip().lower()
    report_style_object = report.get("style") if isinstance(report.get("style"), dict) else report
    reported_style = str(report_style_object.get("style_profile", "")).strip().lower()
    if declared_style and reported_style != declared_style:
        errors.append(
            f"{prefix}.backend_report.style_profile: runtime '{reported_style}' does not match "
            f"declared '{declared_style}'"
        )
    if backend in DATA_BACKENDS:
        declared_palette = grammar.get("palette")
        reported_palette = report_style_object.get("effective_palette")
        if isinstance(reported_palette, str) and reported_palette.strip():
            reported_palette = [reported_palette]
        if not isinstance(reported_palette, list) or not reported_palette:
            errors.append(f"{prefix}.backend_report.effective_palette: required for data backends")
        elif isinstance(declared_palette, list):
            normalized_declared = [str(color).strip().upper() for color in declared_palette]
            normalized_reported = [str(color).strip().upper() for color in reported_palette]
            if normalized_reported[: len(normalized_declared)] != normalized_declared:
                errors.append(
                    f"{prefix}.backend_report.effective_palette: does not match visual_grammar.palette"
                )
        declared_effects = {
            str(effect).strip().lower() for effect in grammar.get("decorative_effects", [])
        }
        reported_effects_value = report_style_object.get("decorative_effects")
        reported_effects = {
            str(effect).strip().lower()
            for effect in reported_effects_value
        } if isinstance(reported_effects_value, list) else set()
        if reported_effects != declared_effects:
            errors.append(
                f"{prefix}.backend_report.decorative_effects: actual renderer effects must "
                "match visual_grammar.decorative_effects"
            )

    if backend in {"matlab", "python", "python/matplotlib", "matplotlib"}:
        renderer_spec = entry.get("renderer_spec")
        renderer_spec_paths = collect_paths(renderer_spec)
        if not isinstance(renderer_spec, dict) or len(renderer_spec_paths) != 1:
            errors.append(
                f"{prefix}.renderer_spec: exactly one hash-bound renderer spec is required"
            )
            declared_spec_hash = ""
        else:
            declared_spec_hash = declared_hash_for_path(renderer_spec, renderer_spec_paths[0], 1)
            spec_path = Path(renderer_spec_paths[0])
            if not spec_path.is_absolute():
                spec_path = base_dir / spec_path
            if not re.fullmatch(r"[0-9a-f]{64}", declared_spec_hash):
                errors.append(f"{prefix}.renderer_spec.sha256: required as 64 hexadecimal characters")
            elif not spec_path.is_file() or file_sha256(spec_path) != declared_spec_hash:
                errors.append(f"{prefix}.renderer_spec.sha256: does not match renderer spec file")
        report_spec = report.get("spec")
        report_spec_hash = str(report_spec.get("sha256", "")).lower() if isinstance(
            report_spec, dict
        ) else ""
        if declared_spec_hash and report_spec_hash != declared_spec_hash:
            errors.append(
                f"{prefix}.backend_report.spec.sha256: does not match renderer_spec.sha256"
            )
        contract = report.get("render_contract")
        if not isinstance(contract, dict):
            errors.append(f"{prefix}.backend_report.render_contract: required")
        else:
            declared_chart = str(entry.get("chart_or_diagram_type", "")).strip().lower()
            contract_chart = str(contract.get("chart_type", "")).strip().lower()
            chart_aliases = {"line_chart": "line", "scatter_plot": "scatter", "boxplot": "box"}
            if chart_aliases.get(declared_chart, declared_chart) != chart_aliases.get(
                contract_chart, contract_chart
            ):
                errors.append(
                    f"{prefix}.backend_report.render_contract.chart_type: does not match intent"
                )
            declared_variables = [str(value) for value in entry.get("variables", [])]
            contract_variables = [str(value) for value in contract.get("variables", [])] if isinstance(
                contract.get("variables"), list
            ) else []
            if declared_variables != contract_variables:
                errors.append(
                    f"{prefix}.backend_report.render_contract.variables: does not match intent"
                )
            declared_transform = json.dumps(
                entry.get("transformations"), ensure_ascii=False, sort_keys=True
            )
            contract_transform = json.dumps(
                contract.get("transformations"), ensure_ascii=False, sort_keys=True
            )
            if declared_transform != contract_transform:
                errors.append(
                    f"{prefix}.backend_report.render_contract.transformations: does not match intent"
                )
        numeric_pairs = (
            ("final_width_mm", "final_width_mm", 0.05),
            ("line_width_pt", "line_width_pt", 0.01),
            ("base_font_pt", "base_font_pt", 0.01),
        )
        for grammar_field, report_field, tolerance in numeric_pairs:
            declared_value = grammar.get(grammar_field)
            reported_value = report_style_object.get(report_field)
            if not isinstance(declared_value, (int, float)) or not isinstance(
                reported_value, (int, float)
            ) or abs(float(declared_value) - float(reported_value)) > tolerance:
                errors.append(
                    f"{prefix}.backend_report.{report_field}: must match "
                    f"visual_grammar.{grammar_field}"
                )
        effective_font = report_style_object.get("effective_min_font_pt")
        if not isinstance(effective_font, (int, float)) or float(effective_font) < 7:
            errors.append(
                f"{prefix}.backend_report.effective_min_font_pt: must be at least 7 pt at final width"
            )
        declared_font = str(grammar.get("font_family", "")).strip().casefold()
        reported_font = str(report_style_object.get("font_family", "")).strip().casefold()
        if not reported_font or reported_font != declared_font:
            errors.append(
                f"{prefix}.backend_report.font_family: runtime font must match visual_grammar.font_family"
            )
        declared_legend = str(grammar.get("legend_strategy", "")).strip().lower()
        reported_legend = str(report_style_object.get("legend_strategy", "")).strip().lower()
        if reported_legend != declared_legend:
            errors.append(
                f"{prefix}.backend_report.legend_strategy: runtime legend must match "
                "visual_grammar.legend_strategy"
            )

    if backend == "origin":
        for field in (
            "project_saved", "pdf_exported", "project_reopened", "pdf_reopened",
            "metadata_sanitized", "anonymous_check",
        ):
            if report.get(field) is not True:
                errors.append(f"{prefix}.backend_report.{field}: must be true for Origin")
        effective_font = report.get("effective_min_font_pt")
        if not isinstance(effective_font, (int, float)) or float(effective_font) < 7:
            errors.append(
                f"{prefix}.backend_report.effective_min_font_pt: must be at least 7 pt at final width"
            )
        declared_width = grammar.get("final_width_mm")
        reported_width = report.get("final_width_mm")
        if not isinstance(reported_width, (int, float)) or not isinstance(declared_width, (int, float)) or (
            abs(float(reported_width) - float(declared_width)) > 0.01
        ):
            errors.append(
                f"{prefix}.backend_report.final_width_mm: must match visual_grammar.final_width_mm"
            )
    elif backend == "visio":
        for field in (
            "document_saved", "pdf_exported", "document_reopened", "pdf_reopened",
            "metadata_sanitized", "anonymous_check",
        ):
            if report.get(field) is not True:
                errors.append(f"{prefix}.backend_report.{field}: must be true for Visio")
        if int(report.get("unsupported_groups", 0) or 0) != 0:
            errors.append(f"{prefix}.backend_report.unsupported_groups: must be zero")
        effective_font = report.get("effective_min_font_pt")
        if not isinstance(effective_font, (int, float)) or float(effective_font) < 7:
            errors.append(
                f"{prefix}.backend_report.effective_min_font_pt: must be at least 7 pt at final width"
            )
        for grammar_field, report_field, tolerance in (
            ("final_width_mm", "final_width_mm", 0.05),
            ("base_font_pt", "base_font_pt", 0.05),
            ("line_width_pt", "line_width_pt", 0.05),
        ):
            declared_value = grammar.get(grammar_field)
            reported_value = report.get(report_field)
            if not isinstance(declared_value, (int, float)) or not isinstance(
                reported_value, (int, float)
            ) or abs(float(declared_value) - float(reported_value)) > tolerance:
                errors.append(
                    f"{prefix}.backend_report.{report_field}: must match "
                    f"visual_grammar.{grammar_field}"
                )
        if str(report.get("legend_strategy", "")).lower() != str(
            grammar.get("legend_strategy", "")
        ).lower():
            errors.append(f"{prefix}.backend_report.legend_strategy: must match visual grammar")
        declared_effects = {
            str(effect).strip().lower() for effect in grammar.get("decorative_effects", [])
        }
        reported_effects = {
            str(effect).strip().lower() for effect in report.get("decorative_effects", [])
        } if isinstance(report.get("decorative_effects"), list) else set()
        if reported_effects != declared_effects:
            errors.append(f"{prefix}.backend_report.decorative_effects: must match visual grammar")
        declared_palette = {
            str(color).strip().upper() for color in grammar.get("palette", [])
        }
        reported_palette = {
            str(color).strip().upper() for color in report.get("effective_palette", [])
        } if isinstance(report.get("effective_palette"), list) else set()
        if not declared_palette.issubset(reported_palette):
            errors.append(f"{prefix}.backend_report.effective_palette: must contain declared colors")
        declared_font = re.sub(r"[^a-z0-9]", "", str(grammar.get("font_family", "")).lower())
        pdf_fonts = [
            re.sub(r"[^a-z0-9]", "", str(font).lower())
            for font in report.get("pdf_fonts", [])
        ] if isinstance(report.get("pdf_fonts"), list) else []
        if not declared_font or not any(
            declared_font in font or font in declared_font for font in pdf_fonts if font
        ):
            errors.append(f"{prefix}.backend_report.pdf_fonts: declared font was not embedded")
    elif backend in {"matlab", "python", "python/matplotlib", "matplotlib"}:
        reopen = report.get("reopen_check")
        if not isinstance(reopen, dict) or not reopen or not all(value is True for value in reopen.values()):
            errors.append(f"{prefix}.backend_report.reopen_check: every recorded output must be true")
    else:
        if report.get("reopen_check") is not True:
            errors.append(f"{prefix}.backend_report.reopen_check: a passing reopen report is required")

    source_hashes: set[str] = set()
    source_data = entry.get("source_data")
    for source in collect_paths(source_data):
        declared = declared_hash_for_path(source_data, source, len(collect_paths(source_data)))
        if re.fullmatch(r"[0-9a-f]{64}", declared):
            source_hashes.add(declared)
    report_source_hashes: set[str] = set()
    for key in ("input_sha256",):
        value = report.get(key)
        if isinstance(value, str):
            report_source_hashes.add(value.lower())
    for key in ("source", "spec"):
        value = report.get(key)
        if isinstance(value, dict) and isinstance(value.get("sha256"), str):
            report_source_hashes.add(str(value["sha256"]).lower())
    sources = report.get("sources")
    if isinstance(sources, list):
        for value in sources:
            if isinstance(value, dict) and isinstance(value.get("sha256"), str):
                report_source_hashes.add(str(value["sha256"]).lower())
    if source_hashes and not report_source_hashes:
        errors.append(f"{prefix}.backend_report: runtime report records no source/input hash")
    elif source_hashes and not source_hashes.issubset(report_source_hashes):
        missing = sorted(source_hashes - report_source_hashes)
        errors.append(
            f"{prefix}.backend_report: runtime report does not cover every declared source hash; "
            f"missing {', '.join(missing)}"
        )
    return errors


def validate_entry(
    entry: dict[str, Any], index: int, base_dir: Path, require_sources: bool,
    require_outputs: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"figures[{index}]"

    for field in REQUIRED_FIELDS:
        if field not in entry or not nonempty(entry[field]):
            errors.append(f"{prefix}.{field}: required and must be non-empty")

    figure_id = str(entry.get("figure_id", ""))
    if figure_id and not re.fullmatch(r"[A-Za-z0-9_.-]+", figure_id):
        errors.append(f"{prefix}.figure_id: use only letters, digits, underscore, dot, or hyphen")

    caption = str(entry.get("caption_zh", ""))
    if caption and not ZH_RE.search(caption):
        warnings.append(f"{prefix}.caption_zh: no Chinese character detected")

    narrative_role = str(entry.get("narrative_role", "")).strip().lower()
    if narrative_role and narrative_role not in NARRATIVE_ROLES:
        errors.append(
            f"{prefix}.narrative_role: expected one of {sorted(NARRATIVE_ROLES)}, got '{narrative_role}'"
        )
    exact_values_location = str(entry.get("exact_values_location", "")).strip().lower()
    if exact_values_location and exact_values_location not in EXACT_VALUE_LOCATIONS:
        errors.append(
            f"{prefix}.exact_values_location: expected one of {sorted(EXACT_VALUE_LOCATIONS)}, "
            f"got '{exact_values_location}'"
        )
    placement = str(entry.get("placement", "")).strip().lower()
    if placement and placement not in PLACEMENTS:
        errors.append(f"{prefix}.placement: expected one of {sorted(PLACEMENTS)}, got '{placement}'")

    grammar = entry.get("visual_grammar")
    if isinstance(grammar, dict):
        missing_grammar = sorted(field for field in VISUAL_GRAMMAR_FIELDS if not nonempty(grammar.get(field)))
        if missing_grammar:
            errors.append(f"{prefix}.visual_grammar: missing {', '.join(missing_grammar)}")
        font_pt = grammar.get("base_font_pt")
        if font_pt is not None and (not isinstance(font_pt, (int, float)) or font_pt < 7):
            errors.append(f"{prefix}.visual_grammar.base_font_pt: must be numeric and at least 7 pt")
        line_width = grammar.get("line_width_pt")
        if line_width is not None and (not isinstance(line_width, (int, float)) or line_width <= 0):
            errors.append(f"{prefix}.visual_grammar.line_width_pt: must be a positive number")
        palette = grammar.get("palette")
        if palette is not None and (not isinstance(palette, list) or not palette):
            errors.append(f"{prefix}.visual_grammar.palette: must be a non-empty list")
        style_profile = str(grammar.get("style_profile", "")).strip().lower()
        if style_profile and style_profile not in STYLE_PROFILES:
            errors.append(
                f"{prefix}.visual_grammar.style_profile: expected one of {sorted(STYLE_PROFILES)}"
            )
        final_width = grammar.get("final_width_mm")
        if final_width is not None and (
            not isinstance(final_width, (int, float)) or not 65 <= float(final_width) <= 180
        ):
            errors.append(
                f"{prefix}.visual_grammar.final_width_mm: must be between 65 and 180 mm"
            )
        legend_strategy = str(grammar.get("legend_strategy", "")).strip().lower()
        if legend_strategy and legend_strategy not in LEGEND_STRATEGIES:
            errors.append(
                f"{prefix}.visual_grammar.legend_strategy: expected one of {sorted(LEGEND_STRATEGIES)}"
            )
        effects = grammar.get("decorative_effects")
        if effects is not None and (not isinstance(effects, list) or not effects):
            errors.append(f"{prefix}.visual_grammar.decorative_effects: must be a non-empty list")
        active_effects = [] if not isinstance(effects, list) else [
            str(effect).strip().lower() for effect in effects if str(effect).strip().lower() != "none"
        ]
        if active_effects:
            effect_semantics = str(entry.get("effect_semantics", "")).strip().lower()
            if effect_semantics not in {"nonsemantic", "encoded"}:
                errors.append(
                    f"{prefix}.effect_semantics: decorative effects require 'nonsemantic' or 'encoded'"
                )
            if effect_semantics == "encoded" and not nonempty(entry.get("effect_encoding_variable")):
                errors.append(f"{prefix}.effect_encoding_variable: required for encoded effects")
            if require_outputs:
                effect_audit = entry.get("effect_audit")
                required_effect_checks = {
                    "occlusion_check", "grayscale_check", "final_size_check", "effect_removed_comparison"
                }
                if not isinstance(effect_audit, dict):
                    errors.append(f"{prefix}.effect_audit: required for final outputs with decorative effects")
                else:
                    for check in sorted(required_effect_checks):
                        if str(effect_audit.get(check, "")).upper() != "PASSED":
                            errors.append(f"{prefix}.effect_audit.{check}: must be PASSED")
    elif grammar is not None:
        errors.append(f"{prefix}.visual_grammar: must be an object")

    chart_type = str(entry.get("chart_or_diagram_type", "")).strip().lower().replace(" ", "_")
    backend = str(entry.get("backend_preference", "")).strip().lower()
    editable = Path(str(entry.get("editable_output", "")))
    latex = Path(str(entry.get("latex_output", "")))

    if chart_type in DATA_TYPES and backend not in DATA_BACKENDS:
        errors.append(f"{prefix}: data chart type '{chart_type}' is incompatible with backend '{backend}'")
    if chart_type in DIAGRAM_TYPES and backend not in DIAGRAM_BACKENDS:
        errors.append(f"{prefix}: diagram type '{chart_type}' is incompatible with backend '{backend}'")
    if chart_type in {"software_screenshot", "code_screenshot", "ui_screenshot"}:
        errors.append(f"{prefix}.chart_or_diagram_type: software/code screenshots are not final evidence figures")
    elif chart_type not in DATA_TYPES | DIAGRAM_TYPES | {"table", "none"}:
        errors.append(f"{prefix}.chart_or_diagram_type: unrecognized type '{chart_type}'")
    if chart_type in {"radar", "pie", "donut", "dual_axis", "surface_3d", "bar_3d"}:
        if not nonempty(entry.get("restricted_chart_justification")):
            errors.append(f"{prefix}.restricted_chart_justification: required for restricted chart types")
        if not nonempty(entry.get("alternative_2d_check")):
            errors.append(f"{prefix}.alternative_2d_check: required for restricted chart types")
    if chart_type in {"surface_3d", "bar_3d"} and not nonempty(entry.get("projection_or_exact_table")):
        errors.append(f"{prefix}.projection_or_exact_table: required for 3D charts")
    if bool(entry.get("internal_title", False)):
        errors.append(f"{prefix}.internal_title: paper figures must use the LaTeX caption, not an internal title")
    if bool(entry.get("categorical_gradient", False)) and not nonempty(entry.get("color_encoding_variable")):
        errors.append(
            f"{prefix}.color_encoding_variable: categorical gradients require a real encoded variable"
        )
    if bool(entry.get("significance_annotation", False)):
        for field in ("statistical_test", "comparison_family", "multiplicity_policy"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for significance annotations")
    if chart_type == "errorbar":
        for field in ("uncertainty_type", "uncertainty_level", "sample_size_source"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for error bars")

    panel_count = entry.get("panel_count")
    if panel_count is not None:
        if not isinstance(panel_count, int) or panel_count < 1:
            errors.append(f"{prefix}.panel_count: must be a positive integer")
        elif panel_count > 4 and not nonempty(entry.get("multi_panel_justification")):
            errors.append(f"{prefix}.multi_panel_justification: required when panel_count > 4")
        if isinstance(panel_count, int) and panel_count > 6 and placement == "body":
            errors.append(f"{prefix}.panel_count: more than 6 panels are not allowed in the paper body")

    if narrative_role == "orientation" and exact_values_location not in {"not_applicable", ""}:
        errors.append(f"{prefix}: orientation figures cannot be the source of exact result values")
    if narrative_role in {"evidence", "validation"} and exact_values_location == "not_applicable":
        errors.append(f"{prefix}: evidence/validation figures require an exact-value location")
    if narrative_role == "mechanism" and chart_type in DATA_TYPES:
        errors.append(f"{prefix}: mechanism role cannot use a data-chart type")
    if narrative_role in {"evidence", "validation"} and chart_type in DIAGRAM_TYPES:
        errors.append(f"{prefix}: evidence/validation roles cannot use a structural diagram type")
    claim_ids = {claim.lower() for claim in normalized_claim_ids(entry.get("claim_id"))}
    if narrative_role in {"evidence", "validation"} and (
        not claim_ids or "not_applicable" in claim_ids
    ):
        errors.append(f"{prefix}.claim_id: evidence/validation figures require only real claim ids")
    if narrative_role == "validation":
        for field in ("validation_target", "validation_method"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for an independent validation figure")

    if backend == "origin" and editable.suffix.lower() != ".opju":
        errors.append(f"{prefix}.editable_output: Origin output must use .opju")
    if backend == "visio" and editable.suffix.lower() != ".vsdx":
        errors.append(f"{prefix}.editable_output: Visio output must use .vsdx")
    if backend in {"figurespec", "figurespec/svg", "svg"} and editable.suffix.lower() not in {".json", ".svg"}:
        errors.append(f"{prefix}.editable_output: FigureSpec/SVG source must use .json or .svg")
    if backend in {"python", "python/matplotlib", "matplotlib"} and editable.suffix.lower() not in {".py", ".json", ".ipynb"}:
        errors.append(f"{prefix}.editable_output: Python/Matplotlib source must use .py, .json, or .ipynb")
    if backend == "matlab" and editable.suffix.lower() not in {".fig", ".m", ".json"}:
        errors.append(f"{prefix}.editable_output: MATLAB source must use .fig, .m, or .json")
    if backend == "mermaid" and editable.suffix.lower() not in {".mmd", ".md"}:
        errors.append(f"{prefix}.editable_output: Mermaid source must use .mmd or .md")
    if latex.suffix.lower() not in {".pdf", ".png"}:
        errors.append(f"{prefix}.latex_output: XeLaTeX output must use .pdf or .png")
    elif latex.suffix.lower() == ".png" and chart_type not in {"map"}:
        warnings.append(f"{prefix}.latex_output: PDF vector output is preferred for non-raster figures")

    variables = entry.get("variables")
    units = entry.get("units")
    if isinstance(variables, list) and isinstance(units, dict):
        missing_units = [str(v) for v in variables if str(v) not in units]
        if missing_units:
            warnings.append(f"{prefix}.units: no unit entry for {', '.join(missing_units)}")

    if require_sources:
        source_paths = collect_paths(entry.get("source_data"))
        if not source_paths:
            errors.append(f"{prefix}.source_data: no source path could be located")
        for source in source_paths:
            candidate = Path(source)
            if not candidate.is_absolute():
                candidate = base_dir / candidate
            if not candidate.is_file():
                errors.append(f"{prefix}.source_data: missing file {candidate}")
        source_data = entry.get("source_data")
        for source in source_paths:
            declared = declared_hash_for_path(source_data, source, len(source_paths))
            if not re.fullmatch(r"[0-9a-f]{64}", declared):
                errors.append(
                    f"{prefix}.source_data.sha256: every source requires a colocated or mapped "
                    f"64-character SHA-256 ({source})"
                )
            else:
                candidate = Path(source)
                if not candidate.is_absolute():
                    candidate = base_dir / candidate
                if candidate.is_file() and file_sha256(candidate) != declared:
                    errors.append(f"{prefix}.source_data.sha256: does not match {candidate}")

    if require_outputs:
        resolved_hashes: dict[str, str] = {}
        for field, path_value, hash_field in (
            ("editable_output", editable, "editable_sha256"),
            ("latex_output", latex, "latex_sha256"),
        ):
            candidate = path_value if path_value.is_absolute() else base_dir / path_value
            if not candidate.is_file():
                errors.append(f"{prefix}.{field}: missing output file {candidate}")
                continue
            declared = str(entry.get(hash_field, "")).strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", declared):
                errors.append(f"{prefix}.{hash_field}: required as 64 hexadecimal characters")
            elif file_sha256(candidate) != declared:
                errors.append(f"{prefix}.{hash_field}: does not match {candidate}")
            else:
                resolved_hashes[field] = declared
            if candidate.is_file():
                reopen_error = basic_output_reopen_error(candidate)
                if reopen_error:
                    errors.append(f"{prefix}.{field}: {reopen_error}: {candidate}")
        errors.extend(
            validate_backend_report(
                entry, prefix, base_dir,
                resolved_hashes.get("editable_output", ""),
                resolved_hashes.get("latex_output", ""),
            )
        )

    return errors, warnings


def validate_grammar_groups(entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    grammar_by_group: dict[str, str] = {}
    for index, entry in enumerate(entries):
        group = str(entry.get("visual_grammar_group", ""))
        grammar = entry.get("visual_grammar")
        if group and isinstance(grammar, dict):
            signature = json.dumps(grammar, ensure_ascii=False, sort_keys=True)
            if group in grammar_by_group and grammar_by_group[group] != signature:
                errors.append(
                    f"figures[{index}].visual_grammar: conflicts with earlier entry in group '{group}'"
                )
            else:
                grammar_by_group[group] = signature
    return errors


def value_at_dotted_field(payload: Any, field: str) -> Any:
    value = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(field)
        value = value[part]
    return value


def validate_coverage(
    document: Any, entries: list[dict[str, Any]], base_dir: Path | None = None
) -> tuple[list[str], dict[str, Any]]:
    """Validate reader-task coverage without imposing an arbitrary global figure count."""
    errors: list[str] = []
    summary: dict[str, Any] = {"question_count": 0, "covered_claim_count": 0, "questions": []}
    if not isinstance(document, dict) or not isinstance(document.get("coverage_plan"), dict):
        return ["coverage_plan: required in final coverage mode"], summary
    questions = document["coverage_plan"].get("questions")
    if not isinstance(questions, list) or not questions:
        return ["coverage_plan.questions: must be a non-empty list"], summary

    expected_question_ids = document["coverage_plan"].get("expected_question_ids")
    if not isinstance(expected_question_ids, list) or not expected_question_ids or not all(
        isinstance(item, str) and item.strip() for item in expected_question_ids
    ):
        errors.append("coverage_plan.expected_question_ids: must list every expected question")
        expected_question_ids = []
    elif len(set(expected_question_ids)) != len(expected_question_ids):
        errors.append("coverage_plan.expected_question_ids: duplicate question id")

    expected_source = document["coverage_plan"].get("expected_question_ids_source")
    if not isinstance(expected_source, dict):
        errors.append("coverage_plan.expected_question_ids_source: required and must be an object")
    else:
        source_paths = collect_paths(expected_source)
        field = str(expected_source.get("field", "")).strip()
        if len(source_paths) != 1:
            errors.append(
                "coverage_plan.expected_question_ids_source: exactly one source file is required"
            )
        elif not field:
            errors.append("coverage_plan.expected_question_ids_source.field: required")
        else:
            source_path = Path(source_paths[0])
            if not source_path.is_absolute():
                source_path = (base_dir or Path.cwd()) / source_path
            declared = declared_hash_for_path(expected_source, source_paths[0], 1)
            if not re.fullmatch(r"[0-9a-f]{64}", declared):
                errors.append(
                    "coverage_plan.expected_question_ids_source.sha256: required as 64 hexadecimal characters"
                )
            elif not source_path.is_file():
                errors.append(
                    f"coverage_plan.expected_question_ids_source.file: missing file {source_path}"
                )
            elif file_sha256(source_path) != declared:
                errors.append(
                    "coverage_plan.expected_question_ids_source.sha256: does not match source file"
                )
            else:
                try:
                    source_payload = load_document(source_path)
                    source_ids = value_at_dotted_field(source_payload, field)
                    if not isinstance(source_ids, list) or not all(
                        isinstance(item, str) and item.strip() for item in source_ids
                    ):
                        errors.append(
                            "coverage_plan.expected_question_ids_source.field: must resolve to a list of ids"
                        )
                    elif {item.strip() for item in source_ids} != {
                        str(item).strip() for item in expected_question_ids
                    }:
                        errors.append(
                            "coverage_plan.expected_question_ids: does not match the bound decomposition source"
                        )
                except Exception as exc:
                    errors.append(
                        "coverage_plan.expected_question_ids_source: cannot read bound field: "
                        f"{type(exc).__name__}: {exc}"
                    )

    by_id = {str(entry.get("figure_id", "")): entry for entry in entries}
    planned_questions: set[str] = set()
    summary["question_count"] = len(questions)
    for index, question in enumerate(questions):
        prefix = f"coverage_plan.questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        question_id = str(question.get("question_id", "")).strip()
        if not question_id:
            errors.append(f"{prefix}.question_id: required")
            continue
        if question_id in planned_questions:
            errors.append(f"{prefix}.question_id: duplicate '{question_id}'")
        planned_questions.add(question_id)
        core_claim_ids = question.get("core_claim_ids")
        if not isinstance(core_claim_ids, list) or not core_claim_ids or not all(
            isinstance(item, str) and item.strip() for item in core_claim_ids
        ):
            errors.append(f"{prefix}.core_claim_ids: must be a non-empty list of claim ids")
            core_claim_ids = []
        slots = question.get("slots")
        if not isinstance(slots, dict):
            errors.append(f"{prefix}.slots: must be an object")
            continue
        missing_slots = sorted(COVERAGE_SLOTS - set(slots))
        if missing_slots:
            errors.append(f"{prefix}.slots: missing {', '.join(missing_slots)}")

        slot_ids: dict[str, list[str]] = {}
        first_slot_by_figure: dict[str, str] = {}
        for slot_name in sorted(COVERAGE_SLOTS):
            slot = slots.get(slot_name)
            slot_prefix = f"{prefix}.slots.{slot_name}"
            if not isinstance(slot, dict):
                if slot_name in slots:
                    errors.append(f"{slot_prefix}: must be an object")
                continue
            figure_ids = slot.get("figure_ids", [])
            if not isinstance(figure_ids, list) or not all(isinstance(fid, str) and fid for fid in figure_ids):
                errors.append(f"{slot_prefix}.figure_ids: must be a list of figure ids")
                figure_ids = []
            slot_ids[slot_name] = figure_ids
            if slot_name in MANDATORY_COVERAGE_SLOTS and not figure_ids:
                errors.append(f"{slot_prefix}.figure_ids: at least one figure is mandatory")
            if slot_name not in MANDATORY_COVERAGE_SLOTS and not figure_ids and not specific_reason(
                slot.get("omission_reason")
            ):
                errors.append(
                    f"{slot_prefix}: provide figure_ids or a specific omission_reason of at least 8 characters"
                )
            for figure_id in figure_ids:
                entry = by_id.get(figure_id)
                if entry is None:
                    errors.append(f"{slot_prefix}.figure_ids: unknown figure '{figure_id}'")
                    continue
                if str(entry.get("question_id", "")).strip() != question_id:
                    errors.append(
                        f"{slot_prefix}.figure_ids: figure '{figure_id}' belongs to another question"
                    )
                previous_slot = first_slot_by_figure.get(figure_id)
                if previous_slot is not None and previous_slot != slot_name:
                    errors.append(
                        f"{slot_prefix}: figure '{figure_id}' is already used by slot '{previous_slot}'; "
                        "coverage slots require distinct figure ids"
                    )
                else:
                    first_slot_by_figure[figure_id] = slot_name
                role = str(entry.get("narrative_role", "")).lower()
                if role not in SLOT_ALLOWED_ROLES[slot_name]:
                    errors.append(
                        f"{slot_prefix}: figure '{figure_id}' has role '{role}', expected one of "
                        f"{sorted(SLOT_ALLOWED_ROLES[slot_name])}"
                    )
                chart_type = str(entry.get("chart_or_diagram_type", "")).strip().lower()
                if chart_type in {"", "none", "table"}:
                    errors.append(
                        f"{slot_prefix}: figure '{figure_id}' must reference an actual chart or diagram"
                    )

        main_ids = set(slot_ids.get("main_result", []))
        validation_ids = set(slot_ids.get("validation", []))
        if main_ids & validation_ids:
            errors.append(f"{prefix}: main_result and validation must use different figure ids")
        main_signatures = {
            figure_content_signature(by_id[figure_id])
            for figure_id in main_ids if figure_id in by_id
        }
        validation_signatures = {
            figure_content_signature(by_id[figure_id])
            for figure_id in validation_ids if figure_id in by_id
        }
        if main_signatures & validation_signatures:
            errors.append(
                f"{prefix}: main_result and validation contain the same source, variables, "
                "transformations, and chart type; independent validation content is required"
            )
        for figure_id in main_ids | validation_ids:
            entry = by_id.get(figure_id, {})
            if str(entry.get("placement", "")).lower() != "body":
                errors.append(f"{prefix}: mandatory figure '{figure_id}' must be placed in the body")

        referenced_ids = set().union(*[set(ids) for ids in slot_ids.values()])
        artifact_owner: dict[tuple[str, str], str] = {}
        for figure_id in sorted(referenced_ids):
            entry = by_id.get(figure_id, {})
            for hash_field in ("latex_sha256", "editable_sha256", "backend_report_sha256"):
                artifact_hash = str(entry.get(hash_field, "")).strip().lower()
                if not re.fullmatch(r"[0-9a-f]{64}", artifact_hash):
                    continue
                key = (hash_field, artifact_hash)
                previous = artifact_owner.get(key)
                if previous is not None and previous != figure_id:
                    errors.append(
                        f"{prefix}: figures '{previous}' and '{figure_id}' reuse the same "
                        f"{hash_field} artifact; distinct figure ids must reference distinct outputs"
                    )
                else:
                    artifact_owner[key] = figure_id
        covered_claims: set[str] = set()
        for entry in entries:
            if (
                str(entry.get("question_id", "")).strip() == question_id
                and str(entry.get("narrative_role", "")).lower() in {"evidence", "validation"}
                and str(entry.get("figure_id", "")) in referenced_ids
            ):
                covered_claims.update(normalized_claim_ids(entry.get("claim_id")))
        for claim_id in core_claim_ids:
            if claim_id not in covered_claims:
                errors.append(
                    f"{prefix}.core_claim_ids: claim '{claim_id}' has no evidence/validation figure"
                )
            else:
                summary["covered_claim_count"] += 1
        for entry in entries:
            if (
                str(entry.get("question_id", "")).strip() == question_id
                and str(entry.get("narrative_role", "")).lower() in NARRATIVE_ROLES
                and str(entry.get("figure_id", "")) not in referenced_ids
            ):
                errors.append(
                    f"{prefix}: figure '{entry.get('figure_id', '')}' is not assigned "
                    "to any coverage slot"
                )
        distinct_figure_count = len(set().union(*[set(ids) for ids in slot_ids.values()]))
        if distinct_figure_count < MIN_DISTINCT_FIGURES_PER_QUESTION:
            errors.append(
                f"{prefix}: at least {MIN_DISTINCT_FIGURES_PER_QUESTION} distinct figures are "
                "required per question; add diagnosis, mechanism, comparison, or robustness evidence"
            )
        summary["questions"].append(
            {
                "question_id": question_id,
                "core_claim_count": len(core_claim_ids),
                "distinct_figure_count": distinct_figure_count,
                "distinct_latex_output_count": len({
                    str(by_id[figure_id].get("latex_sha256", "")).strip().lower()
                    for figure_id in referenced_ids if figure_id in by_id
                    and re.fullmatch(
                        r"[0-9a-f]{64}",
                        str(by_id[figure_id].get("latex_sha256", "")).strip().lower(),
                    )
                }),
            }
        )

    figure_questions = {
        str(entry.get("question_id", "")).strip()
        for entry in entries
        if str(entry.get("question_id", "")).strip().lower() not in {"", "paper"}
    }
    for question_id in sorted(figure_questions - planned_questions):
        errors.append(f"coverage_plan.questions: missing plan for figure question '{question_id}'")
    expected = {str(item).strip() for item in expected_question_ids}
    for question_id in sorted(expected - planned_questions):
        errors.append(f"coverage_plan.questions: missing expected question '{question_id}'")
    for question_id in sorted(planned_questions - expected):
        errors.append(f"coverage_plan.expected_question_ids: missing planned question '{question_id}'")
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate FIGURE_INTENT JSON/YAML structure, paths, and backend/output contracts."
    )
    parser.add_argument("intent_file", type=Path)
    parser.add_argument("--base-dir", type=Path, default=None, help="Base directory for relative source paths")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--require-sources",
        dest="require_sources",
        action="store_true",
        help="Fail when referenced source files are absent (default)",
    )
    source_group.add_argument(
        "--allow-missing-sources",
        dest="require_sources",
        action="store_false",
        help="Allow draft intents whose source files do not exist; never use for final delivery",
    )
    parser.set_defaults(require_sources=True)
    parser.add_argument(
        "--require-outputs",
        action="store_true",
        help="Final mode: require editable/LaTeX output files and matching SHA-256 fields",
    )
    parser.add_argument(
        "--require-coverage",
        action="store_true",
        help="Final mode: require per-question reader-task coverage and core-claim mapping",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report path")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "checker": "figure-intent-structure-only",
        "output_integrity_check": bool(args.require_outputs),
        "coverage_check": bool(args.require_coverage),
        "semantic_claim_validation": False,
        "input": str(args.intent_file.resolve()),
        "status": "FAILED",
        "figure_count": 0,
        "errors": [],
        "warnings": [],
    }
    try:
        document = load_document(args.intent_file)
        entries = normalize_entries(document)
        report["figure_count"] = len(entries)
        if not entries:
            report["errors"].append("figures: at least one figure entry is required")
        seen: set[str] = set()
        base_dir = (args.base_dir or args.intent_file.parent).resolve()
        for index, entry in enumerate(entries):
            errors, warnings = validate_entry(
                entry, index, base_dir, args.require_sources, args.require_outputs
            )
            report["errors"].extend(errors)
            report["warnings"].extend(warnings)
            figure_id = str(entry.get("figure_id", ""))
            if figure_id in seen:
                report["errors"].append(f"figures[{index}].figure_id: duplicate '{figure_id}'")
            seen.add(figure_id)
        report["errors"].extend(validate_grammar_groups(entries))
        if args.require_coverage:
            coverage_errors, coverage_summary = validate_coverage(document, entries, base_dir)
            report["errors"].extend(coverage_errors)
            report["coverage_summary"] = coverage_summary
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")

    failed = bool(report["errors"] or (args.strict and report["warnings"]))
    report["status"] = "FAILED" if failed else "PASSED"
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
