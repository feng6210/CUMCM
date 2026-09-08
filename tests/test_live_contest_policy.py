from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (
    ROOT
    / "packages"
    / "math-modeling-skills-complete-20260903"
    / "skills"
    / "math-modeling-orchestrator"
    / "scripts"
    / "workflow_state.py"
)


def load_workflow_module():
    spec = importlib.util.spec_from_file_location("workflow_state_live_policy_test", WORKFLOW)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALID_POLICY = """schema_version: \"1.0\"
competition_name: Demo Contest
stage: live_contest
ai_allowed: restricted
ai_scope: AI可用于题意分析、建模、代码与写作辅助，具体以规则限制为准
web_allowed: forbidden
external_papers_allowed: restricted
external_papers_scope: 仅可查阅规则允许的背景文献，不导入外部答案作为候选解
benchmark_answers_allowed: forbidden
team_collaboration_scope: registered team only
citation_requirement: follow official rules
source:
  kind: official_rules
  reference: demo official rulebook
unresolved: []
"""


class LiveContestPolicyTests(unittest.TestCase):
    def _advance_after_policy_to_approval(self, wf, state_path: Path):
        for target in (
            "DECOMPOSED",
            "SEMANTICS_REVIEW",
            "SEMANTICS_LOCKED",
            "BASELINE_SOLVING",
            "BASELINE_READY",
            "MODEL_PLANNED",
            "INNOVATION_PROPOSED",
            "AWAITING_MODEL_APPROVAL",
        ):
            wf.transition(state_path, target, None, None)

    def _decision(self, root: Path) -> Path:
        decision = root / "decision.json"
        decision.write_text(
            json.dumps(
                {
                    "approved": True,
                    "selected_routes": {"Q1": "route-A"},
                    "approved_claim_scope": ["claim-q1"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return decision

    def _write_valid_policy(self, root: Path) -> Path:
        policy = root / "COMPETITION_POLICY.yaml"
        policy.write_text(VALID_POLICY, encoding="utf-8")
        return policy

    def test_live_contest_blocks_substantive_ai_work_until_policy_is_validated(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "workflow_state.json"
            wf.initialize(state_path, "live-demo", "policy regression", "live_contest", "analysis")
            self.assertEqual(wf.read_json(state_path)["competition_policy_status"], "PENDING")

            # Registering the input/rules is allowed before policy validation.
            wf.transition(state_path, "INPUT_REGISTERED", None, None)
            with self.assertRaisesRegex(ValueError, "validated COMPETITION_POLICY"):
                wf.transition(state_path, "DECOMPOSED", None, None)

            policy = self._write_valid_policy(root)
            wf.record_competition_policy(state_path, policy)
            bound = wf.read_json(state_path)
            self.assertEqual(bound["competition_policy_status"], "VALIDATED")
            self.assertEqual(bound["competition_policy"]["benchmark_answers_allowed"], "forbidden")
            self.assertTrue(Path(bound["competition_policy"]["file"]).is_absolute())
            self.assertTrue(bound["competition_policy"]["ai_scope"])

            self._advance_after_policy_to_approval(wf, state_path)
            wf.approve(state_path, self._decision(root))
            wf.transition(state_path, "USER_APPROVED", None, None)
            wf.transition(state_path, "SOLVING", None, None)
            self.assertEqual(wf.read_json(state_path)["stage"], "SOLVING")

    def test_unknown_live_contest_permissions_are_rejected(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "workflow_state.json"
            wf.initialize(state_path, "live-demo", "policy regression", "live_contest", "analysis")
            policy = root / "COMPETITION_POLICY.yaml"
            policy.write_text(
                """schema_version: \"1.0\"
competition_name: Demo Contest
stage: live_contest
ai_allowed: unknown
web_allowed: forbidden
external_papers_allowed: restricted
external_papers_scope: 仅允许规则明确列出的背景文献，不使用公开答案
benchmark_answers_allowed: forbidden
team_collaboration_scope: registered team only
citation_requirement: follow official rules
source:
  kind: official_rules
  reference: incomplete rulebook
unresolved:
  - AI permission unresolved
""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                wf.record_competition_policy(state_path, policy)

    def test_policy_file_change_invalidates_sensitive_transition(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "workflow_state.json"
            wf.initialize(state_path, "live-demo", "policy hash regression", "live_contest", "analysis")
            wf.transition(state_path, "INPUT_REGISTERED", None, None)
            policy = self._write_valid_policy(root)
            wf.record_competition_policy(state_path, policy)

            policy.write_text(VALID_POLICY + "notes:\n  - changed after validation\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after validation"):
                wf.transition(state_path, "DECOMPOSED", None, None)

            wf.record_competition_policy(state_path, policy)
            wf.transition(state_path, "DECOMPOSED", None, None)
            self.assertEqual(wf.read_json(state_path)["stage"], "DECOMPOSED")

    def test_ai_forbidden_policy_stops_ai_workflow(self):
        wf = load_workflow_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "workflow_state.json"
            wf.initialize(state_path, "live-demo", "AI forbidden regression", "live_contest", "analysis")
            wf.transition(state_path, "INPUT_REGISTERED", None, None)
            policy = root / "COMPETITION_POLICY.yaml"
            policy.write_text(
                """schema_version: \"1.0\"
competition_name: Demo Contest
stage: live_contest
ai_allowed: forbidden
web_allowed: forbidden
external_papers_allowed: forbidden
benchmark_answers_allowed: forbidden
team_collaboration_scope: registered team only
citation_requirement: no AI use permitted
source:
  kind: official_rules
  reference: demo rulebook forbidding AI
unresolved: []
""",
                encoding="utf-8",
            )
            wf.record_competition_policy(state_path, policy)
            with self.assertRaisesRegex(ValueError, "forbids AI use"):
                wf.transition(state_path, "DECOMPOSED", None, None)


if __name__ == "__main__":
    unittest.main()
