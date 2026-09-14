from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "math-modeling-skills-complete-20260903"
ORCH = PKG / "skills" / "math-modeling-orchestrator"


def test_orchestrator_defaults_to_lean_standard_profile():
    skill = (ORCH / "SKILL.md").read_text(encoding="utf-8")
    assert "`standard` — 默认" in skill
    assert "最短可靠闭环" in skill
    assert "默认不要求" in skill
    assert "不要因为用户只说“写完整论文”“生成 PDF”“正式排版”就自动升级到该模式" in skill
    assert "Artifact economy" in skill


def test_default_prompt_does_not_force_strict_audit_for_normal_papers():
    config = yaml.safe_load((ORCH / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    prompt = config["interface"]["default_prompt"]
    assert "默认采用 standard 精简执行" in prompt
    assert "不要默认等待用户批准主路线" in prompt
    assert "普通完整论文走 formal_delivery" in prompt
    assert "只有用户明确要求 provenance-bound competition-ready 审计时" in prompt
    assert "deliverable_mode 为 cumcm_latex_paper/submission_package" not in prompt


def test_strict_submission_contract_is_explicit_opt_in():
    contract = (ORCH / "references" / "full_submission_contract.md").read_text(encoding="utf-8")
    assert "本文件对应 `strict_submission_audit`" in contract
    assert "不要仅因为用户要求“完整论文”“最终 PDF”“正式排版”就自动触发本模式" in contract
    assert "--competition-ready" in contract
    assert "四路 fresh-subagent" in contract


def test_contest_operations_uses_one_compact_plan_by_default():
    planner = (PKG / "skills" / "mm-contest-operations-planner" / "SKILL.md").read_text(encoding="utf-8")
    assert "默认只生成一份 `CONTEST_PLAN.md`" in planner
    assert "只有当团队明确使用脚本、Agent 或 CI 消费机器文件时" in planner
