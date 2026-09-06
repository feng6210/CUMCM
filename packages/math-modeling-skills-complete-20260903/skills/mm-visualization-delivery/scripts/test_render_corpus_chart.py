#!/usr/bin/env python3
"""Executable family coverage and fail-closed input tests; not aesthetic approval."""
import argparse
import copy
import csv
import json
from pathlib import Path
import pandas as pd

import render_corpus_chart as rc
import validate_figure_intent as intent_validator
from visual_review_contract import intent_digest, CHECKS


def integration(directory, family, report):
    """Use real rendered files; synthetic review is ONLY a parser test fixture."""
    source, spec_path = directory/"data.csv", directory/"spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    preview = directory/"preview"
    pdf = preview/("demo-"+family+".pdf")
    png = preview/("demo-"+family+".png")
    manifest = preview/("demo-"+family+".manifest.json")
    style = report["style"]
    entry = {
        "figure_id": "demo-"+family, "question_id": "DEMO_ONLY", "purpose": "TEST_ONLY校验绘图接口，不构成任何实际论文结论",
        "claim_id": "SYNTHETIC_TEST_NOT_A_PAPER_CLAIM", "source_data": {"file": str(source), "sha256": rc.sha256(source)},
        "variables": report["render_contract"]["variables"], "units": report["render_contract"]["units"],
        "transformations": "none", "chart_or_diagram_type": family, "backend_preference": "matplotlib",
        "editable_output": str(spec_path), "editable_sha256": rc.sha256(spec_path), "latex_output": str(pdf), "latex_sha256": rc.sha256(pdf),
        "caption_zh": "合成数据接口测试图，非实验结果", "narrative_role": "evidence", "reader_takeaway": "TEST_ONLY人工合成样例用于验证文件与配置绑定",
        "exact_values_location": "machine_readable_table", "visual_grammar_group": "TEST_ONLY",
        "visual_grammar": {"font_family": style["font_family"], "base_font_pt": style["base_font_pt"], "palette": style["effective_palette"], "line_width_pt": style["line_width_pt"], "style_profile": style["style_profile"], "final_width_mm": 160, "legend_strategy": style["legend_strategy"], "precision_policy": "演示图，精确值见合成CSV；不形成论文声明", "decorative_effects": style["decorative_effects"]},
        "placement": "appendix", "panel_count": 1,
        "renderer_spec": {"file": str(spec_path), "sha256": rc.sha256(spec_path)}, "backend_report": str(manifest), "backend_report_sha256": rc.sha256(manifest),
    }
    if family in intent_validator.RESTRICTED_TYPES:
        entry.update(restricted_chart_justification="TEST_ONLY本样例检验受限图型元数据接口而非对实题的选图批准", alternative_2d_check="TEST_ONLY配套CSV提供原始精确值，真实任务需另审二维替代设计", projection_or_exact_table=str(source))
    if family == "line_interval":
        entry.update(uncertainty_definition=spec["uncertainty_definition"], uncertainty_source=spec["uncertainty_source"])
    for final in (False, True):
        errors, _ = intent_validator.validate_entry(entry, 0, directory, True, final)
        assert not errors, errors
    errors, _ = intent_validator.validate_entry(entry, 0, directory, True, True, True)
    assert errors, "missing independent review wrongly accepted"
    fixture = directory/"TEST_ONLY_SYNTHETIC_REVIEW_CONTRACT"; fixture.mkdir()
    catalog = fixture/"catalog.json"
    catalog.write_text(json.dumps({"test_only": True, "cards": [{"card_id": "TEST_ONLY", "preview_sha256": rc.sha256(png)}]}), encoding="utf-8")
    entry["style_reference"] = {"card_id": "TEST_ONLY", "catalog": {"file": str(catalog), "sha256": rc.sha256(catalog)}, "preview": {"file": str(png), "sha256": rc.sha256(png)}}
    review = {"test_only": True, "disclaimer": "SYNTHETIC_SCHEMA_FIXTURE_NOT_ACTUAL_REVIEW_NO_AESTHETIC_APPROVAL", "decision": "PASSED", "generator_id": "synthetic-test-generator", "reviewers": [{"role": "visual", "reviewer_id": "synthetic-test-reviewer-not-real-agent", "origin": "same-family-fresh"}], "bindings": {"output": rc.sha256(pdf), "editable": rc.sha256(spec_path), "intent": intent_digest(entry)}, "checks": {key: {"status": "PASSED", "note": "TEST_ONLY合成结构占位：测试哈希契约解析，不代表实际视觉观察"} for key in CHECKS | {"numeric_consistency"}}, "blocking_findings": []}
    review_path = fixture/"review.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
    entry["visual_review"] = {"file": str(review_path), "sha256": rc.sha256(review_path)}
    errors, _ = intent_validator.validate_entry(entry, 0, directory, True, True, True)
    assert not errors, errors
    (fixture/"intent.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    changed = copy.deepcopy(entry); changed["caption_zh"] = "改变后的图题必须重新审查"
    errors, _ = intent_validator.validate_entry(changed, 0, directory, True, True, True)
    assert any("stale intent" in err for err in errors), errors
    changed = copy.deepcopy(entry); changed["variables"] = ["fake_field"]
    errors, _ = intent_validator.validate_entry(changed, 0, directory, True, True)
    assert any("render_contract.variables" in err for err in errors), errors
    changed = copy.deepcopy(entry); changed["source_data"]["sha256"] = "0"*64
    errors, _ = intent_validator.validate_entry(changed, 0, directory, True, True)
    assert any("sha256" in err for err in errors), errors


def run(output_dir, pdf_python=None):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    reports = []

    def check(name, func):
        try:
            func()
            reports.append({"test": name, "status": "PASS"})
        except Exception as exc:
            reports.append({"test": name, "status": "FAIL", "error": repr(exc)})

    def fail(name, family, mutation):
        spec, rows = rc.demo_spec(family)
        mutation(spec, rows)
        def execute():
            try:
                rc.validate(spec, pd.DataFrame(rows))
            except (ValueError, KeyError, TypeError):
                return
            raise AssertionError("invalid fixture was accepted")
        check(name, execute)

    for family in rc.FAMILIES:
        def positive(family=family):
            directory = output_dir/family; directory.mkdir()
            spec, rows = rc.demo_spec(family)
            source = directory/"data.csv"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            path = directory/"spec.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            before = rc.sha256(source)
            report = rc.render(path, directory/"preview", pdf_python)
            assert rc.sha256(source) == before == report["source"]["sha256_after"]
            assert report["status"] == "RUNTIME_VERIFIED", report["warnings"]
            assert report["reopen_check"] == {"pdf": True, "svg": True, "png": True}
            assert report["semantic_claim_validation"] is False
            assert report["visual_review"] == "PENDING_REFERENCE_COMPARISON"
            assert report["data_status"].startswith("DEMO_ONLY")
            assert report["render_contract"]["statistics_computed"] is False
            for item in report["outputs"]:
                assert rc.sha256(directory/"preview"/item["path"]) == item["sha256"]
            try:
                rc.render(path, directory/"preview", pdf_python)
            except FileExistsError:
                pass
            else:
                raise AssertionError("overwrite allowed")
        check("runtime:"+family, positive)
        def interface(family=family):
            directory = output_dir/family
            report = json.loads((directory/"preview"/("demo-"+family+".manifest.json")).read_text(encoding="utf-8"))
            integration(directory, family, report)
        check("intent_interface_and_synthetic_review_contract:"+family, interface)
    fail("log_x_nonpositive", "log_x", lambda s,r: r[0].update(t=0))
    fail("log_y_nonpositive", "log_y", lambda s,r: r[0].update(a=-1))
    fail("nonfinite", "line", lambda s,r: r[0].update(a=float("nan")))
    fail("infinite", "scatter_3d", lambda s,r: r[0].update(z=float("inf")))
    fail("missing_units", "line", lambda s,r: s["units"].pop("a"))
    fail("missing_column", "line", lambda s,r: s["series"][0].update(column="not_here"))
    fail("duplicate_category", "bar", lambda s,r: r[1].update(metric=r[0]["metric"]))
    fail("duplicate_series", "line", lambda s,r: s["series"][1].update(column="a"))
    fail("unordered_line", "line", lambda s,r: r.reverse())
    fail("invalid_interval", "line_interval", lambda s,r: r[0].update(lower=100))
    fail("missing_interval_definition", "line_interval", lambda s,r: s.pop("uncertainty_definition"))
    fail("missing_grid", "surface_wireframe", lambda s,r: r.pop())
    fail("duplicate_grid", "surface_wireframe", lambda s,r: r.append(copy.deepcopy(r[0])))
    fail("contour_clipping", "contour", lambda s,r: s.update(levels=[3,4]))
    fail("contour_unordered_levels", "contour", lambda s,r: s.update(levels=[6,2]))
    fail("unknown_model_fit", "line", lambda s,r: s.update(fit="cubic"))
    fail("axis_clipping", "line", lambda s,r: s.update(ylim=[2,3]))
    fail("transformation", "line", lambda s,r: s.update(transformations="normalize"))
    fail("unsafe_basename", "line", lambda s,r: s.update(figure_id="../escape"))
    fail("tiny_font", "line", lambda s,r: s.update(base_font_pt=7))
    fail("false_width", "line", lambda s,r: s.update(width_mm=90))
    fail("nonsemantic_3d", "scatter_3d", lambda s,r: s.pop("spatial_explanation"))
    fail("missing_3d_companion", "area_3d", lambda s,r: s.pop("companion"))
    fail("area_baseline_clipping", "area_3d", lambda s,r: s.update(z_baseline=100))
    fail("area_duplicate_positions", "area_3d", lambda s,r: s["series"][1].update(position=1))
    fail("negative_stack", "stacked_bar", lambda s,r: r[0].update(a=-1))
    fail("nonadditive_stack", "stacked_bar", lambda s,r: s.pop("additive_semantics"))
    fail("pie_invalid_total", "pie", lambda s,r: r[0].update(percent=34))
    fail("pie_negative", "pie", lambda s,r: r[0].update(percent=-35))
    fail("donut_missing_semantics", "donut", lambda s,r: s.pop("composition_semantics"))
    fail("radar_not_normalized", "radar", lambda s,r: s.pop("normalization_definition"))
    fail("radar_nonzero_baseline", "radar", lambda s,r: s.update(vmin=1))
    fail("radar_clipping", "radar", lambda s,r: s.update(vmax=3))
    fail("parallel_direction_unknown", "parallel_coordinates", lambda s,r: s.update(positive_direction=False))
    fail("dual_axis_binding", "dual_axis", lambda s,r: s["series"][1].update(axis="left"))
    fail("dual_axis_missing_alternative", "dual_axis", lambda s,r: s.pop("aligned_alternative_check"))
    fail("vector_scale_zero", "vector_field", lambda s,r: s.update(vector_scale=0))
    fail("bubble_negative_size", "bubble", lambda s,r: r[0].update(size=-1))
    fail("bubble_missing_legend", "bubble", lambda s,r: s.pop("size_legend_values"))
    fail("implicit_step", "step", lambda s,r: s.pop("step_where"))
    fail("palette_not_color", "line", lambda s,r: s.update(palette=["foo", "bar"]))
    report = {"test_scope": "runtime/integrity only; no numerical or aesthetic certification", "passed": sum(r["status"] == "PASS" for r in reports), "failed": sum(r["status"] != "PASS" for r in reports), "tests": reports}
    (output_dir/"TEST_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New immutable test directory")
    parser.add_argument("--pdf-python", type=Path, help="Python with pypdfium2 for real PDF reopen")
    args = parser.parse_args()
    report = run(args.output_dir, args.pdf_python)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report["failed"]))


if __name__ == "__main__":
    main()
