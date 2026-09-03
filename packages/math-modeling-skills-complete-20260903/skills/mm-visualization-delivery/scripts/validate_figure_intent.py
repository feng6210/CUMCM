#!/usr/bin/env python3
"""Validate FIGURE_INTENT / FIGURE_PLAN structure and artifact integrity.

This checker is intentionally structural.  It does not decide whether a scientific
claim is true and it does not impose a fixed number of figures per question.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

ROLE_SET = {"orientation", "mechanism", "evidence", "validation"}
PLACEMENTS = {"body", "appendix"}
REPRESENTATIONS = {"figure", "table", "text", "appendix", "not_applicable"}
STYLE_PROFILES = {
    "cumcm-clean", "cumcm-highlight", "cumcm-data-dense", "cumcm-vivid", "cumcm-mechanism"
}
LEGEND_STRATEGIES = {"top", "right", "inside", "direct", "none"}
EXACT_VALUE_LOCATIONS = {
    "result_table", "machine_readable_table", "figure_annotation", "caption", "not_applicable"
}
READER_TASKS = {
    "orientation", "mechanism", "main_result", "comparison", "validation", "robustness"
}

DATA_TYPES = {
    "line", "line_chart", "scatter", "scatter_plot", "bar", "bar_chart", "horizontal_bar",
    "grouped_bar", "stacked_bar", "box", "boxplot", "violin", "histogram", "density",
    "heatmap", "trajectory", "map", "contour", "errorbar", "area", "scatter_matrix",
    "vector_field", "pareto", "dumbbell", "slope", "interval_band", "interval_timeline",
    "sensitivity", "convergence", "data_plot", "surface_3d", "bar_3d", "radar", "pie",
    "donut", "dual_axis",
}
DIAGRAM_TYPES = {
    "flowchart", "workflow", "architecture", "structural", "state_machine", "sequence",
    "network", "topology", "decision_tree", "mechanism", "diagram", "geometry", "case_diagram",
    "coordinate_system", "free_body_diagram",
}
DATA_BACKENDS = {"origin", "matlab", "python", "python/matplotlib", "matplotlib"}
DIAGRAM_BACKENDS = {"visio", "figurespec", "figurespec/svg", "svg", "mermaid"}
RESTRICTED_TYPES = {"radar", "pie", "donut", "dual_axis", "surface_3d", "bar_3d"}

REQUIRED_FIGURE_FIELDS = (
    "figure_id", "question_id", "purpose", "source_data", "variables", "units",
    "transformations", "chart_or_diagram_type", "backend_preference", "editable_output",
    "latex_output", "caption_zh", "narrative_role", "reader_takeaway", "exact_values_location",
    "visual_grammar_group", "visual_grammar", "placement",
)
VISUAL_GRAMMAR_FIELDS = {
    "font_family", "base_font_pt", "palette", "line_width_pt", "style_profile",
    "final_width_mm", "legend_strategy", "precision_policy", "decorative_effects",
}
PATH_KEYS = {"file", "path", "source", "source_file", "files", "paths", "source_files"}
SINGULAR_PATH_KEYS = {"file", "path", "source", "source_file"}
ZH_RE = re.compile(r"[\u3400-\u9fff]")


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("YAML input requires PyYAML; use JSON or install PyYAML") from exc
    return yaml.safe_load(text)


def nonempty(value: Any) -> bool:
    return value is not None and value not in ("", [], {})


def specific_reason(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) >= 8 and text.lower() not in {"n/a", "na", "none", "not applicable", "不适用"}


def collect_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for child in value:
            result.extend(collect_string_values(child))
        return result
    return []


def collect_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in PATH_KEYS:
                found.extend(collect_string_values(child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_paths(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                found.extend(collect_paths(child))
    return found


def declared_hash_for_path(value: Any, source_path: str, total_paths: int) -> str:
    if isinstance(value, list):
        for child in value:
            result = declared_hash_for_path(child, source_path, total_paths)
            if result:
                return result
        return ""
    if not isinstance(value, dict):
        return ""

    direct_paths: list[str] = []
    for key, child in value.items():
        if str(key).lower() in SINGULAR_PATH_KEYS:
            direct_paths.extend(collect_string_values(child))
    if source_path in direct_paths and isinstance(value.get("sha256"), str):
        return str(value["sha256"]).strip().lower()

    for mapping_key in ("sha256", "hashes"):
        mapping = value.get(mapping_key)
        if isinstance(mapping, dict) and isinstance(mapping.get(source_path), str):
            return str(mapping[source_path]).strip().lower()

    if total_paths == 1 and isinstance(value.get("sha256"), str):
        return str(value["sha256"]).strip().lower()

    for child in value.values():
        if isinstance(child, (dict, list)):
            result = declared_hash_for_path(child, source_path, total_paths)
            if result:
                return result
    return ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_entries(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        entries = document
    elif isinstance(document, dict) and isinstance(document.get("figures"), list):
        entries = document["figures"]
    elif isinstance(document, dict) and "figure_id" in document:
        entries = [document]
    elif isinstance(document, dict) and isinstance(document.get("coverage_plan"), dict):
        entries = []
    else:
        raise ValueError("Root must be a figure, a list, or an object with figures/coverage_plan")
    if not all(isinstance(item, dict) for item in entries):
        raise ValueError("Every figure entry must be an object")
    return entries


def normalized_claim_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def basic_output_reopen_error(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        data = path.read_bytes()
        if len(data) < 256 or not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            return "incomplete PDF header/body/EOF"
    elif suffix == ".png":
        data = path.read_bytes()
        if len(data) < 64 or not data.startswith(b"\x89PNG\r\n\x1a\n") or b"IEND" not in data[-64:]:
            return "incomplete PNG signature/IEND"
    elif suffix == ".vsdx":
        if not zipfile.is_zipfile(path):
            return "not a reopenable OOXML ZIP package"
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or "visio/document.xml" not in archive.namelist():
                return "corrupt or incomplete Visio package"
    elif suffix == ".opju":
        data = path.read_bytes()
        if len(data) < 1024 or not data.startswith(b"CPYUA"):
            return "does not resemble a complete Origin project"
    elif suffix == ".fig":
        data = path.read_bytes()
        if len(data) < 1024 or not (data.startswith(b"MATLAB") or data.startswith(b"\x89HDF")):
            return "does not resemble a complete MATLAB figure"
    return None


def validate_visual_grammar(entry: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    grammar = entry.get("visual_grammar")
    if not isinstance(grammar, dict):
        return [f"{prefix}.visual_grammar: required and must be an object"]
    missing = sorted(VISUAL_GRAMMAR_FIELDS - set(grammar))
    if missing:
        errors.append(f"{prefix}.visual_grammar: missing {', '.join(missing)}")
    profile = str(grammar.get("style_profile", "")).strip().lower()
    if profile and profile not in STYLE_PROFILES:
        errors.append(f"{prefix}.visual_grammar.style_profile: unknown '{profile}'")
    legend = str(grammar.get("legend_strategy", "")).strip().lower()
    if legend and legend not in LEGEND_STRATEGIES:
        errors.append(f"{prefix}.visual_grammar.legend_strategy: unknown '{legend}'")
    min_font = grammar.get("base_font_pt")
    if isinstance(min_font, (int, float)) and float(min_font) < 7:
        errors.append(f"{prefix}.visual_grammar.base_font_pt: must be at least 7 pt")
    width = grammar.get("final_width_mm")
    if isinstance(width, (int, float)) and float(width) <= 0:
        errors.append(f"{prefix}.visual_grammar.final_width_mm: must be positive")
    effects = grammar.get("decorative_effects")
    if effects is not None and not isinstance(effects, list):
        errors.append(f"{prefix}.visual_grammar.decorative_effects: must be a list")
    return errors


def validate_entry(
    entry: dict[str, Any], index: int, base_dir: Path,
    require_sources: bool, require_outputs: bool,
) -> tuple[list[str], list[str]]:
    prefix = f"figures[{index}]"
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIGURE_FIELDS:
        if field not in entry or not nonempty(entry[field]):
            errors.append(f"{prefix}.{field}: required and must be non-empty")

    figure_id = str(entry.get("figure_id", ""))
    if figure_id and not re.fullmatch(r"[A-Za-z0-9_.-]+", figure_id):
        errors.append(f"{prefix}.figure_id: use letters, digits, '.', '_' or '-'")

    role = str(entry.get("narrative_role", "")).strip().lower()
    if role and role not in ROLE_SET:
        errors.append(f"{prefix}.narrative_role: expected one of {sorted(ROLE_SET)}")
    placement = str(entry.get("placement", "")).strip().lower()
    if placement and placement not in PLACEMENTS:
        errors.append(f"{prefix}.placement: expected one of {sorted(PLACEMENTS)}")
    exact_location = str(entry.get("exact_values_location", "")).strip().lower()
    if exact_location and exact_location not in EXACT_VALUE_LOCATIONS:
        errors.append(f"{prefix}.exact_values_location: unknown '{exact_location}'")
    takeaway = str(entry.get("reader_takeaway", "")).strip()
    if takeaway and len(takeaway) < 8:
        warnings.append(f"{prefix}.reader_takeaway: too vague; state the reader decision/understanding")
    if not ZH_RE.search(str(entry.get("caption_zh", ""))):
        warnings.append(f"{prefix}.caption_zh: no Chinese characters detected")

    chart = str(entry.get("chart_or_diagram_type", "")).strip().lower().replace(" ", "_")
    backend = str(entry.get("backend_preference", "")).strip().lower()
    if chart in DATA_TYPES and backend not in DATA_BACKENDS:
        errors.append(f"{prefix}: data chart '{chart}' incompatible with backend '{backend}'")
    elif chart in DIAGRAM_TYPES and backend not in DIAGRAM_BACKENDS:
        errors.append(f"{prefix}: diagram '{chart}' incompatible with backend '{backend}'")
    elif chart not in DATA_TYPES | DIAGRAM_TYPES:
        errors.append(f"{prefix}.chart_or_diagram_type: unrecognized '{chart}'")

    if chart in RESTRICTED_TYPES:
        if not specific_reason(entry.get("restricted_chart_justification")):
            errors.append(f"{prefix}.restricted_chart_justification: required for '{chart}'")
        if not specific_reason(entry.get("alternative_2d_check")):
            errors.append(f"{prefix}.alternative_2d_check: explain why a 2D alternative is insufficient")
    if chart in {"surface_3d", "bar_3d"} and not nonempty(entry.get("projection_or_exact_table")):
        errors.append(f"{prefix}.projection_or_exact_table: required for 3D figures")

    if bool(entry.get("internal_title", False)):
        errors.append(f"{prefix}.internal_title: use LaTeX caption instead of a paper-style internal title")
    if bool(entry.get("significance_annotation", False)):
        for field in ("statistical_test", "comparison_family", "multiplicity_policy"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for significance annotations")
    if chart == "errorbar":
        for field in ("uncertainty_type", "uncertainty_level", "sample_size_source"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for error bars")

    panel_count = entry.get("panel_count")
    if panel_count is not None:
        if not isinstance(panel_count, int) or panel_count < 1:
            errors.append(f"{prefix}.panel_count: must be a positive integer")
        elif panel_count > 4 and not specific_reason(entry.get("multi_panel_justification")):
            errors.append(f"{prefix}.multi_panel_justification: required when panel_count > 4")
        if isinstance(panel_count, int) and panel_count > 6 and placement == "body":
            errors.append(f"{prefix}.panel_count: >6 panels should move to appendix")

    if role == "orientation" and exact_location not in {"", "not_applicable"}:
        errors.append(f"{prefix}: orientation figures cannot be the source of exact result values")
    if role in {"evidence", "validation"} and exact_location == "not_applicable":
        errors.append(f"{prefix}: evidence/validation figures require an exact-value location")
    if role == "mechanism" and chart in DATA_TYPES:
        errors.append(f"{prefix}: mechanism role should use a structural/geometry diagram, not a data chart")
    if role in {"evidence", "validation"} and chart in DIAGRAM_TYPES:
        errors.append(f"{prefix}: evidence/validation roles cannot use a structural diagram")
    if role == "validation":
        for field in ("validation_target", "validation_method"):
            if not nonempty(entry.get(field)):
                errors.append(f"{prefix}.{field}: required for validation figures")

    errors.extend(validate_visual_grammar(entry, prefix))

    editable = Path(str(entry.get("editable_output", "")))
    latex = Path(str(entry.get("latex_output", "")))
    if backend == "origin" and editable.suffix.lower() != ".opju":
        errors.append(f"{prefix}.editable_output: Origin output must use .opju")
    if backend == "visio" and editable.suffix.lower() != ".vsdx":
        errors.append(f"{prefix}.editable_output: Visio output must use .vsdx")
    if backend in {"figurespec", "figurespec/svg", "svg"} and editable.suffix.lower() not in {".json", ".svg"}:
        errors.append(f"{prefix}.editable_output: FigureSpec/SVG source must use .json or .svg")
    if backend in {"python", "python/matplotlib", "matplotlib"} and editable.suffix.lower() not in {".py", ".json", ".ipynb"}:
        errors.append(f"{prefix}.editable_output: Python source must use .py, .json or .ipynb")
    if backend == "matlab" and editable.suffix.lower() not in {".fig", ".m", ".json"}:
        errors.append(f"{prefix}.editable_output: MATLAB source must use .fig, .m or .json")
    if latex.suffix.lower() not in {".pdf", ".png"}:
        errors.append(f"{prefix}.latex_output: expected .pdf or .png")
    elif latex.suffix.lower() == ".png" and chart != "map":
        warnings.append(f"{prefix}.latex_output: vector PDF is preferred")

    if require_sources:
        source_data = entry.get("source_data")
        source_paths = collect_paths(source_data)
        if not source_paths:
            errors.append(f"{prefix}.source_data: no source path found")
        for source in source_paths:
            candidate = Path(source)
            if not candidate.is_absolute():
                candidate = base_dir / candidate
            if not candidate.is_file():
                errors.append(f"{prefix}.source_data: missing {candidate}")
                continue
            declared = declared_hash_for_path(source_data, source, len(source_paths))
            if not re.fullmatch(r"[0-9a-f]{64}", declared):
                errors.append(f"{prefix}.source_data.sha256: 64-char hash required for {source}")
            elif file_sha256(candidate) != declared:
                errors.append(f"{prefix}.source_data.sha256: mismatch for {candidate}")

    if require_outputs:
        output_hashes: set[str] = set()
        for field, path_value, hash_field in (
            ("editable_output", editable, "editable_sha256"),
            ("latex_output", latex, "latex_sha256"),
        ):
            candidate = path_value if path_value.is_absolute() else base_dir / path_value
            if not candidate.is_file():
                errors.append(f"{prefix}.{field}: missing {candidate}")
                continue
            declared = str(entry.get(hash_field, "")).strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", declared):
                errors.append(f"{prefix}.{hash_field}: 64-char SHA-256 required")
            elif file_sha256(candidate) != declared:
                errors.append(f"{prefix}.{hash_field}: mismatch for {candidate}")
            else:
                output_hashes.add(declared)
            reopen_error = basic_output_reopen_error(candidate)
            if reopen_error:
                errors.append(f"{prefix}.{field}: {reopen_error}: {candidate}")

        report_value = entry.get("backend_report")
        if not isinstance(report_value, str) or not report_value.strip():
            errors.append(f"{prefix}.backend_report: required in final output mode")
        else:
            report_path = Path(report_value)
            if not report_path.is_absolute():
                report_path = base_dir / report_path
            if not report_path.is_file():
                errors.append(f"{prefix}.backend_report: missing {report_path}")
            else:
                declared = str(entry.get("backend_report_sha256", "")).strip().lower()
                if not re.fullmatch(r"[0-9a-f]{64}", declared):
                    errors.append(f"{prefix}.backend_report_sha256: 64-char SHA-256 required")
                elif file_sha256(report_path) != declared:
                    errors.append(f"{prefix}.backend_report_sha256: mismatch")
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
                    if str(report.get("status", "")).upper() not in {"PASSED", "RUNTIME_VERIFIED"}:
                        errors.append(f"{prefix}.backend_report.status: expected PASSED/RUNTIME_VERIFIED")
                except Exception as exc:
                    errors.append(f"{prefix}.backend_report: unreadable JSON: {type(exc).__name__}: {exc}")

    return errors, warnings


def value_at_dotted_field(payload: Any, field: str) -> Any:
    value = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(field)
        value = value[part]
    return value


def normalize_task_block(question: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Support new `tasks` schema and old `slots` schema during migration."""
    if isinstance(question.get("tasks"), dict):
        return question["tasks"]
    slots = question.get("slots")
    if not isinstance(slots, dict):
        return {}
    converted: dict[str, dict[str, Any]] = {}
    mapping = {
        "data_diagnosis": "orientation",
        "mechanism": "mechanism",
        "main_result": "main_result",
        "comparison": "comparison",
        "validation": "validation",
        "robustness": "robustness",
    }
    for old_name, task_name in mapping.items():
        slot = slots.get(old_name)
        if not isinstance(slot, dict):
            continue
        ids = slot.get("figure_ids", [])
        if isinstance(ids, list) and ids:
            converted[task_name] = {
                "representation": "figure", "figure_ids": ids,
                "reason": slot.get("reason") or "legacy slot migrated as figure",
            }
        else:
            converted[task_name] = {
                "representation": "not_applicable", "figure_ids": [],
                "reason": slot.get("omission_reason") or "legacy slot has no figure",
            }
    return converted


