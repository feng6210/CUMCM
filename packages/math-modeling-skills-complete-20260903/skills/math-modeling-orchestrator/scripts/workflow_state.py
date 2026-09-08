"""Fail-closed, artifact-aware workflow state for the math-modeling Skill suite."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = (
    "NEW", "INPUT_REGISTERED", "DECOMPOSED",
    "SEMANTICS_REVIEW", "SEMANTICS_LOCKED",
    "DATA_AUDITED", "BASELINE_SOLVING", "BASELINE_READY",
    "MODEL_PLANNED", "INNOVATION_PROPOSED", "AWAITING_MODEL_APPROVAL", "USER_APPROVED",
    "SOLVING", "SOLVED", "BENCHMARK_CHALLENGE", "INTEGRITY_AUDIT", "VALIDATING",
    "PASS", "PARTIAL", "FAIL", "RESULT_TO_CLAIM", "WRITING", "FIGURES", "DELIVERING",
    "REVIEWING", "COMPLETE", "BLOCKED_INPUT", "BLOCKED_CAPABILITY",
)
EVIDENCE = ("NOT_EVALUATED", "PASS", "PARTIAL", "FAIL")
RESULT_TO_CLAIM = ("NOT_EVALUATED", "YES", "PARTIAL", "NO", "BLOCKED")
TASK_MODES = ("training", "live_contest", "coursework", "research", "business", "engineering")
DELIVERABLE_MODES = ("analysis", "code", "figures", "paper_outline", "cumcm_latex_paper", "submission_package")
REPORTING_PROFILES = ("competition_compact", "research_audit")
POLICY_STATUSES = ("NOT_REQUIRED", "PENDING", "VALIDATED", "BLOCKED")

# The minimum-baseline stage is deliberately mandatory. A task whose baseline is
# genuinely not applicable still passes through BASELINE_SOLVING -> BASELINE_READY
# with an explicit not-applicable baseline record; it must not jump directly from
# semantics/data audit to MODEL_PLANNED.
ALLOWED = {
    "NEW": {"INPUT_REGISTERED", "BLOCKED_INPUT"},
    "INPUT_REGISTERED": {"DECOMPOSED", "BLOCKED_INPUT"},
    "DECOMPOSED": {"SEMANTICS_REVIEW", "BLOCKED_INPUT"},
    "SEMANTICS_REVIEW": {"SEMANTICS_LOCKED", "DECOMPOSED", "BLOCKED_INPUT"},
    "SEMANTICS_LOCKED": {"DATA_AUDITED", "BASELINE_SOLVING", "BLOCKED_INPUT"},
    "DATA_AUDITED": {"BASELINE_SOLVING", "BLOCKED_INPUT", "BLOCKED_CAPABILITY"},
    "BASELINE_SOLVING": {"BASELINE_READY", "BLOCKED_INPUT", "BLOCKED_CAPABILITY"},
    "BASELINE_READY": {"MODEL_PLANNED", "INNOVATION_PROPOSED", "BLOCKED_CAPABILITY"},
    "MODEL_PLANNED": {"INNOVATION_PROPOSED", "BLOCKED_CAPABILITY"},
    "INNOVATION_PROPOSED": {"AWAITING_MODEL_APPROVAL", "SEMANTICS_REVIEW"},
    "AWAITING_MODEL_APPROVAL": {"USER_APPROVED", "INNOVATION_PROPOSED", "SEMANTICS_REVIEW", "BLOCKED_INPUT"},
    "USER_APPROVED": {"SOLVING", "INNOVATION_PROPOSED", "SEMANTICS_REVIEW"},
    "SOLVING": {"SOLVED", "BLOCKED_INPUT", "BLOCKED_CAPABILITY", "SEMANTICS_REVIEW"},
    "SOLVED": {"BENCHMARK_CHALLENGE", "INTEGRITY_AUDIT", "VALIDATING"},
    "BENCHMARK_CHALLENGE": {"INTEGRITY_AUDIT", "VALIDATING", "SOLVING", "PARTIAL", "FAIL", "BLOCKED_INPUT"},
    "INTEGRITY_AUDIT": {"VALIDATING", "FAIL", "BLOCKED_INPUT"},
    "VALIDATING": {"PASS", "PARTIAL", "FAIL"},
    "PASS": {"RESULT_TO_CLAIM", "DELIVERING"},
    "PARTIAL": {"RESULT_TO_CLAIM", "DELIVERING", "SOLVING", "SEMANTICS_REVIEW"},
    "FAIL": {"SOLVING", "SEMANTICS_REVIEW", "BLOCKED_CAPABILITY"},
    "RESULT_TO_CLAIM": {"WRITING", "SOLVING", "SEMANTICS_REVIEW", "BLOCKED_INPUT"},
    "WRITING": {"FIGURES", "REVIEWING", "SOLVING", "SEMANTICS_REVIEW"},
    "FIGURES": {"DELIVERING", "REVIEWING", "SOLVING", "SEMANTICS_REVIEW"},
    "DELIVERING": {"REVIEWING"},
    "REVIEWING": {"COMPLETE", "SOLVING", "WRITING", "SEMANTICS_REVIEW"},
    "BLOCKED_INPUT": {"INPUT_REGISTERED", "DECOMPOSED", "SEMANTICS_REVIEW", "DATA_AUDITED", "BASELINE_SOLVING", "INNOVATION_PROPOSED"},
    "BLOCKED_CAPABILITY": {"BASELINE_SOLVING", "SOLVING"},
    "COMPLETE": set(),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("YAML input requires PyYAML") from exc
    return yaml.safe_load(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def validate_state(state: dict) -> None:
    required = {
        "schema_version", "task_id", "scope", "stage", "task_mode", "deliverable_mode",
        "output_language", "paper_profile", "paper_format", "latex_engine", "problem_parts",
        "inputs", "assumptions", "claims", "artifacts", "evidence_status", "unresolved",
        "next_skill", "history", "result_to_claim_status", "stale_artifacts",
    }
    missing = required - state.keys()
    if missing:
        raise ValueError("missing state fields: " + ", ".join(sorted(missing)))
    if state["stage"] not in STAGES:
        raise ValueError(f"unknown stage: {state['stage']}")
    if state["evidence_status"] not in EVIDENCE:
        raise ValueError(f"unknown evidence status: {state['evidence_status']}")
    if state["result_to_claim_status"] not in RESULT_TO_CLAIM:
        raise ValueError("unknown result_to_claim_status")
    if state["task_mode"] not in TASK_MODES:
        raise ValueError("unknown task_mode")
    if state["deliverable_mode"] not in DELIVERABLE_MODES:
        raise ValueError("unknown deliverable_mode")
    profile = state.get("reporting_profile")
    if profile is not None and profile not in REPORTING_PROFILES:
        raise ValueError("unknown reporting_profile")
    policy_status = state.get("competition_policy_status")
    if policy_status is not None and policy_status not in POLICY_STATUSES:
        raise ValueError("unknown competition_policy_status")


def default_reporting_profile(task_mode: str) -> str:
    return "competition_compact" if task_mode in {"training", "live_contest", "coursework"} else "research_audit"


def initialize(path: Path, task_id: str, scope: str, task_mode: str, deliverable_mode: str) -> dict:
    if path.exists():
        raise FileExistsError(f"state already exists: {path}")
    state = {
        "schema_version": "3.0",
        "task_id": task_id,
        "scope": scope,
        "stage": "NEW",
        "task_mode": task_mode,
        "deliverable_mode": deliverable_mode,
        "reporting_profile": default_reporting_profile(task_mode),
        "competition_policy_status": "PENDING" if task_mode == "live_contest" else "NOT_REQUIRED",
        "competition_policy": None,
        "output_language": "zh-CN",
        "paper_profile": "cumcm-2026-electronic",
        "paper_format": "latex",
        "latex_engine": "xelatex",
        "problem_parts": [],
        "inputs": [],
        "assumptions": [],
        "claims": [],
        "artifacts": [],
        "problem_semantics": None,
        "baseline_result": None,
        "benchmark_challenge": None,
        "experiment_plan": None,
        "run_manifest": None,
        "paper_claim_audit_status": "NOT_EVALUATED",
        "citation_audit_status": "NOT_EVALUATED",
        "compile_status": "NOT_EVALUATED",
        "result_to_claim_status": "NOT_EVALUATED",
        "evidence_status": "NOT_EVALUATED",
        "unresolved": [],
        "stale_artifacts": [],
        "next_skill": "mm-problem-decomposer",
        "model_approval": None,
        "history": [{"at": now(), "event": "initialized", "stage": "NEW"}],
    }
    write_json(path, state)
    return state


def validate_competition_policy(policy_path: Path) -> dict:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise RuntimeError("competition policy validation requires jsonschema>=4.23") from exc

    payload = load_document(policy_path)
    if not isinstance(payload, dict):
        raise ValueError("competition policy root must be an object")
    package_root = Path(__file__).resolve().parents[3]
    schema_path = package_root / "schemas" / "competition_policy.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    errors = sorted(validator_cls(schema).iter_errors(payload), key=lambda e: (list(e.absolute_path), e.message))
    if errors:
        joined = "; ".join(f"{list(error.absolute_path)}: {error.message}" for error in errors[:8])
        raise ValueError(f"competition policy schema failed: {joined}")
    return payload


def record_competition_policy(path: Path, policy_path: Path) -> dict:
    state = read_json(path)
    validate_state(state)
    policy_path = policy_path.resolve()
    policy = validate_competition_policy(policy_path)
    if state["task_mode"] == "live_contest" and policy.get("stage") != "live_contest":
        raise ValueError("live_contest workflow requires a live_contest competition policy")
    state["competition_policy_status"] = "VALIDATED"
    state["competition_policy"] = {
        "file": str(policy_path),
        "sha256": sha256_file(policy_path),
        "stage": policy.get("stage"),
        "ai_allowed": policy.get("ai_allowed"),
        "ai_scope": policy.get("ai_scope"),
        "web_allowed": policy.get("web_allowed"),
        "web_scope": policy.get("web_scope"),
        "external_papers_allowed": policy.get("external_papers_allowed"),
        "external_papers_scope": policy.get("external_papers_scope"),
        "benchmark_answers_allowed": policy.get("benchmark_answers_allowed"),
        "benchmark_answers_scope": policy.get("benchmark_answers_scope"),
        "source": policy.get("source"),
    }
    state["history"].append({
        "at": now(),
        "event": "competition_policy_recorded",
        "status": "VALIDATED",
        "policy_sha256": state["competition_policy"]["sha256"],
    })
    write_json(path, state)
    return state


def assert_competition_policy_current(state: dict) -> dict:
    if state.get("competition_policy_status") != "VALIDATED":
        raise ValueError("live_contest requires a validated COMPETITION_POLICY before substantive AI work")
    binding = state.get("competition_policy")
    if not isinstance(binding, dict):
        raise ValueError("validated competition policy is missing its hash-bound record")
    file_value = binding.get("file")
    expected_hash = binding.get("sha256")
    if not isinstance(file_value, str) or not file_value or not isinstance(expected_hash, str):
        raise ValueError("validated competition policy binding is incomplete")
    policy_path = Path(file_value)
    if not policy_path.is_file():
        raise ValueError("bound COMPETITION_POLICY file is missing; revalidate policy before continuing")
    if sha256_file(policy_path) != expected_hash:
        raise ValueError("bound COMPETITION_POLICY changed after validation; revalidate policy before continuing")
    return binding


def assert_live_contest_ai_use_allowed(state: dict) -> dict:
    binding = assert_competition_policy_current(state)
    if binding.get("ai_allowed") == "forbidden":
        raise ValueError("COMPETITION_POLICY forbids AI use in this live contest; stop the AI workflow")
    if binding.get("ai_allowed") == "restricted" and not binding.get("ai_scope"):
        raise ValueError("restricted AI permission requires an explicit ai_scope")
    return binding


def transition(path: Path, target: str, next_skill: str | None, evidence_status: str | None) -> dict:
    state = read_json(path)
    validate_state(state)
    current = state["stage"]
    if target not in ALLOWED[current]:
        raise ValueError(f"transition not allowed: {current} -> {target}")

    # Registering inputs/rules is allowed before policy binding. Any substantive
    # decomposition/modeling/validation/writing transition is AI work and must
    # already be permitted by a current official/course policy in live contests.
    if state["task_mode"] == "live_contest" and target not in {"INPUT_REGISTERED", "BLOCKED_INPUT"}:
        assert_live_contest_ai_use_allowed(state)

    approval = state.get("model_approval") or {}
    if target == "USER_APPROVED" and approval.get("approved") is not True:
        raise ValueError("model approval record required before USER_APPROVED")
    if target == "SOLVING" and current not in {
        "USER_APPROVED", "PARTIAL", "FAIL", "RESULT_TO_CLAIM", "WRITING", "FIGURES",
        "REVIEWING", "BENCHMARK_CHALLENGE",
    }:
        raise ValueError("initial main SOLVING requires USER_APPROVED; use BASELINE_SOLVING for pre-approval baselines")
    if target == "MODEL_PLANNED" and current != "BASELINE_READY":
        raise ValueError("MODEL_PLANNED requires BASELINE_READY; record an explicit not-applicable baseline when necessary")
    new_evidence = evidence_status or state["evidence_status"]
    if target == "DELIVERING" and new_evidence not in {"PASS", "PARTIAL"}:
        raise ValueError("DELIVERING requires PASS or PARTIAL evidence")
    state["stage"], state["next_skill"], state["evidence_status"] = target, next_skill, new_evidence
    state["history"].append({"at": now(), "event": "transition", "from": current, "to": target})
    write_json(path, state)
    return state


def approve(path: Path, decision_path: Path) -> dict:
    state = read_json(path)
    validate_state(state)
    if state["stage"] != "AWAITING_MODEL_APPROVAL":
        raise ValueError("approval is accepted only at AWAITING_MODEL_APPROVAL")
    decision = read_json(decision_path)
    routes, claims = decision.get("selected_routes"), decision.get("approved_claim_scope")
    if decision.get("approved") is not True:
        raise ValueError("decision.approved must be true")
    if not isinstance(routes, dict) or not routes or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in routes.items()):
        raise ValueError("selected_routes must be a non-empty object of non-empty strings")
    if not isinstance(claims, list) or not claims or not all(isinstance(item, str) and item for item in claims):
        raise ValueError("approved_claim_scope must be a non-empty string array")
    decision = dict(decision)
    decision.setdefault("decided_at", now())
    state["model_approval"] = decision
    state["history"].append({"at": now(), "event": "model_approval_recorded", "routes": routes})
    write_json(path, state)
    return state


def amend(path: Path, reason: str, affected: list[str], semantic: bool = False) -> dict:
    state = read_json(path)
    validate_state(state)
    if not reason.strip() or not affected:
        raise ValueError("amendment requires a reason and affected artifacts")
    state["stage"] = "SEMANTICS_REVIEW" if semantic else "INNOVATION_PROPOSED"
    state["model_approval"] = None
    if semantic:
        state["problem_semantics"] = None
        state["baseline_result"] = None
        state["benchmark_challenge"] = None
        state["evidence_status"] = "NOT_EVALUATED"
        state["result_to_claim_status"] = "NOT_EVALUATED"
    state["stale_artifacts"] = sorted(set(state["stale_artifacts"]) | set(affected))
    state["history"].append({
        "at": now(), "event": "plan_amended", "reason": reason, "affected": affected,
        "semantic": semantic,
    })
    write_json(path, state)
    return state


def mark_stale(path: Path, artifacts: list[str], reason: str) -> dict:
    state = read_json(path)
    validate_state(state)
    if not artifacts:
        raise ValueError("at least one artifact is required")
    state["stale_artifacts"] = sorted(set(state["stale_artifacts"]) | set(artifacts))
    state["paper_claim_audit_status"] = "STALE"
    state["citation_audit_status"] = "STALE"
    state["compile_status"] = "STALE"
    state["history"].append({"at": now(), "event": "artifacts_marked_stale", "reason": reason, "artifacts": artifacts})
    write_json(path, state)
    return state


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and enforce a fail-closed mathematical-modeling workflow state.")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a workflow state without overwriting an existing file.")
    init.add_argument("--state", type=Path, required=True)
    init.add_argument("--task-id", required=True)
    init.add_argument("--scope", default="")
    init.add_argument("--task-mode", choices=TASK_MODES, default="training")
    init.add_argument("--deliverable-mode", choices=DELIVERABLE_MODES, default="analysis")
    show = sub.add_parser("show", help="Validate and print a workflow state.")
    show.add_argument("--state", type=Path, required=True)
    move = sub.add_parser("transition", help="Apply an allowed stage transition.")
    move.add_argument("--state", type=Path, required=True)
    move.add_argument("--to", choices=STAGES, required=True)
    move.add_argument("--next-skill")
    move.add_argument("--evidence-status", choices=EVIDENCE)
    policy = sub.add_parser("set-competition-policy", help="Validate and bind COMPETITION_POLICY.yaml to a workflow state.")
    policy.add_argument("--state", type=Path, required=True)
    policy.add_argument("--policy-file", type=Path, required=True)
    approval = sub.add_parser("approve-model", help="Record a valid model decision while awaiting approval.")
    approval.add_argument("--state", type=Path, required=True)
    approval.add_argument("--decision-file", type=Path, required=True)
    amendment = sub.add_parser("amend-plan", help="Invalidate approval when a material modeling plan changes.")
    amendment.add_argument("--state", type=Path, required=True)
    amendment.add_argument("--reason", required=True)
    amendment.add_argument("--affected", nargs="+", required=True)
    amendment.add_argument("--semantic", action="store_true", help="Return to semantic review and invalidate all downstream evidence")
    stale = sub.add_parser("mark-stale", help="Mark result-derived artifacts stale after source changes.")
    stale.add_argument("--state", type=Path, required=True)
    stale.add_argument("--reason", required=True)
    stale.add_argument("--artifacts", nargs="+", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            emit(initialize(args.state, args.task_id, args.scope, args.task_mode, args.deliverable_mode))
        elif args.command == "show":
            state = read_json(args.state)
            validate_state(state)
            emit(state)
        elif args.command == "transition":
            emit(transition(args.state, args.to, args.next_skill, args.evidence_status))
        elif args.command == "set-competition-policy":
            emit(record_competition_policy(args.state, args.policy_file))
        elif args.command == "approve-model":
            emit(approve(args.state, args.decision_file))
        elif args.command == "amend-plan":
            emit(amend(args.state, args.reason, args.affected, args.semantic))
        else:
            emit(mark_stale(args.state, args.artifacts, args.reason))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"workflow state error: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
