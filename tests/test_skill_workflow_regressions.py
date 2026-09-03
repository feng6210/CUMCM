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


def load_workflow_module():
    spec = importlib.util.spec_from_file_location("workflow_state_under_test", WORKFLOW)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


class FigurePlanningRegressionTests(unittest.TestCase):
    def test_table_only_question_does_not_fail_a_figure_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            decomposition = base / "QUESTION_DECOMPOSITION.json"
            decomposition.write_text(
                json.dumps({"expected_question_ids": ["Q1"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            sha = hashlib.sha256(decomposition.read_bytes()).hexdigest()
            plan = base / "FIGURE_PLAN.yaml"
            plan.write_text(
                f"""coverage_plan:
  expected_question_ids: [Q1]
  expected_question_ids_source:
    file: QUESTION_DECOMPOSITION.json
    sha256: {sha}
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


if __name__ == "__main__":
    unittest.main()
