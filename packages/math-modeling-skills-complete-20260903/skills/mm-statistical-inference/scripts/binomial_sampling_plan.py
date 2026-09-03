"""Find a one-stage binomial acceptance-sampling plan by exact probabilities."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scipy.stats import binom


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def find_plan(p_acceptable: float, p_rejectable: float, producer_risk: float,
              consumer_risk: float, max_n: int):
    if not (0 < p_acceptable < p_rejectable < 1):
        raise ValueError("require 0 < p_acceptable < p_rejectable < 1")
    if not (0 < producer_risk < 1 and 0 < consumer_risk < 1):
        raise ValueError("risk levels must be in (0, 1)")
    for n in range(1, max_n + 1):
        for c in range(n + 1):
            reject_good = float(binom.sf(c, n, p_acceptable))
            accept_bad = float(binom.cdf(c, n, p_rejectable))
            if reject_good <= producer_risk and accept_bad <= consumer_risk:
                return {"sample_size": n, "accept_if_defects_at_most": c,
                        "reject_good_probability": reject_good, "accept_bad_probability": accept_bad}
    raise ValueError(f"no plan found up to max_n={max_n}")


def run(output_dir: str, p_acceptable: float, p_rejectable: float,
        producer_risk: float, consumer_risk: float, max_n: int) -> int:
    plan = find_plan(p_acceptable, p_rejectable, producer_risk, consumer_risk, max_n)
    plan.update({"p_acceptable": p_acceptable, "p_rejectable": p_rejectable,
                 "producer_risk_limit": producer_risk, "consumer_risk_limit": consumer_risk,
                 "decision_rule": "accept lot when observed defects <= c"})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "sampling_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Binomial sampling plan\n\n" + "\n".join(f"- {k}: {v}" for k, v in plan.items()) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Design an exact one-stage binomial acceptance-sampling plan.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--p-acceptable", type=float, default=0.05)
    parser.add_argument("--p-rejectable", type=float, default=0.15)
    parser.add_argument("--producer-risk", type=float, default=0.05)
    parser.add_argument("--consumer-risk", type=float, default=0.10)
    parser.add_argument("--max-n", type=int, default=1000)
    args = parser.parse_args()
    try:
        if args.max_n < 1:
            raise ValueError("max-n must be positive")
        return run(args.output, args.p_acceptable, args.p_rejectable,
                   args.producer_risk, args.consumer_risk, args.max_n)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
