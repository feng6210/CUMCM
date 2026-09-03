"""Fail-closed, artifact-aware workflow state for the math-modeling Skill suite."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("NEW", "INPUT_REGISTERED", "DECOMPOSED", "DATA_AUDITED", "MODEL_PLANNED", "INNOVATION_PROPOSED", "AWAITING_MODEL_APPROVAL", "USER_APPROVED", "SOLVING", "SOLVED", "INTEGRITY_AUDIT", "VALIDATING", "PASS", "PARTIAL", "FAIL", "RESULT_TO_CLAIM", "WRITING", "FIGURES", "DELIVERING", "REVIEWING", "COMPLETE", "BLOCKED_INPUT", "BLOCKED_CAPABILITY")
EVIDENCE = ("NOT_EVALUATED", "PASS", "PARTIAL", "FAIL")
RESULT_TO_CLAIM = ("NOT_EVALUATED", "YES", "PARTIAL", "NO", "BLOCKED")
TASK_MODES = ("training", "live_contest", "coursework", "research", "business", "engineering")
DELIVERABLE_MODES = ("analysis", "code", "figures", "paper_outline", "cumcm_latex_paper", "submission_package")
ALLOWED = {
    "NEW": {"INPUT_REGISTERED", "BLOCKED_INPUT"}, "INPUT_REGISTERED": {"DECOMPOSED", "BLOCKED_INPUT"},
    "DECOMPOSED": {"DATA_AUDITED", "MODEL_PLANNED", "BLOCKED_INPUT"}, "DATA_AUDITED": {"MODEL_PLANNED", "BLOCKED_INPUT", "BLOCKED_CAPABILITY"},
    "MODEL_PLANNED": {"INNOVATION_PROPOSED", "BLOCKED_CAPABILITY"}, "INNOVATION_PROPOSED": {"AWAITING_MODEL_APPROVAL"},
    "AWAITING_MODEL_APPROVAL": {"USER_APPROVED", "INNOVATION_PROPOSED", "BLOCKED_INPUT"}, "USER_APPROVED": {"SOLVING", "INNOVATION_PROPOSED"},
    "SOLVING": {"SOLVED", "BLOCKED_INPUT", "BLOCKED_CAPABILITY"}, "SOLVED": {"INTEGRITY_AUDIT", "VALIDATING"},
    "INTEGRITY_AUDIT": {"VALIDATING", "FAIL", "BLOCKED_INPUT"}, "VALIDATING": {"PASS", "PARTIAL", "FAIL"},
    "PASS": {"RESULT_TO_CLAIM", "DELIVERING"}, "PARTIAL": {"RESULT_TO_CLAIM", "DELIVERING", "SOLVING"},
    "FAIL": {"SOLVING", "BLOCKED_CAPABILITY"}, "RESULT_TO_CLAIM": {"WRITING", "SOLVING", "BLOCKED_INPUT"},
    "WRITING": {"FIGURES", "REVIEWING", "SOLVING"}, "FIGURES": {"DELIVERING", "REVIEWING", "SOLVING"},
    "DELIVERING": {"REVIEWING"}, "REVIEWING": {"COMPLETE", "SOLVING", "WRITING"},
    "BLOCKED_INPUT": {"INPUT_REGISTERED", "DECOMPOSED", "DATA_AUDITED", "INNOVATION_PROPOSED"},
    "BLOCKED_CAPABILITY": {"MODEL_PLANNED", "SOLVING"}, "COMPLETE": set(),
}

def now() -> str: return datetime.now(timezone.utc).isoformat()

def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"JSON object required: {path}")
    return value

def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try: os.unlink(temp_name)
        except FileNotFoundError: pass
        raise

def validate_state(state: dict) -> None:
    required = {"schema_version", "task_id", "scope", "stage", "task_mode", "deliverable_mode", "output_language", "paper_profile", "paper_format", "latex_engine", "problem_parts", "inputs", "assumptions", "claims", "artifacts", "evidence_status", "unresolved", "next_skill", "history", "result_to_claim_status", "stale_artifacts"}
    missing = required - state.keys()
    if missing: raise ValueError("missing state fields: " + ", ".join(sorted(missing)))
    if state["stage"] not in STAGES: raise ValueError(f"unknown stage: {state['stage']}")
    if state["evidence_status"] not in EVIDENCE: raise ValueError(f"unknown evidence status: {state['evidence_status']}")
    if state["result_to_claim_status"] not in RESULT_TO_CLAIM: raise ValueError("unknown result_to_claim_status")
    if state["task_mode"] not in TASK_MODES: raise ValueError("unknown task_mode")
    if state["deliverable_mode"] not in DELIVERABLE_MODES: raise ValueError("unknown deliverable_mode")

def initialize(path: Path, task_id: str, scope: str, task_mode: str, deliverable_mode: str) -> dict:
    if path.exists(): raise FileExistsError(f"state already exists: {path}")
    state = {"schema_version": "2.0", "task_id": task_id, "scope": scope, "stage": "NEW", "task_mode": task_mode, "deliverable_mode": deliverable_mode, "output_language": "zh-CN", "paper_profile": "cumcm-2026-electronic", "paper_format": "latex", "latex_engine": "xelatex", "problem_parts": [], "inputs": [], "assumptions": [], "claims": [], "artifacts": [], "experiment_plan": None, "run_manifest": None, "paper_claim_audit_status": "NOT_EVALUATED", "citation_audit_status": "NOT_EVALUATED", "compile_status": "NOT_EVALUATED", "result_to_claim_status": "NOT_EVALUATED", "evidence_status": "NOT_EVALUATED", "unresolved": [], "stale_artifacts": [], "next_skill": "mm-problem-decomposer", "model_approval": None, "history": [{"at": now(), "event": "initialized", "stage": "NEW"}]}
    write_json(path, state); return state

def transition(path: Path, target: str, next_skill: str | None, evidence_status: str | None) -> dict:
    state = read_json(path); validate_state(state); current = state["stage"]
    if target not in ALLOWED[current]: raise ValueError(f"transition not allowed: {current} -> {target}")
    approval = state.get("model_approval") or {}
    if target == "USER_APPROVED" and approval.get("approved") is not True: raise ValueError("model approval record required before USER_APPROVED")
    if target == "SOLVING" and current not in {"USER_APPROVED", "PARTIAL", "FAIL", "RESULT_TO_CLAIM", "WRITING", "FIGURES", "REVIEWING"}: raise ValueError("initial SOLVING requires USER_APPROVED")
    new_evidence = evidence_status or state["evidence_status"]
    if target == "DELIVERING" and new_evidence not in {"PASS", "PARTIAL"}: raise ValueError("DELIVERING requires PASS or PARTIAL evidence")
    state["stage"], state["next_skill"], state["evidence_status"] = target, next_skill, new_evidence
    state["history"].append({"at": now(), "event": "transition", "from": current, "to": target})
    write_json(path, state); return state

def approve(path: Path, decision_path: Path) -> dict:
    state = read_json(path); validate_state(state)
    if state["stage"] != "AWAITING_MODEL_APPROVAL": raise ValueError("approval is accepted only at AWAITING_MODEL_APPROVAL")
    decision = read_json(decision_path)
    routes, claims = decision.get("selected_routes"), decision.get("approved_claim_scope")
    if decision.get("approved") is not True: raise ValueError("decision.approved must be true")
    if not isinstance(routes, dict) or not routes or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in routes.items()): raise ValueError("selected_routes must be a non-empty object of non-empty strings")
    if not isinstance(claims, list) or not claims or not all(isinstance(item, str) and item for item in claims): raise ValueError("approved_claim_scope must be a non-empty string array")
    decision = dict(decision); decision.setdefault("decided_at", now()); state["model_approval"] = decision
    state["history"].append({"at": now(), "event": "model_approval_recorded", "routes": routes}); write_json(path, state); return state

def amend(path: Path, reason: str, affected: list[str]) -> dict:
    state = read_json(path); validate_state(state)
    if not reason.strip() or not affected: raise ValueError("amendment requires a reason and affected artifacts")
    state["stage"], state["model_approval"] = "INNOVATION_PROPOSED", None
    state["stale_artifacts"] = sorted(set(state["stale_artifacts"]) | set(affected))
    state["history"].append({"at": now(), "event": "plan_amended", "reason": reason, "affected": affected}); write_json(path, state); return state

def mark_stale(path: Path, artifacts: list[str], reason: str) -> dict:
    state = read_json(path); validate_state(state)
    if not artifacts: raise ValueError("at least one artifact is required")
    state["stale_artifacts"] = sorted(set(state["stale_artifacts"]) | set(artifacts))
    state["paper_claim_audit_status"], state["citation_audit_status"], state["compile_status"] = "STALE", "STALE", "STALE"
    state["history"].append({"at": now(), "event": "artifacts_marked_stale", "reason": reason, "artifacts": artifacts}); write_json(path, state); return state

def emit(value: dict) -> None: print(json.dumps(value, ensure_ascii=False, indent=2))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and enforce a fail-closed mathematical-modeling workflow state."); sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a workflow state without overwriting an existing file."); init.add_argument("--state", type=Path, required=True); init.add_argument("--task-id", required=True); init.add_argument("--scope", default=""); init.add_argument("--task-mode", choices=TASK_MODES, default="training"); init.add_argument("--deliverable-mode", choices=DELIVERABLE_MODES, default="analysis")
    show = sub.add_parser("show", help="Validate and print a workflow state."); show.add_argument("--state", type=Path, required=True)
    move = sub.add_parser("transition", help="Apply an allowed stage transition."); move.add_argument("--state", type=Path, required=True); move.add_argument("--to", choices=STAGES, required=True); move.add_argument("--next-skill"); move.add_argument("--evidence-status", choices=EVIDENCE)
    approval = sub.add_parser("approve-model", help="Record a valid model decision while awaiting approval."); approval.add_argument("--state", type=Path, required=True); approval.add_argument("--decision-file", type=Path, required=True)
    amendment = sub.add_parser("amend-plan", help="Invalidate approval when a material modeling plan changes."); amendment.add_argument("--state", type=Path, required=True); amendment.add_argument("--reason", required=True); amendment.add_argument("--affected", nargs="+", required=True)
    stale = sub.add_parser("mark-stale", help="Mark result-derived artifacts stale after source changes."); stale.add_argument("--state", type=Path, required=True); stale.add_argument("--reason", required=True); stale.add_argument("--artifacts", nargs="+", required=True)
    return parser

def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init": emit(initialize(args.state, args.task_id, args.scope, args.task_mode, args.deliverable_mode))
        elif args.command == "show": state = read_json(args.state); validate_state(state); emit(state)
        elif args.command == "transition": emit(transition(args.state, args.to, args.next_skill, args.evidence_status))
        elif args.command == "approve-model": emit(approve(args.state, args.decision_file))
        elif args.command == "amend-plan": emit(amend(args.state, args.reason, args.affected))
        else: emit(mark_stale(args.state, args.artifacts, args.reason))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"workflow state error: {error}", file=os.sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
