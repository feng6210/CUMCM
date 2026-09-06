#!/usr/bin/env python3
"""Deterministic regression cases for validate_figure_intent.py."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_figure_intent.py")
SPEC = importlib.util.spec_from_file_location("figure_intent_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot import {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SANITIZER_SCRIPT = Path(__file__).with_name("sanitize_office_metadata.py")
SANITIZER_SPEC = importlib.util.spec_from_file_location("office_metadata_sanitizer", SANITIZER_SCRIPT)
if SANITIZER_SPEC is None or SANITIZER_SPEC.loader is None:
    raise RuntimeError(f"Cannot import {SANITIZER_SCRIPT}")
SANITIZER = importlib.util.module_from_spec(SANITIZER_SPEC)
SANITIZER_SPEC.loader.exec_module(SANITIZER)


def base_entry(source: Path) -> dict:
    return {
        "figure_id": "q1-evidence",
        "question_id": "Q1",
        "purpose": "show a verified comparison",
        "claim_id": "claim-q1",
        "source_data": {
            "file": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "sheet": "results",
        },
        "variables": ["x", "y"],
        "units": {"x": "s", "y": "m"},
        "transformations": "none",
        "chart_or_diagram_type": "line",
        "backend_preference": "origin",
        "editable_output": "figures/q1.opju",
        "latex_output": "figures/q1.pdf",
        "caption_zh": "问题一结果对比",
        "narrative_role": "evidence",
        "reader_takeaway": "main and baseline differ under the frozen protocol",
        "exact_values_location": "result_table",
        "visual_grammar_group": "main-data",
        "visual_grammar": {
            "font_family": "Microsoft YaHei",
            "base_font_pt": 8,
            "palette": ["#1F4E79", "#C55A11"],
            "line_width_pt": 1.0,
            "style_profile": "cumcm-clean",
            "final_width_mm": 155,
            "legend_strategy": "top",
            "precision_policy": "正文图保留2位，精确值见结果表",
            "decorative_effects": ["none"],
        },
        "placement": "body",
        "panel_count": 1,
    }


def validate(
    entry: dict, root: Path, require_sources: bool = True, require_outputs: bool = False
) -> tuple[list[str], list[str]]:
    return MODULE.validate_entry(entry, 0, root, require_sources, require_outputs)


def expect_pass(name: str, entry: dict, root: Path, require_sources: bool = True) -> None:
    errors, _ = validate(entry, root, require_sources=require_sources)
    if errors:
        raise AssertionError(f"{name} should pass: {errors}")


def expect_fail(name: str, entry: dict, root: Path, needle: str) -> None:
    errors, _ = validate(entry, root)
    if not any(needle in error for error in errors):
        raise AssertionError(f"{name} should fail with {needle!r}: {errors}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mm-figure-intent-") as tmp:
        root = Path(tmp)
        source = root / "results.csv"
        source.write_text("x,y\n0,1\n", encoding="utf-8")
        good = base_entry(source)
        expect_pass("valid with sha metadata", good, root)

        missing = copy.deepcopy(good)
        del missing["reader_takeaway"]
        expect_fail("missing required field", missing, root, "reader_takeaway")

        bad_role = copy.deepcopy(good)
        bad_role["narrative_role"] = "summary"
        expect_fail("bad role", bad_role, root, "narrative_role")

        orientation_value = copy.deepcopy(good)
        orientation_value["narrative_role"] = "orientation"
        expect_fail("orientation as exact evidence", orientation_value, root, "orientation figures")

        diagram_evidence = copy.deepcopy(good)
        diagram_evidence["chart_or_diagram_type"] = "flowchart"
        diagram_evidence["backend_preference"] = "visio"
        diagram_evidence["editable_output"] = "figures/q1.vsdx"
        expect_fail("evidence diagram mismatch", diagram_evidence, root, "cannot use a structural diagram")

        screenshot = copy.deepcopy(good)
        screenshot["chart_or_diagram_type"] = "software_screenshot"
        expect_fail("software screenshot", screenshot, root, "unrecognized 'software_screenshot'")

        incomplete_3d = copy.deepcopy(good)
        incomplete_3d["chart_or_diagram_type"] = "surface_3d"
        expect_fail("3d without controls", incomplete_3d, root, "restricted_chart_justification")

        complete_3d = copy.deepcopy(incomplete_3d)
        complete_3d["restricted_chart_justification"] = "third dimension is a real response variable"
        complete_3d["alternative_2d_check"] = "contours hide the response ridge"
        complete_3d["projection_or_exact_table"] = "tables/q1_optimum.csv"
        expect_pass("controlled 3d", complete_3d, root)

        titled = copy.deepcopy(good)
        titled["internal_title"] = True
        expect_fail("internal paper title", titled, root, "LaTeX caption")

        fake_gradient = copy.deepcopy(good)
        fake_gradient["categorical_gradient"] = True
        expect_fail("unencoded gradient", fake_gradient, root, "color_encoding_variable")

        unaudited_effect = copy.deepcopy(good)
        unaudited_effect["visual_grammar"]["decorative_effects"] = ["transparent_fill"]
        expect_fail("effect without semantics", unaudited_effect, root, "effect_semantics")

        declared_effect = copy.deepcopy(unaudited_effect)
        declared_effect["effect_semantics"] = "nonsemantic"
        expect_pass("declared nonsemantic effect", declared_effect, root)

        weak_significance = copy.deepcopy(good)
        weak_significance["significance_annotation"] = True
        expect_fail("unproven significance", weak_significance, root, "statistical_test")

        weak_errorbar = copy.deepcopy(good)
        weak_errorbar["chart_or_diagram_type"] = "errorbar"
        expect_fail("errorbar without uncertainty semantics", weak_errorbar, root, "uncertainty_type")

        bad_style = copy.deepcopy(good)
        bad_style["visual_grammar"]["style_profile"] = "neon-dashboard"
        expect_fail("bad style profile", bad_style, root, "style_profile")

        dense_body = copy.deepcopy(good)
        dense_body["panel_count"] = 7
        dense_body["multi_panel_justification"] = "shared-scale scenario comparison"
        expect_fail("dense body", dense_body, root, ">6 panels should move to appendix")

        dense_appendix = copy.deepcopy(dense_body)
        dense_appendix["placement"] = "appendix"
        expect_pass("dense appendix", dense_appendix, root)

        missing_source = copy.deepcopy(good)
        missing_source["source_data"]["file"] = str(root / "missing.csv")
        expect_fail("missing source", missing_source, root, "source_data: missing")
        expect_pass("draft may allow missing source", missing_source, root, require_sources=False)

        bad_hash = copy.deepcopy(good)
        bad_hash["source_data"]["sha256"] = "0" * 64
        expect_fail("source hash mismatch", bad_hash, root, "source_data.sha256: mismatch")

        final_outputs = copy.deepcopy(good)
        editable = root / "q1.opju"
        latex = root / "q1.pdf"
        editable.write_bytes(b"CPYUA 4.3668 178\n" + b"0" * 1200)
        latex.write_bytes(b"%PDF-1.4\n" + b"0" * 300 + b"\n%%EOF\n")
        final_outputs["editable_output"] = str(editable)
        final_outputs["latex_output"] = str(latex)
        final_outputs["editable_sha256"] = hashlib.sha256(editable.read_bytes()).hexdigest()
        final_outputs["latex_sha256"] = hashlib.sha256(latex.read_bytes()).hexdigest()
        backend_report = root / "q1.origin-report.json"
        backend_report.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "style_profile": "cumcm-clean",
                    "effective_palette": ["#1F4E79", "#C55A11"],
                    "decorative_effects": ["none"],
                    "input_sha256": good["source_data"]["sha256"],
                    "project_saved": True,
                    "pdf_exported": True,
                    "project_reopened": True,
                    "pdf_reopened": True,
                    "metadata_sanitized": True,
                    "anonymous_check": True,
                    "effective_min_font_pt": 8.5,
                    "final_width_mm": 155,
                    "opju_sha256": final_outputs["editable_sha256"],
                    "pdf_sha256": final_outputs["latex_sha256"],
                }
            ),
            encoding="utf-8",
        )
        final_outputs["backend_report"] = str(backend_report)
        final_outputs["backend_report_sha256"] = hashlib.sha256(backend_report.read_bytes()).hexdigest()
        final_errors, _ = validate(final_outputs, root, require_outputs=True)
        if final_errors:
            raise AssertionError(f"final output hashes should pass: {final_errors}")

        missing_output_hash = copy.deepcopy(final_outputs)
        del missing_output_hash["latex_sha256"]
        final_errors, _ = validate(missing_output_hash, root, require_outputs=True)
        if not any("latex_sha256" in error for error in final_errors):
            raise AssertionError(f"missing final output hash should fail: {final_errors}")

        fake_pdf = copy.deepcopy(final_outputs)
        latex.write_bytes(b"%PDF-test")
        fake_pdf["latex_sha256"] = hashlib.sha256(latex.read_bytes()).hexdigest()
        final_errors, _ = validate(fake_pdf, root, require_outputs=True)
        if not any("complete PDF" in error for error in final_errors):
            raise AssertionError(f"header-only fake PDF should fail: {final_errors}")
        latex.write_bytes(b"%PDF-1.4\n" + b"0" * 300 + b"\n%%EOF\n")

        missing_runtime_report = copy.deepcopy(final_outputs)
        del missing_runtime_report["backend_report"]
        final_errors, _ = validate(missing_runtime_report, root, require_outputs=True)
        if not any("backend_report" in error for error in final_errors):
            raise AssertionError(f"missing runtime report should fail: {final_errors}")

        fake_native = copy.deepcopy(final_outputs)
        editable.write_bytes(b"native")
        fake_native["editable_sha256"] = hashlib.sha256(editable.read_bytes()).hexdigest()
        final_errors, _ = validate(fake_native, root, require_outputs=True)
        if not any("complete Origin project" in error for error in final_errors):
            raise AssertionError(f"fake native file should fail: {final_errors}")
        editable.write_bytes(b"CPYUA 4.3668 178\n" + b"0" * 1200)

        final_effect = copy.deepcopy(final_outputs)
        final_effect["visual_grammar"]["decorative_effects"] = ["transparent_fill"]
        final_effect["effect_semantics"] = "nonsemantic"
        final_errors, _ = validate(final_effect, root, require_outputs=True)
        if not any("effect_audit" in error for error in final_errors):
            raise AssertionError(f"final decorative effect without audit should fail: {final_errors}")

        visio_entry = copy.deepcopy(good)
        visio_vsdx = root / "q1.vsdx"
        with zipfile.ZipFile(visio_vsdx, "w") as archive:
            archive.writestr("visio/document.xml", "<VisioDocument/>")
        visio_entry.update(
            {
                "narrative_role": "mechanism",
                "claim_id": "not_applicable",
                "exact_values_location": "not_applicable",
                "chart_or_diagram_type": "flowchart",
                "backend_preference": "visio",
                "editable_output": str(visio_vsdx),
                "latex_output": str(latex),
                "editable_sha256": hashlib.sha256(visio_vsdx.read_bytes()).hexdigest(),
                "latex_sha256": hashlib.sha256(latex.read_bytes()).hexdigest(),
            }
        )
        visio_entry["visual_grammar"]["style_profile"] = "cumcm-mechanism"
        visio_entry["visual_grammar"]["legend_strategy"] = "none"
        visio_report = root / "q1.visio-report.json"
        visio_payload = {
            "status": "PASSED",
            "style_profile": "cumcm-mechanism",
            "input_sha256": good["source_data"]["sha256"],
            "document_saved": True,
            "pdf_exported": True,
            "document_reopened": True,
            "pdf_reopened": True,
            "metadata_sanitized": True,
            "anonymous_check": True,
            "unsupported_groups": 0,
            "base_font_pt": 8,
            "effective_min_font_pt": 8,
            "final_width_mm": 155,
            "line_width_pt": 1.0,
            "legend_strategy": "none",
            "decorative_effects": ["none"],
            "effective_palette": ["#1F4E79", "#C55A11"],
            "pdf_fonts": ["MicrosoftYaHei"],
            "vsdx_sha256": visio_entry["editable_sha256"],
            "pdf_sha256": visio_entry["latex_sha256"],
        }
        visio_report.write_text(json.dumps(visio_payload), encoding="utf-8")
        visio_entry["backend_report"] = str(visio_report)
        visio_entry["backend_report_sha256"] = hashlib.sha256(visio_report.read_bytes()).hexdigest()
        final_errors, _ = validate(visio_entry, root, require_outputs=True)
        if final_errors:
            raise AssertionError(f"sanitized reopened Visio output should pass: {final_errors}")

        wrong_visio_base_font = copy.deepcopy(visio_entry)
        wrong_visio_base_font["visual_grammar"]["base_font_pt"] = 7
        final_errors, _ = validate(wrong_visio_base_font, root, require_outputs=True)
        if not any("backend_report.base_font_pt" in error for error in final_errors):
            raise AssertionError(f"Visio base/effective font semantics should not be mixed: {final_errors}")

        path_leaking_vsdx = root / "path-leak.vsdx"
        with zipfile.ZipFile(path_leaking_vsdx, "w") as archive:
            archive.writestr("visio/document.xml", "<VisioDocument/>")
            archive.writestr(
                "visio/_rels/document.xml.rels",
                '<Relationship Target="file:///C:/Users/ASUS/private/source.xlsx"/>',
            )
        path_findings = SANITIZER.inspect_vsdx_metadata(path_leaking_vsdx)
        if not any("absolute-path" in finding for finding in path_findings):
            raise AssertionError(f"absolute VSDX relationship path should be detected: {path_findings}")

        matlab_spec = root / "q1-matlab.json"
        matlab_spec.write_text(
            json.dumps({
                "chart_type": "line", "x": "x", "y": ["y"],
                "transformations": "none", "source_csv": str(source),
            }), encoding="utf-8",
        )
        matlab_fig = root / "q1.fig"
        matlab_pdf = root / "q1-matlab.pdf"
        matlab_fig.write_bytes(b"MATLAB 5.0 MAT-file" + b"0" * 1200)
        matlab_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 300 + b"\n%%EOF\n")
        matlab_entry = copy.deepcopy(good)
        matlab_entry.update({
            "backend_preference": "matlab",
            "editable_output": str(matlab_fig),
            "latex_output": str(matlab_pdf),
            "editable_sha256": hashlib.sha256(matlab_fig.read_bytes()).hexdigest(),
            "latex_sha256": hashlib.sha256(matlab_pdf.read_bytes()).hexdigest(),
            "renderer_spec": {
                "file": str(matlab_spec),
                "sha256": hashlib.sha256(matlab_spec.read_bytes()).hexdigest(),
            },
        })
        matlab_report = root / "q1.matlab-report.json"
        matlab_payload = {
            "status": "RUNTIME_VERIFIED",
            "style_profile": "cumcm-clean",
            "effective_palette": ["#1F4E79", "#C55A11"],
            "font_family": "Microsoft YaHei",
            "base_font_pt": 8,
            "effective_min_font_pt": 7.5,
            "final_width_mm": 155,
            "line_width_pt": 1.0,
            "legend_strategy": "top",
            "decorative_effects": ["none"],
            "source": {"sha256": good["source_data"]["sha256"]},
            "spec": {"sha256": matlab_entry["renderer_spec"]["sha256"]},
            "render_contract": {
                "chart_type": "line", "variables": ["x", "y"],
                "transformations": "none",
                "source_sha256": good["source_data"]["sha256"],
                "spec_sha256": matlab_entry["renderer_spec"]["sha256"],
            },
            "outputs": [
                {"sha256": matlab_entry["editable_sha256"]},
                {"sha256": matlab_entry["latex_sha256"]},
            ],
            "reopen_check": {"fig": True, "pdf": True},
        }
        matlab_report.write_text(json.dumps(matlab_payload), encoding="utf-8")
        matlab_entry["backend_report"] = str(matlab_report)
        matlab_entry["backend_report_sha256"] = hashlib.sha256(matlab_report.read_bytes()).hexdigest()
        final_errors, _ = validate(matlab_entry, root, require_outputs=True)
        if final_errors:
            raise AssertionError(f"hash-bound MATLAB render contract should pass: {final_errors}")

        lied_about_chart = copy.deepcopy(matlab_entry)
        lied_about_chart["chart_or_diagram_type"] = "area"
        final_errors, _ = validate(lied_about_chart, root, require_outputs=True)
        if not any("render_contract.chart_type" in error for error in final_errors):
            raise AssertionError(f"intent chart lie should fail: {final_errors}")

        lied_about_variables = copy.deepcopy(matlab_entry)
        lied_about_variables["variables"] = ["totally_different"]
        final_errors, _ = validate(lied_about_variables, root, require_outputs=True)
        if not any("render_contract.variables" in error for error in final_errors):
            raise AssertionError(f"intent variable lie should fail: {final_errors}")

        unsupported_visio = copy.deepcopy(visio_entry)
        visio_payload["unsupported_groups"] = 1
        visio_report.write_text(json.dumps(visio_payload), encoding="utf-8")
        unsupported_visio["backend_report_sha256"] = hashlib.sha256(visio_report.read_bytes()).hexdigest()
        final_errors, _ = validate(unsupported_visio, root, require_outputs=True)
        if not any("unsupported_groups" in error for error in final_errors):
            raise AssertionError(f"unsupported Visio groups should fail: {final_errors}")

        wrong_python_source = copy.deepcopy(good)
        wrong_python_source["backend_preference"] = "python"
        wrong_python_source["editable_output"] = "figures/q1.bin"
        expect_fail("wrong python source", wrong_python_source, root, "Python source")

        grammar_a = copy.deepcopy(good)
        grammar_b = copy.deepcopy(good)
        grammar_b["figure_id"] = "q2-evidence"
        grammar_b["visual_grammar"]["palette"] = ["#000000"]
        grammar_errors = MODULE.validate_grammar_groups([grammar_a, grammar_b])
        if not any("visual_grammar conflicts with group" in error for error in grammar_errors):
            raise AssertionError(f"visual grammar conflict should fail: {grammar_errors}")

        validation_figure = copy.deepcopy(good)
        validation_figure["figure_id"] = "q1-validation"
        validation_figure["narrative_role"] = "validation"
        validation_figure["claim_id"] = "claim-q1"
        validation_figure["variables"] = ["x", "residual"]
        validation_figure["transformations"] = "residual = observed - predicted"
        validation_figure["chart_or_diagram_type"] = "scatter"
        validation_figure["validation_target"] = "main-model residual structure"
        validation_figure["validation_method"] = "residual scatter against fitted order"
        comparison_figure = copy.deepcopy(good)
        comparison_figure["figure_id"] = "q1-comparison"
        comparison_figure["transformations"] = "baseline-to-main absolute difference"
        comparison_figure["chart_or_diagram_type"] = "bar"
        robustness_figure = copy.deepcopy(validation_figure)
        robustness_figure["figure_id"] = "q1-robustness"
        robustness_figure["transformations"] = "parameter sweep envelope"
        robustness_figure["chart_or_diagram_type"] = "area"
        decomposition = root / "decomposition.json"
        decomposition.write_text('{"expected_question_ids":["Q1"]}\n', encoding="utf-8")
        coverage_document = {
            "coverage_plan": {
                "expected_question_ids": ["Q1"],
                "expected_question_ids_source": {
                    "file": str(decomposition),
                    "sha256": hashlib.sha256(decomposition.read_bytes()).hexdigest(),
                    "field": "expected_question_ids",
                },
                "questions": [
                    {
                        "question_id": "Q1",
                        "core_claim_ids": ["claim-q1"],
                        "slots": {
                            "data_diagnosis": {"figure_ids": [], "omission_reason": "no raw observations"},
                            "mechanism": {"figure_ids": [], "omission_reason": "closed-form transformation"},
                            "main_result": {"figure_ids": ["q1-evidence"]},
                            "comparison": {"figure_ids": ["q1-comparison"]},
                            "validation": {"figure_ids": ["q1-validation"]},
                            "robustness": {"figure_ids": ["q1-robustness"]},
                        },
                    }
                ]
            },
            "figures": [good, validation_figure, comparison_figure, robustness_figure],
        }
        coverage_errors, coverage_summary = MODULE.validate_coverage(
            coverage_document, coverage_document["figures"], root
        )
        if coverage_errors or coverage_summary["question_count"] != 1 or coverage_summary["body_figure_count"] != 4:
            raise AssertionError(f"complete coverage should pass: {coverage_errors}, {coverage_summary}")

        validation_without_method = copy.deepcopy(validation_figure)
        del validation_without_method["validation_method"]
        expect_fail(
            "validation without independent method", validation_without_method, root,
            "validation_method",
        )

        too_few_figures = copy.deepcopy(coverage_document)
        too_few_figures["coverage_plan"]["questions"][0]["slots"]["comparison"] = {
            "figure_ids": [], "omission_reason": "no competing route exists"
        }
        too_few_figures["coverage_plan"]["questions"][0]["slots"]["robustness"] = {
            "figure_ids": [], "omission_reason": "deterministic exact input only"
        }
        too_few_figures["figures"] = too_few_figures["figures"][:2]
        coverage_errors, _ = MODULE.validate_coverage(
            too_few_figures, too_few_figures["figures"], root
        )
        # Reader-task-driven planning has no minimum figure quota.
        if coverage_errors:
            raise AssertionError(f"two useful figures with explained omissions should pass: {coverage_errors}")

        missing_validation = copy.deepcopy(coverage_document)
        missing_validation["coverage_plan"]["questions"][0]["slots"]["validation"]["figure_ids"] = []
        missing_validation["coverage_plan"]["questions"][0]["slots"]["validation"]["omission_reason"] = "residual checks are fully reported in the numerical appendix"
        missing_validation["figures"] = [figure for figure in missing_validation["figures"] if figure["figure_id"] != "q1-validation"]
        coverage_errors, _ = MODULE.validate_coverage(
            missing_validation, missing_validation["figures"], root
        )
        if coverage_errors:
            raise AssertionError(f"validation reported without a standalone figure should pass: {coverage_errors}")

        weak_omission = copy.deepcopy(coverage_document)
        weak_omission["coverage_plan"]["questions"][0]["slots"]["mechanism"]["omission_reason"] = "N/A"
        coverage_errors, _ = MODULE.validate_coverage(weak_omission, weak_omission["figures"], root)
        if not any("at least 8 characters" in error for error in coverage_errors):
            raise AssertionError(f"placeholder omission reason should fail: {coverage_errors}")

        same_figure = copy.deepcopy(coverage_document)
        same_figure["coverage_plan"]["questions"][0]["slots"]["validation"]["figure_ids"] = [
            "q1-evidence"
        ]
        same_figure["figures"] = [figure for figure in same_figure["figures"] if figure["figure_id"] != "q1-validation"]
        coverage_errors, coverage_summary = MODULE.validate_coverage(same_figure, same_figure["figures"], root)
        if coverage_errors or not any("q1-evidence" in warning and "is reused" in warning for warning in coverage_summary["warnings"]):
            raise AssertionError(f"one figure serving two tasks must trigger reuse review: {coverage_errors}, {coverage_summary}")

        repeated_optional_slot = copy.deepcopy(coverage_document)
        repeated_optional_slot["coverage_plan"]["questions"][0]["slots"]["comparison"] = {
            "figure_ids": ["q1-evidence"]
        }
        repeated_optional_slot["figures"] = [figure for figure in repeated_optional_slot["figures"] if figure["figure_id"] != "q1-comparison"]
        coverage_errors, coverage_summary = MODULE.validate_coverage(
            repeated_optional_slot, repeated_optional_slot["figures"], root
        )
        if coverage_errors or not any("q1-evidence" in warning and "is reused" in warning for warning in coverage_summary["warnings"]):
            raise AssertionError(f"reused comparison figure must trigger reuse review: {coverage_errors}, {coverage_summary}")

        list_claims = copy.deepcopy(coverage_document)
        list_claims["figures"][0]["claim_id"] = ["claim-q1", "claim-q1-secondary"]
        list_claims["coverage_plan"]["questions"][0]["core_claim_ids"] = [
            "claim-q1", "claim-q1-secondary"
        ]
        coverage_errors, coverage_summary = MODULE.validate_coverage(
            list_claims, list_claims["figures"], root
        )
        if coverage_errors or coverage_summary["question_count"] != 1 or coverage_summary["body_figure_count"] != 4:
            raise AssertionError(f"claim-id list should pass: {coverage_errors}, {coverage_summary}")

        missing_expected_question = copy.deepcopy(coverage_document)
        missing_expected_question["coverage_plan"]["expected_question_ids"].append("Q2")
        coverage_errors, _ = MODULE.validate_coverage(
            missing_expected_question, missing_expected_question["figures"], root
        )
        if not any("missing expected question 'Q2'" in error for error in coverage_errors):
            raise AssertionError(f"missing whole question should fail: {coverage_errors}")

        mismatched_source = copy.deepcopy(coverage_document)
        mismatched_source["coverage_plan"]["expected_question_ids"] = ["Q1", "Q2"]
        coverage_errors, _ = MODULE.validate_coverage(
            mismatched_source, mismatched_source["figures"], root
        )
        if not any("does not match decomposition source" in error for error in coverage_errors):
            raise AssertionError(f"unbound expected-question expansion should fail: {coverage_errors}")

        stray_claim = copy.deepcopy(coverage_document)
        stray_claim["figures"][0]["claim_id"] = "secondary"
        stray = copy.deepcopy(good)
        stray["figure_id"] = "q1-stray"
        stray["claim_id"] = "claim-q1"
        stray_claim["figures"].append(stray)
        coverage_errors, _ = MODULE.validate_coverage(stray_claim, stray_claim["figures"], root)
        if not any("is not assigned to any reader task" in error for error in coverage_errors):
            raise AssertionError(f"stray evidence figure should fail: {coverage_errors}")

        uncovered_core_claim = copy.deepcopy(coverage_document)
        for figure in uncovered_core_claim["figures"]:
            figure["claim_id"] = "secondary"
        coverage_errors, _ = MODULE.validate_coverage(
            uncovered_core_claim, uncovered_core_claim["figures"], root
        )
        # Claim support is checked by result-to-claim audits, not mandatory plots.
        if coverage_errors:
            raise AssertionError(f"claims need not each have a separate figure: {coverage_errors}")

        none_main = copy.deepcopy(coverage_document)
        none_main["figures"][0]["chart_or_diagram_type"] = "none"
        # Type validity belongs to single-entry validation; coverage handles tasks.
        expect_fail("none is not a chart", none_main["figures"][0], root, "unrecognized 'none'")

        orphan_mechanism = copy.deepcopy(coverage_document)
        mechanism = copy.deepcopy(good)
        mechanism.update(
            {
                "figure_id": "q1-orphan-mechanism",
                "narrative_role": "mechanism",
                "claim_id": "not_applicable",
                "exact_values_location": "not_applicable",
                "chart_or_diagram_type": "flowchart",
                "backend_preference": "visio",
                "editable_output": "figures/q1-orphan.vsdx",
            }
        )
        mechanism["visual_grammar"]["style_profile"] = "cumcm-mechanism"
        orphan_mechanism["figures"].append(mechanism)
        coverage_errors, _ = MODULE.validate_coverage(
            orphan_mechanism, orphan_mechanism["figures"], root
        )
        if not any("q1-orphan-mechanism" in error and "not assigned" in error for error in coverage_errors):
            raise AssertionError(f"orphan mechanism figure should fail: {coverage_errors}")

        invalid_claim_list = copy.deepcopy(good)
        invalid_claim_list["claim_id"] = ["not_applicable"]
        expect_fail("not-applicable claim list", invalid_claim_list, root, "require real claim ids")

        second_source = root / "more.csv"
        second_source.write_text("x,y\n1,2\n", encoding="utf-8")
        multiple_sources = copy.deepcopy(good)
        multiple_sources["source_data"] = {
            "sources": [
                {"file": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
                {"file": str(second_source), "sha256": hashlib.sha256(second_source.read_bytes()).hexdigest()},
            ]
        }
        expect_pass("multiple source hashes", multiple_sources, root)

        missing_second_hash = copy.deepcopy(multiple_sources)
        del missing_second_hash["source_data"]["sources"][1]["sha256"]
        expect_fail("missing one of multiple source hashes", missing_second_hash, root, "source_data.sha256: 64-char hash required")

        partial_runtime_sources = copy.deepcopy(final_outputs)
        partial_runtime_sources["source_data"] = multiple_sources["source_data"]
        partial_errors, _ = validate(partial_runtime_sources, root, require_outputs=True)
        if not any("missing declared source hashes" in error for error in partial_errors):
            raise AssertionError(f"partial runtime source coverage should fail: {partial_errors}")

        # Matching bindings do not prove duplicate information: view, zoom or
        # annotation can differ. Semantic duplication belongs to visual review.
        shared_bindings = copy.deepcopy(coverage_document)
        shared_bindings["figures"][1]["variables"] = shared_bindings["figures"][0]["variables"]
        shared_bindings["figures"][1]["transformations"] = shared_bindings["figures"][0]["transformations"]
        shared_bindings["figures"][1]["chart_or_diagram_type"] = shared_bindings["figures"][0]["chart_or_diagram_type"]
        coverage_errors, _ = MODULE.validate_coverage(shared_bindings, shared_bindings["figures"], root)
        if coverage_errors:
            raise AssertionError(f"planner cannot infer semantic duplication from bindings alone: {coverage_errors}")

        duplicate_artifact = copy.deepcopy(coverage_document)
        duplicate_artifact["figures"][0]["latex_sha256"] = "a" * 64
        duplicate_artifact["figures"][1]["latex_sha256"] = "a" * 64
        # Actual byte-identical final artifacts are checked by the final-output
        # validator, not the planning-stage coverage function.
        coverage_errors = MODULE.validate_distinct_outputs(duplicate_artifact["figures"])
        if not any("reuse the same latex_sha256 artifact" in error for error in coverage_errors):
            raise AssertionError(f"reused physical figure output should fail: {coverage_errors}")

        zero_figure_plan = copy.deepcopy(coverage_document)
        zero_figure_plan["figures"] = []
        zero_figure_plan["coverage_plan"]["questions"][0]["tasks"] = {
            "main_result": {"representation": "table", "reason": "only two exact result values; no shape or trend to visualize"},
            "validation": {"representation": "appendix", "reason": "exact residual and feasibility recomputation retained as tables"},
        }
        coverage_errors, coverage_summary = MODULE.validate_coverage(zero_figure_plan, [], root)
        if coverage_errors or coverage_summary["body_figure_count"] != 0:
            raise AssertionError(f"well-explained table/appendix plan needs no figure quota: {coverage_errors}")

        unmet_figure_task = copy.deepcopy(zero_figure_plan)
        unmet_figure_task["coverage_plan"]["questions"][0]["tasks"]["main_result"] = {
            "representation": "figure", "reason": "nonlinear tradeoff must be visible to the reader", "figure_ids": []
        }
        coverage_errors, _ = MODULE.validate_coverage(unmet_figure_task, [], root)
        if not any("representation=figure requires figure_ids" in error for error in coverage_errors):
            raise AssertionError(f"an explicitly chosen figure task cannot be empty: {coverage_errors}")

    print("PASS: figure-intent entry, artifact-integrity and reader-task coverage regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
