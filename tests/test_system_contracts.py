from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import ValidationError
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "math-modeling-skills-complete-20260903"
SCHEMAS = PKG / "schemas"
ORCH = PKG / "skills" / "math-modeling-orchestrator"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validator(name: str):
    schema = load_json(SCHEMAS / name)
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


class ContractSchemaTests(unittest.TestCase):
    def test_problem_semantics_valid_and_missing_selection_fails(self):
        v = validator("problem_semantics.schema.json")
        payload = {
            "schema_version": "1.0",
            "question_id": "Q5",
            "raw_objective_phrases": ["总有效遮蔽时间"],
            "candidate_interpretations": [
                {
                    "id": "S1",
                    "mathematical_objective": "maximize union measure",
                    "resource_accounting": "shared physical resource",
                    "time_accounting": "union",
                    "assumptions_added": [],
                    "downstream_effect": "changes objective aggregation",
                }
            ],
            "selected_interpretation": "S1",
            "selection_reason": "supported by the problem semantics",
            "semantic_risk": "medium",
            "unresolved_ambiguities": [],
        }
        v.validate(payload)
        invalid = dict(payload)
        invalid.pop("selected_interpretation")
        with self.assertRaises(ValidationError):
            v.validate(invalid)

    def test_challenged_benchmark_requires_same_evaluator_and_search_reopen(self):
        v = validator("benchmark_challenge.schema.json")
        payload = {
            "schema_version": "1.0",
            "benchmark_id": "external-q3",
            "source_scope": "user-provided feasible strategy",
            "parameter_mapping": {},
            "same_evaluator": True,
            "feasible_under_current_model": True,
            "objective_value": 6.9,
            "incumbent_value": 6.4,
            "tolerance": 0.001,
            "objective_direction": "max",
            "outcome": "CHALLENGED",
            "reason": "external candidate is better under the same evaluator",
            "reopen_search_required": True,
        }
        v.validate(payload)
        invalid = dict(payload)
        invalid["same_evaluator"] = False
        with self.assertRaises(ValidationError):
            v.validate(invalid)

    def test_figure_plan_allows_table_only_question(self):
        v = validator("figure_plan.schema.json")
        payload = {
            "schema_version": "1.0",
            "coverage_plan": {
                "expected_question_ids": ["Q1"],
                "questions": [
                    {
                        "question_id": "Q1",
                        "tasks": {
                            "main_result": {
                                "representation": "table",
                                "reason": "只有一组精确数值，三线表比图形更清楚",
                            },
                            "validation": {
                                "representation": "appendix",
                                "reason": "数值复核需保留但不会改变正文主要判断",
                            },
                        },
                    }
                ],
            },
            "figures": [],
        }
        v.validate(payload)

    def test_live_contest_policy_rejects_unknown_critical_permissions(self):
        v = validator("competition_policy.schema.json")
        valid = {
            "schema_version": "1.0",
            "competition_name": "demo",
            "stage": "live_contest",
            "ai_allowed": "restricted",
            "web_allowed": "forbidden",
            "external_papers_allowed": "restricted",
            "benchmark_answers_allowed": "forbidden",
            "team_collaboration_scope": "registered team only",
            "citation_requirement": "follow official rules",
            "source": {"kind": "official_rules", "reference": "official rulebook"},
        }
        v.validate(valid)
        for field in (
            "ai_allowed",
            "web_allowed",
            "external_papers_allowed",
            "benchmark_answers_allowed",
        ):
            with self.subTest(field=field):
                invalid = dict(valid)
                invalid[field] = "unknown"
                with self.assertRaises(ValidationError):
                    v.validate(invalid)

    def test_all_system_benchmark_cases_validate(self):
        v = validator("system_benchmark.schema.json")
        cases = sorted((ROOT / "benchmarks").glob("*/benchmark.yaml"))
        self.assertGreaterEqual(len(cases), 4)
        for path in cases:
            with self.subTest(path=path.name):
                case = yaml.safe_load(path.read_text(encoding="utf-8"))
                v.validate(case)


class IntegrationDriftTests(unittest.TestCase):
    def test_routing_guide_tracks_current_state_machine(self):
        text = (ORCH / "references" / "routing_guide.md").read_text(encoding="utf-8")
        for token in (
            "SEMANTICS_REVIEW",
            "SEMANTICS_LOCKED",
            "BASELINE_SOLVING",
            "BASELINE_READY",
            "BENCHMARK_CHALLENGE",
            "RESULT_TO_CLAIM",
        ):
            self.assertIn(token, text)
        self.assertNotIn("DECOMPOSED → DATA_AUDITED → MODEL_PLANNED", text)

    def test_contest_handoff_contains_normalized_contract_fields(self):
        text = (PKG / "skills" / "mm-contest-operations-planner" / "SKILL.md").read_text(encoding="utf-8")
        for token in ("COMPETITION_POLICY.yaml", "problem_semantics_ref", "baseline", "benchmark_challenge", "figure_intents"):
            self.assertIn(token, text)

    def test_orchestrator_wires_policy_and_contract_validation(self):
        text = (ORCH / "SKILL.md").read_text(encoding="utf-8")
        for token in ("COMPETITION_POLICY.yaml", "validate_contract.py", "schemas/", "benchmarks/"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
