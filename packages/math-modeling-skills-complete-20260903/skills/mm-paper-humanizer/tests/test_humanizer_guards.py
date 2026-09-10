from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load_module("audit_cumcm_style", "scripts/audit_cumcm_style.py")
integrity = load_module("verify_rewrite_integrity", "scripts/verify_rewrite_integrity.py")


def write_tmp(text: str, suffix: str = ".tex") -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False)
    with handle:
        handle.write(text)
    return Path(handle.name)


class HumanizerGuardTests(unittest.TestCase):
    def test_audit_detects_responder_and_audit_language(self):
        path = write_tmp(
            r"""\section{结果分析}
这里需要说明的是，本结果为预算内候选。
值得注意的是，这并不意味着可以声称全局最优。
"""
        )
        report = audit.audit_file(path, strict=True)
        rules = {item["rule"] for item in report["findings"]}
        self.assertIn("responder_frame", rules)
        self.assertIn("audit_jargon", rules)
        self.assertIn("defensive_negation", rules)

    def test_audit_masks_math_environment(self):
        path = write_tmp(
            r"""\section{模型}
\begin{equation}
\text{预算内候选}=1
\end{equation}
模型输出功率为 10 W。
"""
        )
        report = audit.audit_file(path)
        self.assertFalse(any(item["rule"] == "audit_jargon" for item in report["findings"]))

    def test_integrity_preserves_math_numbers_and_refs(self):
        original = r"由式\eqref{eq:p}可得，$P=229.334$ W，见图\ref{fig:p}。"
        rewritten = r"根据式\eqref{eq:p}，$P=229.334$ W。结果见图\ref{fig:p}。"
        checks = [
            integrity.compare_counter("math", integrity.extract_envs(original), integrity.extract_envs(rewritten)),
            integrity.compare_counter("refs", integrity.extract_commands(original), integrity.extract_commands(rewritten)),
            integrity.compare_counter("numbers", integrity.NUMBER_RE.findall(original), integrity.NUMBER_RE.findall(rewritten)),
        ]
        self.assertTrue(all(item["passed"] for item in checks))

    def test_integrity_fails_when_number_changes(self):
        original = "平均功率为 229.334 W。"
        rewritten = "平均功率为 230.000 W。"
        check = integrity.compare_counter(
            "numbers", integrity.NUMBER_RE.findall(original), integrity.NUMBER_RE.findall(rewritten)
        )
        self.assertFalse(check["passed"])

    def test_claim_guard_blocks_global_upgrade(self):
        original = "在当前搜索域内得到最优可行方案。"
        rewritten = "得到全局最优方案。"
        check = integrity.claim_guard(original, rewritten)
        self.assertFalse(check["passed"])
        self.assertIn("全局最优", check["added_strong_claims"])

    def test_claim_guard_warns_when_all_scope_markers_disappear(self):
        original = "该结果为预算内候选，部分区域未收敛。"
        rewritten = "得到最优方案。"
        check = integrity.claim_guard(original, rewritten)
        self.assertTrue(check["scope_all_removed_warning"])


if __name__ == "__main__":
    unittest.main()
