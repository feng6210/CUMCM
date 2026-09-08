"""Synthetic adversarial tests for provenance checks, not real review receipts.

All fixtures are built in fresh temporary directories. No model data, installed
Skill, publication figure or actual author's review is read or rewritten.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import validate_figure_intent as validator
from test_validate_figure_intent import base_entry
from visual_review_contract import CHECKS, MECHANISM_CHECKS, intent_digest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class Fixture:
    def __init__(self, root):
        self.root = root
        assets = Path(__file__).resolve().parents[1] / "assets/tikz-schematics"
        for source, target in (("force-balance.pdf", "figure.pdf"), ("force-balance.png", "preview.png"), ("force-balance.tex", "figure.tex")):
            shutil.copyfile(assets / source, root / target)
        save(root / "model.json", {"synthetic_test_fixture": True, "expected_question_ids": ["Q1"]})
        save(root / "source-checks.json", {"synthetic_test_fixture": True})
        save(root / "reopen.json", {"synthetic_test_fixture": True})
        save(root / "catalog.json", {"cards": [{"card_id": "fixture-style", "preview_sha256": sha(root / "preview.png")}]})

        def bound(name):
            return {"file": name, "sha256": sha(root / name)}

        self.entry = base_entry(root / "model.json")
        self.entry.update(narrative_role="mechanism", claim_id="not_applicable", exact_values_location="not_applicable",
            chart_or_diagram_type="mechanism", backend_preference="tikz", actual_backend="tikz",
            editable_output="figure.tex", latex_output="figure.pdf", editable_sha256=sha(root / "figure.tex"),
            latex_sha256=sha(root / "figure.pdf"), backend_report="backend/report.json",
            source_data=[bound("model.json")], style_reference={"card_id": "fixture-style", "catalog": bound("catalog.json"), "preview": bound("preview.png")},
            renderer_source=bound("figure.tex"), caption_source=bound("model.json"), claim_source=bound("source-checks.json"),
            vector_editable_output=bound("figure.tex"), preview_output="preview.png", preview_sha256=sha(root / "preview.png"))
        self.entry["visual_grammar"]["style_profile"] = "cumcm-mechanism"
        self.receipt = {"synthetic_test_fixture": True, "status": "RUNTIME_VERIFIED", "actual_backend": "tikz",
            "generator_id": "fixture-author", "symbol_unification_by": "fixture-original-editor", "compiler_exit_code": 0,
            "sources": [{"file": "../model.json", "sha256": sha(root / "model.json")}],
            "outputs": [{"file": "../figure.tex", "sha256": sha(root / "figure.tex")}, {"file": "../figure.pdf", "sha256": sha(root / "figure.pdf")}],
            "style_profile": "cumcm-mechanism", "reopen_check": {"pdf": True, "editable": True}}
        self.backend = copy.deepcopy(self.receipt)
        self.backend.update(generator_id="fixture-author", post_generation_editor="fixture-later-editor",
                            original_backend_receipt={"file": "../history/receipt.json", "sha256": ""},
                            reopen_evidence={"file": "../reopen.json", "sha256": sha(root / "reopen.json")})
        self.review = {"synthetic_test_fixture": True, "decision": "PASSED", "generator_id": "fixture-author",
            "reviewers": [{"role": "visual", "reviewer_id": "fixture-reviewer", "origin": "same-family-cross-review",
                           "zero_context": False, "independent_of_figure_generation": True}],
            "bindings": {"output": self.entry["latex_sha256"], "editable": self.entry["editable_sha256"]},
            "checks": {name: {"status": "PASSED", "note": "Synthetic contract fixture, no actual visual approval."} for name in CHECKS | MECHANISM_CHECKS},
            "source_checks": bound("source-checks.json"), "opened_image_bindings": [bound("preview.png")], "blocking_findings": []}

    def sync(self):
        save(self.root / "history/receipt.json", self.receipt)
        if "original_backend_receipt" in self.backend:
            self.backend["original_backend_receipt"]["sha256"] = sha(self.root / "history/receipt.json")
        save(self.root / "backend/report.json", self.backend)
        self.entry["backend_report_sha256"] = sha(self.root / "backend/report.json")
        self.review["bindings"]["intent"] = intent_digest(self.entry)
        save(self.root / "review.json", self.review)
        self.entry["visual_review"] = {"file": "review.json", "sha256": sha(self.root / "review.json")}

    def errors(self):
        return validator.validate_entry(self.entry, 0, self.root, True, True, True)[0]


class ProvenanceTests(unittest.TestCase):
    def run_case(self, mutate=None, needle=None, after=None):
        with tempfile.TemporaryDirectory(prefix="figure-provenance-") as temporary:
            fixture = Fixture(Path(temporary))
            if mutate:
                mutate(fixture)
            fixture.sync()
            if after:
                after(fixture)
            errors = fixture.errors()
            if needle is None:
                self.assertEqual(errors, [])
            else:
                self.assertTrue(any(needle in error for error in errors), errors)

    def test_valid_relative_historical_receipt(self):
        self.run_case()

    def test_valid_direct_receipt(self):
        self.run_case(lambda f: f.backend.pop("original_backend_receipt"))

    def test_generator_and_editors_cannot_review(self):
        for identifier in ("fixture-author", " fixture-author ", "fixture-later-editor", "fixture-original-editor"):
            with self.subTest(identifier=identifier):
                self.run_case(lambda f: f.review["reviewers"][0].update(reviewer_id=identifier), "independent visual reviewer missing")

    def test_hidden_original_author_cannot_review(self):
        def mutate(f):
            f.backend["generator_id"] = f.review["generator_id"] = "fixture-renamed-recorder"
            f.review["reviewers"][0]["reviewer_id"] = "fixture-author"
        self.run_case(mutate, "independent visual reviewer missing")

    def test_hidden_original_editor_cannot_review(self):
        def mutate(f):
            f.backend.pop("symbol_unification_by")
            f.review["reviewers"][0]["reviewer_id"] = "fixture-original-editor"
        self.run_case(mutate, "independent visual reviewer missing")

    def test_generator_identity_conflict(self):
        self.run_case(lambda f: f.review.update(generator_id="fixture-lie"), "generator_id differs")

    def test_cross_review_disclosure_required(self):
        for key, value in (("zero_context", True), ("independent_of_figure_generation", False)):
            with self.subTest(key=key):
                self.run_case(lambda f: f.review["reviewers"][0].update({key: value}), "independent visual reviewer missing")

    def test_fresh_and_external_review_origins_remain_supported(self):
        for origin in ("same-family-fresh", "external"):
            with self.subTest(origin=origin):
                self.run_case(lambda f: f.review["reviewers"][0].update(origin=origin))

    def test_compile_success_requires_integer_zero(self):
        for value in (1, False, "0", None):
            with self.subTest(value=value):
                self.run_case(lambda f: f.receipt.update(compiler_exit_code=value), "successful TikZ compiler receipt required")

    def test_failed_receipt_status_cannot_hide_behind_zero(self):
        self.run_case(lambda f: f.receipt.update(status="FAILED"), "successful TikZ compiler receipt required")

    def test_missing_original_receipt(self):
        self.run_case(lambda f: f.backend["original_backend_receipt"].update(file="missing.json"), "missing/stale")

    def test_source_and_output_receipt_hashes(self):
        for category, index in (("sources", 0), ("outputs", 0), ("outputs", 1)):
            with self.subTest(category=category, index=index):
                self.run_case(lambda f: f.receipt[category][index].update(sha256="0" * 64), "receipt")

    def test_missing_receipt_sources(self):
        self.run_case(lambda f: f.receipt.update(sources=[]), "receipt sources required")

    def test_changed_declared_backend(self):
        self.run_case(lambda f: f.entry.update(actual_backend="svg"), "actual_backend")
        self.run_case(lambda f: f.backend.update(actual_backend="imagegen"), "actual_backend")

    def test_backend_aliases_are_normalized(self):
        self.assertEqual({validator.backend_identity(x) for x in ("python", "Python/Matplotlib", " matplotlib ")}, {"matplotlib"})
        self.assertNotEqual(validator.backend_identity("svg"), validator.backend_identity("tikz"))

    def test_failed_output_reopen(self):
        self.run_case(lambda f: f.backend["reopen_check"].update(pdf=False), "must be reopened")

    def test_optional_provenance_is_not_unchecked_prose(self):
        for key in ("renderer_source", "caption_source", "claim_source", "vector_editable_output"):
            with self.subTest(key=key):
                self.run_case(lambda f: f.entry[key].update(sha256="0" * 64), key)

    def test_preview_and_review_evidence_hashes(self):
        self.run_case(lambda f: f.entry.update(preview_sha256="0" * 64), "preview_output")
        self.run_case(lambda f: f.review["source_checks"].update(sha256="0" * 64), "source_checks")
        self.run_case(lambda f: f.review["opened_image_bindings"][0].update(sha256="0" * 64), "opened_image_binding")
        self.run_case(lambda f: f.backend["reopen_evidence"].update(sha256="0" * 64), "reopen_evidence")

    def test_stale_intent_is_rejected_without_resigning(self):
        self.run_case(needle="stale intent", after=lambda f: f.entry.update(caption_zh="未经复审的图注修改"))

    def test_actual_output_change_is_rejected(self):
        self.run_case(needle="mismatch", after=lambda f: (f.root / "figure.tex").write_text("changed source", encoding="utf-8"))

    def test_style_card_requires_preview_hash_field(self):
        def mutate(f):
            save(f.root / "catalog.json", {"cards": [{"card_id": "fixture-style", "preview": {"sha256": sha(f.root / "preview.png")}}]})
            f.entry["style_reference"]["catalog"]["sha256"] = sha(f.root / "catalog.json")
        self.run_case(mutate, "preview does not belong")

    def test_open_findings_are_not_passed(self):
        self.run_case(lambda f: f.review.update(blocking_findings=["Synthetic unresolved issue"]), "blocking findings remain")


if __name__ == "__main__":
    unittest.main(verbosity=2)
