#!/usr/bin/env python3
"""Validate JSON/YAML workflow artifacts against a versioned JSON Schema.

This checker validates structure only.  A schema PASS does not imply that the
mathematics, evidence, interpretation, benchmark comparison or paper claim is
correct.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("YAML input requires PyYAML") from exc
    return yaml.safe_load(text)


def format_path(parts) -> str:
    if not parts:
        return "$"
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def validate(schema_path: Path, input_path: Path) -> dict[str, Any]:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("JSON Schema validation requires jsonschema>=4.23") from exc

    schema = load_document(schema_path)
    payload = load_document(input_path)
    if not isinstance(schema, dict):
        raise ValueError("schema root must be an object")

    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: (list(e.absolute_path), e.message))

    return {
        "checker": "versioned-contract-schema",
        "semantic_validation": False,
        "schema": str(schema_path.resolve()),
        "input": str(input_path.resolve()),
        "status": "PASSED" if not errors else "FAILED",
        "error_count": len(errors),
        "errors": [
            {
                "path": format_path(error.absolute_path),
                "schema_path": format_path(error.absolute_schema_path),
                "message": error.message,
            }
            for error in errors
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = validate(args.schema, args.input)
        code = 0 if report["status"] == "PASSED" else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        report = {
            "checker": "versioned-contract-schema",
            "semantic_validation": False,
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }
        code = 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
