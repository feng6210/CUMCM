# Changelog

All notable release-level changes to the CUMCM Skill suite are documented here.

## Unreleased

### Public repository polish

- Reworked the root README into a public landing page with release/CI/license badges, quick-start instructions, usage examples, execution-profile guidance, repository structure, verification steps, and clearer compatibility boundaries.
- Added `CONTRIBUTING.md` with contribution scope, testing guidance, complexity constraints, and third-party attribution requirements.
- Added public bug-report and feature-request issue forms plus a concise pull-request template.
- Performed a public-readiness scan for common committed secret/token, `.env`, email, and local absolute-path patterns on the current tree; no matches were found in the scanned patterns.

## v1.0.0 — 2026-09-14

### Execution model

- Introduced three execution profiles: `standard`, `structured`, and `strict_submission_audit`.
- Made `standard` the default path: problem semantics → main model → solve → claim-matched validation → figures/paper/delivery.
- Removed default requirements for A/B/C route generation, pre-solve approval, external benchmark challenge, unnecessary multi-seed runs, fixed figure quotas, and multi-agent audit chains.
- Made workflow state, schemas, manifests, benchmark challenge files, result-to-claim maps, narrative maps, and figure plans optional artifacts that are created only when they have an actual downstream consumer.
- Added `MODELING_SUMMARY.md` as the preferred compact persistence artifact when only one intermediate record is needed.

### Delivery and audit

- Separated normal complete-paper delivery (`formal_delivery`) from provenance-bound `strict_submission_audit`.
- Retained the existing competition-ready hard gate, fresh-subagent review contract, visual binding, support-package checks, and fail-closed provenance validation for explicit strict audits.
- Kept live-contest policy gating for cases where AI, web, external-paper, or benchmark permissions materially affect the current action.

### Contest operations

- Changed the default team-operations output to one compact `CONTEST_PLAN.md`.
- Retained structured `TEAM_ROLES.yaml`, `MILESTONE_PLAN.yaml`, and `QUESTION_HANDOFF.yaml` for machine-assisted collaboration and cross-session recovery.

### Compatibility retained

- 22 installable Skills remain in the package.
- Specialist modeling Skills, visualization renderers, CUMCM LaTeX workflow, schemas, system benchmarks, and deterministic package builder remain available.
- Existing strict competition-delivery regressions and visualization safety checks remain intact.

### Release engineering

- Added regression coverage to prevent the heavy audit workflow from becoming the default again.
- Rewrote repository and package README entry points for external users.
- Added an MIT repository license and consolidated third-party notices for release use.

## Pre-1.0 history

The repository history before v1.0.0 contains the initial 22-Skill package, semantic/baseline gates, system benchmarks, full-corpus plotting support, editable TikZ schematics, paper-quality checks, visual provenance hardening, and strict competition-delivery validation.
