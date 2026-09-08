#!/usr/bin/env python3
"""Build a deterministic preview ZIP and fresh manifest from the package source tree.

The script does not modify the repository. It is intended for CI and release
preparation so that source changes cannot silently ship with stale manifest or
SHA256SUMS metadata. Wall-clock time is deliberately excluded by default so
identical source bytes produce identical ZIP bytes across different days.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

EXCLUDED_NAMES = {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}


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
        if path.name in EXCLUDED_NAMES:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result.append(path)
    return sorted(result, key=lambda p: p.relative_to(package_dir).as_posix())


def build_manifest(package_dir: Path, files: list[Path], release_date: str | None = None) -> dict:
    skills_dir = package_dir / "skills"
    skill_count = sum(1 for path in skills_dir.glob("*/SKILL.md") if path.is_file())
    entries = []
    total_bytes = 0
    for path in files:
        rel = path.relative_to(package_dir).as_posix()
        size = path.stat().st_size
        total_bytes += size
        entries.append({"path": rel, "bytes": size, "sha256": sha256_file(path)})
    return {
        "schema_version": "3.0",
        "package": package_dir.name,
        "release_date": release_date,
        "skill_count": skill_count,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "hash_algorithm": "SHA-256",
        "manifest_excludes": sorted(EXCLUDED_NAMES),
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
) -> dict:
    package_dir = package_dir.resolve()
    files = source_files(package_dir)
    manifest = build_manifest(package_dir, files, release_date=release_date)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sums_bytes = ("".join(f"{entry['sha256']}  {entry['path']}\n" for entry in manifest["files"])).encode("utf-8")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        prefix = package_dir.name
        for path in files:
            rel = path.relative_to(package_dir).as_posix()
            deterministic_write(archive, f"{prefix}/{rel}", path.read_bytes())
        deterministic_write(archive, f"{prefix}/PACKAGE_MANIFEST.json", manifest_bytes)
        deterministic_write(archive, f"{prefix}/SHA256SUMS.txt", sums_bytes)

    with zipfile.ZipFile(output_zip, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP reopen CRC failure: {bad}")
        names = archive.namelist()
        expected = len(files) + 2
        if len(names) != expected:
            raise RuntimeError(f"ZIP entry count mismatch: {len(names)} != {expected}")

    report = {
        "status": "PASSED",
        "package_dir": str(package_dir),
        "output_zip": str(output_zip.resolve()),
        "zip_sha256": sha256_file(output_zip),
        "source_file_count": len(files),
        "zip_entry_count": len(files) + 2,
        "skill_count": manifest["skill_count"],
        "release_date": release_date,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "sha256s_sha256": sha256_bytes(sums_bytes),
        "deterministic_without_wall_clock": release_date is None,
        "note": "Preview ZIP contains freshly generated manifest/SHA256SUMS; repository files are not modified.",
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
    args = parser.parse_args()
    try:
        report = build(args.package_dir, args.output_zip, args.report, release_date=args.release_date)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
