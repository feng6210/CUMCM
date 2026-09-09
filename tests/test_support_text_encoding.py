from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "packages" / "math-modeling-skills-complete-20260903" / "skills" / "mm-paper-compile" / "scripts" / "final_delivery_check.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("support_encoding_checker", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_checker()


class SupportTextEncodingTests(unittest.TestCase):
    def make_zip(self, name: str, payload: bytes) -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory(prefix="support-encoding-")
        archive = Path(tmp.name) / "support.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr(name, payload)
        return tmp, archive

    def test_utf16_bom_power_shell_tokens_are_not_hidden(self):
        text = "# 姓名 张三 学号 20260001\n# TODO 待填写\nWrite-Output 'ok'\n"
        tmp, archive = self.make_zip("code/main.ps1", text.encode("utf-16"))
        self.addCleanup(tmp.cleanup)
        result = checker.inspect_support_zip(archive)
        self.assertEqual(result["uninspected_text_members"], [])
        self.assertIn("code/main.ps1", result["source_program_members"])
        self.assertTrue(any(row["token"] == "姓名" for row in result["identity_hits"]))
        self.assertTrue(any("TODO" in row["pattern"] or "待填写" in row["pattern"] for row in result["placeholder_hits"]))

    def test_utf8_bom_source_is_supported(self):
        text = "Write-Output 'ok'\n"
        tmp, archive = self.make_zip("code/main.ps1", b"\xef\xbb\xbf" + text.encode("utf-8"))
        self.addCleanup(tmp.cleanup)
        result = checker.inspect_support_zip(archive)
        self.assertEqual(result["uninspected_text_members"], [])
        self.assertIn("code/main.ps1", result["source_program_members"])
        self.assertEqual(result["identity_hits"], [])
        self.assertEqual(result["placeholder_hits"], [])

    def test_utf16_without_bom_fails_closed(self):
        payload = "Write-Output 'ok'\n".encode("utf-16-le")
        tmp, archive = self.make_zip("code/main.ps1", payload)
        self.addCleanup(tmp.cleanup)
        result = checker.inspect_support_zip(archive)
        self.assertNotEqual(result["uninspected_text_members"], [])
        self.assertNotIn("code/main.ps1", result["source_program_members"])

    def test_invalid_utf8_fails_closed(self):
        tmp, archive = self.make_zip("code/main.ps1", b"\x80\x81\x82Write-Output 'ok'")
        self.addCleanup(tmp.cleanup)
        result = checker.inspect_support_zip(archive)
        self.assertNotEqual(result["uninspected_text_members"], [])
        self.assertNotIn("code/main.ps1", result["source_program_members"])


if __name__ == "__main__":
    unittest.main()
