#!/usr/bin/env python3
"""Build a deterministic preview ZIP and fresh metadata from the package source tree.

The script does not modify the repository. It is intended for CI and release
preparation so source changes cannot silently ship with stale manifest,
SHA256SUMS or validation metadata. Wall-clock time is deliberately excluded by
default so identical source bytes produce identical preview ZIP bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

SOURCE_METADATA_TO_REGENERATE = {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt", "VALIDATION_REPORT.json"}
SELF_REFERENTIAL_METADATA = {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(package_dir: Path) -> list[Path]:
    result: list[Path] = []
    for path in package_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SOURCE_METADATA_TO_REGENERATE:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result.append(path)
    return sorted(result, key=lambda p: p.relative_to(package_dir).as_posix())


def preview_validation_bytes() -> bytes:
    payload = {
        "schema_version": "preview-1.0",
        "status": "PREVIEW_BUILD_NOT_FORMAL_RELEASE_VALIDATION",
        "semantic_claim_validation": False,
        "scope": "package source was rebuilt in CI; formal release validation was not embedded",
        "note": "Use the PR workflow checks and package-build-report artifact for preview evidence. Do not treat this marker as model or release certification.",
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validation_bytes(validation_report: Path | None) -> tuple[bytes, str]:
    if validation_report is None:
        return preview_validation_bytes(), "preview_marker"
    validation_report = validation_report.resolve()
    payload = json.loads(validation_report.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not payload.get("status"):
        raise ValueError("formal validation report must be a JSON object with status")
    return validation_report.read_bytes(), "provided_formal_report"


def build_manifest(
    package_dir: Path,
    files: list[Path],
    validation_report_bytes: bytes,
    release_date: str | None = None,
) -> dict:
    skills_dir = package_dir / "skills"
    skill_count = sum(1 for path in skills_dir.glob("*/SKILL.md") if path.is_file())
    entries = []
    total_bytes = 0
    for path in files:
        rel = path.relative_to(package_dir).as_posix()
        size = path.stat().st_size
        total_bytes += size
        entries.append({"path": rel, "bytes": size, "sha256": sha256_file(path)})

    validation_entry = {
        "path": "VALIDATION_REPORT.json",
        "bytes": len(validation_report_bytes),
        "sha256": sha256_bytes(validation_report_bytes),
        "generated": True,
    }
    entries.append(validation_entry)
    entries.sort(key=lambda item: item["path"])
    total_bytes += len(validation_report_bytes)

    return {
        "schema_version": "3.0",
        "package": package_dir.name,
        "release_date": release_date,
        "skill_count": skill_count,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "hash_algorithm": "SHA-256",
        "manifest_excludes": sorted(SELF_REFERENTIAL_METADATA),
        "regenerated_metadata": sorted(SOURCE_METADATA_TO_REGENERATE),
        "files": entries,
    }


def deterministic_write(archive: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def build(
    package_dir: Path,
    output_zip: Path,
    report_path: Path | None = None,
    release_date: str | None = None,
    validation_report: Path | None = None,
) -> dict:
    package_dir = package_dir.resolve()
    files = source_files(package_dir)
    validation_report_bytes, validation_mode = validation_bytes(validation_report)
    manifest = build_manifest(
        package_dir,
        files,
        validation_report_bytes=validation_report_bytes,
        release_date=release_date,
    )
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sums_bytes = ("".join(f"{entry['sha256']}  {entry['path']}\n" for entry in manifest["files"])).encode("utf-8")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        prefix = package_dir.name
        for path in files:
            rel = path.relative_to(package_dir).as_posix()
            deterministic_write(archive, f"{prefix}/{rel}", path.read_bytes())
        deterministic_write(archive, f"{prefix}/VALIDATION_REPORT.json", validation_report_bytes)
        deterministic_write(archive, f"{prefix}/PACKAGE_MANIFEST.json", manifest_bytes)
        deterministic_write(archive, f"{prefix}/SHA256SUMS.txt", sums_bytes)

    with zipfile.ZipFile(output_zip, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP reopen CRC failure: {bad}")
        names = archive.namelist()
        expected = len(files) + 3
        if len(names) != expected:
            raise RuntimeError(f"ZIP entry count mismatch: {len(names)} != {expected}")

    report = {
        "status": "PASSED",
        "package_dir": str(package_dir),
        "output_zip": str(output_zip.resolve()),
        "zip_sha256": sha256_file(output_zip),
        "source_file_count": len(files),
        "manifest_file_count": manifest["file_count"],
        "zip_entry_count": len(files) + 3,
        "skill_count": manifest["skill_count"],
        "release_date": release_date,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "sha256s_sha256": sha256_bytes(sums_bytes),
        "validation_report_sha256": sha256_bytes(validation_report_bytes),
        "validation_report_mode": validation_mode,
        "deterministic_without_wall_clock": release_date is None,
        "note": "ZIP contains freshly generated manifest/SHA256SUMS and either a preview validation marker or an explicitly provided formal validation report; repository files are not modified.",
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=Path("packages/math-modeling-skills-complete-20260903"),
    )
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--release-date",
        help="Optional explicit YYYY-MM-DD release metadata. Omit for source-byte-deterministic CI previews.",
    )
    parser.add_argument(
        "--validation-report",
        type=Path,
        help="Optional formal JSON validation report to embed. Omit in CI previews to embed an explicit PREVIEW marker instead of stale committed validation metadata.",
    )
    args = parser.parse_args()
    try:
        report = build(
            args.package_dir,
            args.output_zip,
            args.report,
            release_date=args.release_date,
            validation_report=args.validation_report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
