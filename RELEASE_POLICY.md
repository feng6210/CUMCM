# Release and package synchronization policy

## Source of truth

- `main` is the authoritative current source.
- `packages/math-modeling-skills-complete-20260903/` is the installable source package retained under its historical directory name for compatibility.
- `dist/math-modeling-skills-complete-20260903.zip` is a historical packaged snapshot. It must not be described as current merely because its filename is unchanged.
- Versioned GitHub Release assets produced by `.github/workflows/release-package.yml` are the preferred distribution artifacts for v1.0.0 and later.
- `PACKAGE_MANIFEST.json`, `SHA256SUMS.txt`, and `VALIDATION_REPORT.json` are release metadata only when generated from the same exact source SHA as the distributed ZIP.

## Pull requests

`skill-regression` must pass before merge. It checks:

1. workflow/state/schema regressions;
2. system benchmark specifications;
3. deterministic visualization tests;
4. package structure;
5. reproducible preview package generation.

For pull requests, CI builds a deterministic preview ZIP. Preview packages deliberately embed `PREVIEW_BUILD_NOT_FORMAL_RELEASE_VALIDATION` rather than copying a stale committed validation report. A preview artifact is for review/testing and is not a formal release.

## Formal releases

Formal releases use `.github/workflows/release-package.yml` from a clean `main` commit.

The workflow:

1. checks out the exact source SHA;
2. installs the declared package dependencies and CJK fonts used by visualization regressions;
3. reruns root workflow/contract tests;
4. validates every system benchmark specification;
5. reruns visualization regressions;
6. checks package structure, Skill count, license files, and compiled-cache hygiene;
7. writes a fresh scoped `VALIDATION_REPORT.json` containing the release version, date, and source SHA;
8. runs `tools/build_release_package.py` with that validation report and explicit release date;
9. reopens the generated ZIP and records package hashes through the builder;
10. uploads the ZIP, validation report, package build report, release SHA256 file, and release notes as an Actions artifact.

When the workflow is manually invoked with `publish_release=true`, a second job creates the GitHub Release and tag with the validated artifacts. It refuses to overwrite an existing release of the same version.

## Validation scope

A formal release validation report certifies only the software/package checks actually rerun for that source SHA. It does not certify:

- mathematical correctness for arbitrary contest problems;
- correctness of user-supplied data or assumptions;
- Origin/Visio availability on another machine;
- full XeLaTeX rendering on every environment;
- independent reproduction of every numerical experiment;
- competition award level.

Claims outside the tested scope must remain explicit and separate.

## Licensing and third-party material

The repository-level license is `LICENSE`. Third-party attribution and licensing boundaries are recorded in `THIRD_PARTY_NOTICES.md` and in package-local provenance notices. Third-party notices must not be removed from release packages when they cover redistributed or adapted material.

## Versioning

The historical `20260903` package directory is retained for installation compatibility. Public release identity is versioned independently with semantic tags such as `v1.0.0`.

Breaking changes to package layout or Skill contracts require a major-version decision or an explicit migration note. Backward-compatible workflow/documentation improvements may use minor or patch releases as appropriate.

## Release integrity rules

- Do not hand-edit a ZIP after its hashes are recorded.
- Do not reuse a validation report from another source SHA.
- Do not label preview artifacts as formal releases.
- Do not silently replace an existing versioned GitHub Release.
- Re-run the formal release workflow after any package-content change.
- Keep release notes, source SHA, validation report, ZIP hash, and GitHub tag consistent.
