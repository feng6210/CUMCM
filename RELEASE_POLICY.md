# Release and package synchronization policy

## Source of truth

- `main` is the authoritative current source.
- `dist/math-modeling-skills-complete-20260903.zip` is a packaged release snapshot, not a promise that every source commit has already been repacked.
- `packages/math-modeling-skills-complete-20260903/PACKAGE_MANIFEST.json` and `SHA256SUMS.txt` describe the committed packaged snapshot when refreshed for a release.

## Pull requests

`skill-regression` must pass before merge. It checks:

1. workflow/state/schema regressions;
2. all system benchmark specifications;
3. deterministic visualization tests;
4. package structure;
5. reproducible preview package generation.

For pull requests, CI uploads `math-modeling-skills-package-preview` containing a fresh deterministic ZIP and build report from the PR source tree. The preview artifact is for review/testing and does not silently overwrite `dist/`.

Preview builds deliberately omit wall-clock release metadata, so identical package source bytes produce identical ZIP bytes across different days. A formal release may add an explicit date with `--release-date YYYY-MM-DD`; the date is then part of the release bytes by design.

## Formal package refresh

A formal packaged release should:

1. start from a clean commit with passing CI;
2. run `tools/build_release_package.py --release-date YYYY-MM-DD` from that commit;
3. refresh the committed package manifest and SHA256SUMS using the same source tree and explicit release metadata;
4. replace `dist/math-modeling-skills-complete-20260903.zip` with the generated ZIP;
5. update the root README ZIP SHA-256;
6. tag the release commit or otherwise record the exact source SHA;
7. rerun release checks after any package-content change.

Do not call a ZIP “current” merely because its filename is unchanged. Do not modify a ZIP by hand after its hashes are recorded.

## Versioning direction

The historical `20260903` directory name is retained for installation compatibility. Future breaking package-layout changes should move to semantic release identifiers or a stable `packages/current` entry point rather than encoding every content update into ad-hoc folder renames.