def validate_coverage(document: Any, entries: list[dict[str, Any]], base_dir: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {"question_count": 0, "body_figure_count": 0, "questions": [], "warnings": warnings}
    if not isinstance(document, dict) or not isinstance(document.get("coverage_plan"), dict):
        return ["coverage_plan: required in coverage mode"], summary

    plan = document["coverage_plan"]
    questions = plan.get("questions")
    if not isinstance(questions, list) or not questions:
        return ["coverage_plan.questions: must be a non-empty list"], summary

    expected_ids = plan.get("expected_question_ids")
    if not isinstance(expected_ids, list) or not expected_ids or not all(isinstance(item, str) and item.strip() for item in expected_ids):
        errors.append("coverage_plan.expected_question_ids: must list every expected question")
        expected_ids = []

    expected_source = plan.get("expected_question_ids_source")
    if isinstance(expected_source, dict):
        paths = collect_paths(expected_source)
        field = str(expected_source.get("field", "")).strip()
        if len(paths) == 1 and field:
            source_path = Path(paths[0])
            if not source_path.is_absolute():
                source_path = base_dir / source_path
            declared = declared_hash_for_path(expected_source, paths[0], 1)
            if not source_path.is_file():
                errors.append(f"coverage_plan.expected_question_ids_source.file: missing {source_path}")
            elif not re.fullmatch(r"[0-9a-f]{64}", declared) or file_sha256(source_path) != declared:
                errors.append("coverage_plan.expected_question_ids_source.sha256: missing or mismatched")
            else:
                try:
                    payload = load_document(source_path)
                    source_ids = value_at_dotted_field(payload, field)
                    if {str(item).strip() for item in source_ids} != {str(item).strip() for item in expected_ids}:
                        errors.append("coverage_plan.expected_question_ids does not match decomposition source")
                except Exception as exc:
                    errors.append(f"coverage_plan.expected_question_ids_source: {type(exc).__name__}: {exc}")
        else:
            errors.append("coverage_plan.expected_question_ids_source: exactly one file and a field are required")
    else:
        errors.append("coverage_plan.expected_question_ids_source: required")

    by_id = {str(entry.get("figure_id", "")): entry for entry in entries}
    planned: set[str] = set()
    used_figures: set[str] = set()
    summary["question_count"] = len(questions)

    for index, question in enumerate(questions):
        prefix = f"coverage_plan.questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        qid = str(question.get("question_id", "")).strip()
        if not qid:
            errors.append(f"{prefix}.question_id: required")
            continue
        if qid in planned:
            errors.append(f"{prefix}.question_id: duplicate '{qid}'")
        planned.add(qid)

        tasks = normalize_task_block(question)
        if not tasks:
            errors.append(f"{prefix}.tasks: define reader tasks with a representation")
            continue

        q_figure_ids: list[str] = []
        for task_name, task in tasks.items():
            task_prefix = f"{prefix}.tasks.{task_name}"
            if task_name not in READER_TASKS:
                warnings.append(f"{task_prefix}: nonstandard reader task")
            if not isinstance(task, dict):
                errors.append(f"{task_prefix}: must be an object")
                continue
            representation = str(task.get("representation", "")).strip().lower()
            if representation not in REPRESENTATIONS:
                errors.append(f"{task_prefix}.representation: expected one of {sorted(REPRESENTATIONS)}")
                continue
            if not specific_reason(task.get("reason")):
                errors.append(f"{task_prefix}.reason: explain the reader-task choice in at least 8 characters")
            figure_ids = task.get("figure_ids", [])
            if figure_ids is None:
                figure_ids = []
            if not isinstance(figure_ids, list) or not all(isinstance(fid, str) and fid for fid in figure_ids):
                errors.append(f"{task_prefix}.figure_ids: must be a list")
                figure_ids = []
            if representation == "figure" and not figure_ids:
                errors.append(f"{task_prefix}: representation=figure requires figure_ids")
            if representation != "figure" and figure_ids:
                warnings.append(f"{task_prefix}: figure_ids present while representation='{representation}'")

            for figure_id in figure_ids:
                entry = by_id.get(figure_id)
                if entry is None:
                    errors.append(f"{task_prefix}.figure_ids: unknown figure '{figure_id}'")
                    continue
                if str(entry.get("question_id", "")).strip() != qid:
                    errors.append(f"{task_prefix}: figure '{figure_id}' belongs to another question")
                if figure_id in used_figures:
                    warnings.append(f"{task_prefix}: figure '{figure_id}' is reused; verify it has one clear primary task")
                used_figures.add(figure_id)
                q_figure_ids.append(figure_id)

        body_ids = [fid for fid in q_figure_ids if str(by_id.get(fid, {}).get("placement", "")).lower() == "body"]
        summary["body_figure_count"] += len(set(body_ids))
        summary["questions"].append({
            "question_id": qid,
            "planned_task_count": len(tasks),
            "figure_count": len(set(q_figure_ids)),
            "body_figure_count": len(set(body_ids)),
        })

    expected = {str(item).strip() for item in expected_ids}
    for qid in sorted(expected - planned):
        errors.append(f"coverage_plan.questions: missing expected question '{qid}'")
    for qid in sorted(planned - expected):
        errors.append(f"coverage_plan.expected_question_ids: missing planned question '{qid}'")

    figure_qids = {
        str(entry.get("question_id", "")).strip()
        for entry in entries if str(entry.get("question_id", "")).strip().lower() not in {"", "paper"}
    }
    for qid in sorted(figure_qids - planned):
        errors.append(f"coverage_plan.questions: missing plan for figure question '{qid}'")

    for entry in entries:
        fid = str(entry.get("figure_id", ""))
        qid = str(entry.get("question_id", "")).strip().lower()
        if qid != "paper" and fid not in used_figures:
            errors.append(f"figure '{fid}' is not assigned to any reader task")

    return errors, summary


def validate_grammar_groups(entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_group: dict[str, str] = {}
    for index, entry in enumerate(entries):
        group = str(entry.get("visual_grammar_group", ""))
        grammar = entry.get("visual_grammar")
        if group and isinstance(grammar, dict):
            signature = json.dumps(grammar, ensure_ascii=False, sort_keys=True)
            if group in by_group and by_group[group] != signature:
                errors.append(f"figures[{index}].visual_grammar conflicts with group '{group}'")
            else:
                by_group[group] = signature
    return errors


def validate_distinct_outputs(entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    owner: dict[tuple[str, str], str] = {}
    for entry in entries:
        fid = str(entry.get("figure_id", ""))
        for field in ("latex_sha256", "editable_sha256", "backend_report_sha256"):
            value = str(entry.get(field, "")).strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                continue
            key = (field, value)
            if key in owner and owner[key] != fid:
                errors.append(f"figures '{owner[key]}' and '{fid}' reuse the same {field} artifact")
            else:
                owner[key] = fid
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CUMCM figure plans/intents without imposing figure quotas")
    parser.add_argument("intent_file", type=Path)
    parser.add_argument("--base-dir", type=Path, default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--require-sources", dest="require_sources", action="store_true")
    group.add_argument("--allow-missing-sources", dest="require_sources", action="store_false")
    parser.set_defaults(require_sources=True)
    parser.add_argument("--require-outputs", action="store_true")
    parser.add_argument("--require-coverage", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report: dict[str, Any] = {
        "checker": "figure-intent-and-reader-task-structure",
        "semantic_claim_validation": False,
        "fixed_figure_quota": False,
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
        seen: set[str] = set()
        base_dir = (args.base_dir or args.intent_file.parent).resolve()
        for index, entry in enumerate(entries):
            errors, warnings = validate_entry(entry, index, base_dir, args.require_sources, args.require_outputs)
            report["errors"].extend(errors)
            report["warnings"].extend(warnings)
            fid = str(entry.get("figure_id", ""))
            if fid in seen:
                report["errors"].append(f"figures[{index}].figure_id: duplicate '{fid}'")
            seen.add(fid)
        report["errors"].extend(validate_grammar_groups(entries))
        if args.require_outputs:
            report["errors"].extend(validate_distinct_outputs(entries))
        if args.require_coverage:
            errors, summary = validate_coverage(document, entries, base_dir)
            report["errors"].extend(errors)
            report["coverage_summary"] = summary
            report["warnings"].extend(summary.get("warnings", []))
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
