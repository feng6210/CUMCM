from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_release_package.py"
PACKAGE = ROOT / "packages" / "math-modeling-skills-complete-20260903"


def load_builder():
    spec = importlib.util.spec_from_file_location("release_package_builder_under_test", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleasePackageBuilderTests(unittest.TestCase):
    def test_preview_zip_is_deterministic_and_contains_fresh_metadata(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_a = root / "a.zip"
            zip_b = root / "b.zip"
            report_a = builder.build(PACKAGE, zip_a)
            report_b = builder.build(PACKAGE, zip_b)
            self.assertEqual(report_a["zip_sha256"], report_b["zip_sha256"])
            self.assertEqual(report_a["skill_count"], 22)
            self.assertGreater(report_a["source_file_count"], 300)
            self.assertEqual(report_a["validation_report_mode"], "preview_marker")
            self.assertTrue(report_a["deterministic_without_wall_clock"])

            import zipfile

            with zipfile.ZipFile(zip_a, "r") as archive:
                prefix = PACKAGE.name
                manifest = json.loads(archive.read(f"{prefix}/PACKAGE_MANIFEST.json").decode("utf-8"))
                sums = archive.read(f"{prefix}/SHA256SUMS.txt").decode("utf-8")
                validation = json.loads(archive.read(f"{prefix}/VALIDATION_REPORT.json").decode("utf-8"))
                self.assertEqual(manifest["schema_version"], "3.0")
                self.assertEqual(manifest["skill_count"], 22)
                self.assertIn("VALIDATION_REPORT.json", manifest["generated_metadata"])
                self.assertIn("schemas/problem_semantics.schema.json", sums)
                self.assertIn("skills/math-modeling-orchestrator/scripts/validate_contract.py", sums)
                self.assertEqual(validation["status"], "PREVIEW_BUILD_NOT_FORMAL_RELEASE_VALIDATION")
                self.assertFalse(validation["semantic_claim_validation"])

    def test_formal_validation_report_must_be_json_object_with_status(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / "validation.json"
            invalid.write_text(json.dumps({"note": "missing status"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.build(PACKAGE, root / "formal.zip", validation_report=invalid)


if __name__ == "__main__":
    unittest.main()
