from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills"
WORKFLOW = PKG / "math-modeling-orchestrator" / "scripts" / "workflow_state.py"
FIGURE_VALIDATOR = PKG / "mm-visualization-delivery" / "scripts" / "validate_figure_intent.py"
CROSS_SKILL_CONTRACT = PKG / "math-modeling-orchestrator" / "references" / "cross_skill_output_contract.md"


def load_workflow_module():
    spec = importlib.util.spec_from_file_location("workflow_state_under_test", WORKFLOW)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WorkflowStateRegressionTests(unittest.TestCase):
    def test_semantics_and_baseline_precede_main_solving(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "workflow_state.json"
            wf.initialize(state_path, "demo", "regression", "training", "analysis")
            state = wf.read_json(state_path)
            self.assertEqual(state["reporting_profile"], "competition_compact")

            wf.transition(state_path, "INPUT_REGISTERED", "mm-problem-decomposer", None)
            wf.transition(state_path, "DECOMPOSED", "mm-problem-decomposer", None)
            wf.transition(state_path, "SEMANTICS_REVIEW", "mm-variable-assumption-builder", None)
            wf.transition(state_path, "SEMANTICS_LOCKED", "mm-data-eda-cleaning", None)
            wf.transition(state_path, "BASELINE_SOLVING", "mm-optimization-models", None)
            wf.transition(state_path, "BASELINE_READY", "mm-model-selector", None)
            wf.transition(state_path, "MODEL_PLANNED", "mm-model-innovation-designer", None)
            wf.transition(state_path, "INNOVATION_PROPOSED", "mm-model-innovation-designer", None)
            wf.transition(state_path, "AWAITING_MODEL_APPROVAL", None, None)

            with self.assertRaises(ValueError):
                wf.transition(state_path, "SOLVING", "mm-optimization-models", None)

            decision = Path(tmp) / "decision.json"
            decision.write_text(
                json.dumps(
                    {
                        "approved": True,
                        "selected_routes": {"Q1": "route-B"},
                        "approved_claim_scope": ["claim-q1"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wf.approve(state_path, decision)
            wf.transition(state_path, "USER_APPROVED", "mm-optimization-models", None)
            wf.transition(state_path, "SOLVING", "mm-optimization-models", None)
            self.assertEqual(wf.read_json(state_path)["stage"], "SOLVING")

    def test_minimum_baseline_gate_cannot_be_bypassed(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "workflow_state.json"
            wf.initialize(state_path, "demo", "baseline-gate", "training", "analysis")
            wf.transition(state_path, "INPUT_REGISTERED", None, None)
            wf.transition(state_path, "DECOMPOSED", None, None)
            wf.transition(state_path, "SEMANTICS_REVIEW", None, None)
            wf.transition(state_path, "SEMANTICS_LOCKED", None, None)

            with self.assertRaises(ValueError):
                wf.transition(state_path, "MODEL_PLANNED", "mm-model-selector", None)

            wf.transition(state_path, "DATA_AUDITED", None, None)
            with self.assertRaises(ValueError):
                wf.transition(state_path, "MODEL_PLANNED", "mm-model-selector", None)

            wf.transition(state_path, "BASELINE_SOLVING", None, None)
            wf.transition(state_path, "BASELINE_READY", None, None)
            wf.transition(state_path, "MODEL_PLANNED", "mm-model-selector", None)
            self.assertEqual(wf.read_json(state_path)["stage"], "MODEL_PLANNED")

    def test_semantic_amendment_invalidates_downstream_evidence(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "workflow_state.json"
            wf.initialize(state_path, "demo", "regression", "research", "analysis")
            state = wf.read_json(state_path)
            state["stage"] = "PARTIAL"
            state["problem_semantics"] = {"sha256": "demo"}
            state["baseline_result"] = {"value": 1.0}
            state["benchmark_challenge"] = {"status": "PASS"}
            state["evidence_status"] = "PARTIAL"
            state["result_to_claim_status"] = "PARTIAL"
            wf.write_json(state_path, state)

            wf.amend(
                state_path,
                "objective aggregation changed",
                ["results", "paper", "figures"],
                semantic=True,
            )
            amended = wf.read_json(state_path)
            self.assertEqual(amended["stage"], "SEMANTICS_REVIEW")
            self.assertIsNone(amended["problem_semantics"])
            self.assertIsNone(amended["baseline_result"])
            self.assertIsNone(amended["benchmark_challenge"])
            self.assertEqual(amended["evidence_status"], "NOT_EVALUATED")


class CrossSkillContractRegressionTests(unittest.TestCase):
    def test_contract_keeps_legacy_figure_field_compatible(self):
        text = CROSS_SKILL_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("recommended_figures", text)
        self.assertIn("规范化 envelope", text)
        self.assertIn("不得要求每个专业 Skill 重复生成", text)


class FigurePlanningRegressionTests(unittest.TestCase):
    def test_table_only_question_does_not_fail_a_figure_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            decomposition = base / "QUESTION_DECOMPOSITION.json"
            decomposition.write_text(
                json.dumps({"expected_question_ids": ["Q1"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            decomposition_sha = sha256(decomposition)
            plan = base / "FIGURE_PLAN.yaml"
            plan.write_text(
                f"""coverage_plan:
  expected_question_ids: [Q1]
  expected_question_ids_source:
    file: QUESTION_DECOMPOSITION.json
    sha256: {decomposition_sha}
    field: expected_question_ids
  questions:
    - question_id: Q1
      core_claim_ids: [claim-q1]
      tasks:
        orientation:
          representation: not_applicable
          figure_ids: []
          reason: 本问没有独立场景关系需要额外导航图
        mechanism:
          representation: not_applicable
          figure_ids: []
          reason: 本问只有直接闭式换算没有复杂机理障碍
        main_result:
          representation: table
          figure_ids: []
          reason: 只有一组精确数值用三线表比图形更清楚
        comparison:
          representation: not_applicable
          figure_ids: []
          reason: 本问没有多个可比模型或方案需要视觉比较
        validation:
          representation: appendix
          figure_ids: []
          reason: 数值复核需要保留但不值得占用正文图位
        robustness:
          representation: not_applicable
          figure_ids: []
          reason: 题面参数固定且本问没有额外不确定性分析
figures: []
""",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(FIGURE_VALIDATOR),
                    str(plan),
                    "--base-dir",
                    str(base),
                    "--allow-missing-sources",
                    "--require-coverage",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                self.fail(completed.stdout + "\n" + completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "PASSED")
            self.assertFalse(report["fixed_figure_quota"])
            self.assertEqual(report["figure_count"], 0)

    def test_final_renderer_contract_remains_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data = base / "data.csv"
            data.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")
            spec = base / "figure.json"
            spec.write_text(json.dumps({"chart_type": "line"}), encoding="utf-8")
            pdf = base / "figure.pdf"
            pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 320 + b"\n%%EOF\n")

            data_sha = sha256(data)
            spec_sha = sha256(spec)
            pdf_sha = sha256(pdf)
            report_path = base / "backend_report.json"

            def write_report(variables: list[str]) -> str:
                payload = {
                    "status": "PASSED",
                    "outputs": [
                        {"path": spec.name, "sha256": spec_sha},
                        {"path": pdf.name, "sha256": pdf_sha},
                    ],
                    "sources": [{"path": data.name, "sha256": data_sha}],
                    "spec": {"path": spec.name, "sha256": spec_sha},
                    "render_contract": {
                        "chart_type": "line",
                        "variables": variables,
                        "transformations": ["identity"],
                    },
                    "style": {
                        "style_profile": "cumcm-clean",
                        "effective_palette": ["#2F5D7C"],
                        "decorative_effects": ["none"],
                        "final_width_mm": 90.0,
                        "line_width_pt": 1.0,
                        "base_font_pt": 9.0,
                        "effective_min_font_pt": 9.0,
                        "font_family": "Microsoft YaHei",
                        "legend_strategy": "none",
                    },
                    "reopen_check": {"editable": True, "pdf": True},
                }
                report_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return sha256(report_path)

            report_sha = write_report(["x", "y"])
            intent = base / "FIGURE_INTENT.json"

            def write_intent(current_report_sha: str) -> None:
                payload = {
                    "figures": [
                        {
                            "figure_id": "q1-line",
                            "question_id": "Q1",
                            "purpose": "展示变量随横轴的变化趋势",
                            "claim_id": "claim-q1",
                            "source_data": {"file": data.name, "sha256": data_sha},
                            "variables": ["x", "y"],
                            "units": {"x": "s", "y": "m"},
                            "transformations": ["identity"],
                            "chart_or_diagram_type": "line",
                            "backend_preference": "matplotlib",
                            "editable_output": spec.name,
                            "editable_sha256": spec_sha,
                            "latex_output": pdf.name,
                            "latex_sha256": pdf_sha,
                            "backend_report": report_path.name,
                            "backend_report_sha256": current_report_sha,
                            "renderer_spec": {"file": spec.name, "sha256": spec_sha},
                            "caption_zh": "变量变化趋势",
                            "narrative_role": "evidence",
                            "reader_takeaway": "读者能够直接判断变量随横轴增加的变化方向",
                            "exact_values_location": "machine_readable_table",
                            "visual_grammar_group": "paper-data",
                            "visual_grammar": {
                                "font_family": "Microsoft YaHei",
                                "base_font_pt": 9.0,
                                "palette": ["#2F5D7C"],
                                "line_width_pt": 1.0,
                                "style_profile": "cumcm-clean",
                                "final_width_mm": 90.0,
                                "legend_strategy": "none",
                                "precision_policy": "exact values in table",
                                "decorative_effects": ["none"],
                            },
                            "placement": "body",
                        }
                    ]
                }
                intent.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            write_intent(report_sha)
            good = subprocess.run(
                [
                    sys.executable,
                    str(FIGURE_VALIDATOR),
                    str(intent),
                    "--base-dir",
                    str(base),
                    "--require-sources",
                    "--require-outputs",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if good.returncode != 0:
                self.fail(good.stdout + "\n" + good.stderr)

            bad_report_sha = write_report(["wrong"])
            write_intent(bad_report_sha)
            bad = subprocess.run(
                [
                    sys.executable,
                    str(FIGURE_VALIDATOR),
                    str(intent),
                    "--base-dir",
                    str(base),
                    "--require-sources",
                    "--require-outputs",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("render_contract.variables", bad.stdout)


if __name__ == "__main__":
    unittest.main()
