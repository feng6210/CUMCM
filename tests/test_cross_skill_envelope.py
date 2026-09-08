from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import ValidationError
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "schemas" / "cross_skill_envelope.schema.json"


class CrossSkillEnvelopeTests(unittest.TestCase):
    def setUp(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls = validator_for(schema)
        cls.check_schema(schema)
        self.validator = cls(schema)

    def test_normalized_envelope_accepts_pending_benchmark(self):
        payload = {
            "schema_version": "1.0",
            "question_id": "Q1",
            "inputs": {"source": "problem"},
            "problem_semantics_ref": {"file": "PROBLEM_SEMANTICS.yaml", "question_id": "Q1"},
            "assumptions": [],
            "baseline": {"status": "READY", "value": 1.0},
            "model_and_solver": {"model": "baseline", "solver": "analytic"},
            "machine_readable_results": {"value": 1.0},
            "benchmark_challenge": "PENDING",
            "diagnostics": {},
            "unresolved_risks": [],
            "latex_equations": ["x=1"],
            "figure_intents": [],
        }
        self.validator.validate(payload)

    def test_missing_semantics_ref_fails(self):
        payload = {
            "schema_version": "1.0",
            "question_id": "Q1",
            "inputs": {},
            "assumptions": [],
            "baseline": "not_applicable",
            "model_and_solver": "analytic",
            "machine_readable_results": None,
            "benchmark_challenge": "PENDING",
            "diagnostics": {},
            "unresolved_risks": [],
            "latex_equations": [],
            "figure_intents": [],
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(payload)


if __name__ == "__main__":
    unittest.main()
