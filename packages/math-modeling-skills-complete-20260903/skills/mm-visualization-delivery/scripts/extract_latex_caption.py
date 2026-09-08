#!/usr/bin/env python3
"""Extract one literal figure caption by a unique label, without running TeX.

Supports figure/figure*, comments, nested braces, an optional short caption and
literal verbatim regions. It is deliberately not a macro expander: generated
labels/captions, included files and conditional TeX must be resolved by the caller.
Missing, duplicate, malformed or subfigure-only targets raise CaptionError.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import sys


class CaptionError(ValueError):
    """The source does not unambiguously identify one complete figure caption."""


COMMAND = re.compile(r"\\([A-Za-z@]+|[^\r\n])")
VERBATIM = {"verbatim", "verbatim*", "Verbatim", "BVerbatim", "lstlisting", "minted", "comment"}
SUBFIGURES = {"subfigure", "subtable"}
CONDITIONALS = {"if", "ifcat", "ifx", "ifnum", "ifdim", "ifodd", "ifvmode", "ifhmode",
                "ifmmode", "ifinner", "ifvoid", "ifhbox", "ifvbox", "ifeof", "iftrue",
                "iffalse", "ifcase", "ifdefined", "ifcsname", "ifincsname", "unless", "else", "or", "fi"}


def _skip_space(text: str, start: int) -> int:
    while start < len(text) and text[start].isspace():
        start += 1
    return start


def _group(text: str, start: int, opener: str = "{") -> tuple[int, int]:
    """Return the content span, honoring escaped delimiters and brace-protected ]."""
    start = _skip_space(text, start)
    if start >= len(text) or text[start] != opener:
        raise CaptionError(f"Expected {opener!r} at character {start}")
    closer = "}" if opener == "{" else "]"
    depth, braces, index = 1, 0, start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            match = COMMAND.match(text, index)
            index = match.end() if match else index + 1
            continue
        if opener == "[":
            if char == "{":
                braces += 1
            elif char == "}":
                if braces == 0:
                    raise CaptionError(f"Unmatched closing brace at character {index}")
                braces -= 1
            elif braces == 0 and char == "[":
                depth += 1
            elif braces == 0 and char == closer:
                depth -= 1
        else:
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
        if depth == 0:
            return start + 1, index
        index += 1
    raise CaptionError(f"Unclosed {opener!r} group at character {start}")


def _mask_noncode(source: str) -> str:
    """Keep original offsets while hiding comments and verbatim command lookalikes."""
    chars = list(source)

    def hide(start, end):
        for index in range(start, end):
            if chars[index] not in "\r\n":
                chars[index] = " "

    index = 0
    while index < len(source):
        if source[index] == "%":
            end = source.find("\n", index)
            end = len(source) if end < 0 else end
            hide(index, end)
            index = end
        elif source[index] == "\\":
            match = COMMAND.match(source, index)
            if match is None:
                index += 1
                continue
            name = match.group(1)
            if name == "verb":
                delimiter_at = match.end()
                if delimiter_at < len(source) and source[delimiter_at] == "*":
                    delimiter_at += 1
                if delimiter_at >= len(source) or source[delimiter_at].isspace():
                    raise CaptionError("Malformed inline verbatim command")
                end = source.find(source[delimiter_at], delimiter_at + 1)
                if end < 0 or "\n" in source[delimiter_at:end]:
                    raise CaptionError("Unterminated inline verbatim command")
                hide(index, end + 1)
                index = end + 1
            elif name == "begin":
                # Common literal listing environments may contain fake figure commands.
                env = re.match(r"\s*\{([^{}\r\n]+)\}", source[match.end():])
                if env and env.group(1) in VERBATIM:
                    end_marker = re.compile(r"\\end\s*\{" + re.escape(env.group(1)) + r"\}")
                    end = end_marker.search(source, match.end() + env.end())
                    if end is None:
                        raise CaptionError("Unterminated verbatim environment: " + env.group(1))
                    hide(index, end.end())
                    index = end.end()
                else:
                    index = match.end()
            else:
                # A control symbol consumes its next character, so \% is not a comment.
                index = match.end()
        else:
            index += 1
    return "".join(chars)


def _without_comments(source: str) -> str:
    """Preserve LaTeX commands; a comment also removes its following line ending."""
    pieces, index = [], 0
    while index < len(source):
        if source[index] == "\\":
            match = COMMAND.match(source, index)
            end = match.end() if match else index + 1
            if match and match.group(1) == "verb":
                delimiter_at = end + int(end < len(source) and source[end] == "*")
                if delimiter_at < len(source):
                    found = source.find(source[delimiter_at], delimiter_at + 1)
                    if found >= 0:
                        end = found + 1
            pieces.append(source[index:end])
            index = end
        elif source[index] == "%":
            newline = source.find("\n", index)
            index = len(source) if newline < 0 else newline + 1
        else:
            pieces.append(source[index])
            index += 1
    return "".join(pieces).strip()


@dataclass
class Caption:
    label: str
    environment: str
    caption_latex: str
    short_caption_latex: str | None
    figure_span: tuple[int, int]
    caption_span: tuple[int, int]
    figure_line: int
    caption_line: int
    source_sha256: str


@dataclass
class _Figure:
    environment: str
    start: int
    end: int = 0
    captions: list = field(default_factory=list)


def _subfigure_command_spans(masked: str) -> list[tuple[int, int]]:
    """Known subfloat/subcaptionbox arguments belong to a child, not its parent."""
    spans = []
    for command in COMMAND.finditer(masked):
        if command.group(1) not in {"subfloat", "subcaptionbox"}:
            continue
        index = _skip_space(masked, command.end())
        if index < len(masked) and masked[index] == "*":
            index = _skip_space(masked, index + 1)
        # subfloat[short][caption]{body}; subcaptionbox[short]{caption}[width][pos]{body}.
        before = 2 if command.group(1) == "subfloat" else 1
        for _ in range(before):
            if index < len(masked) and masked[index] == "[":
                _, end = _group(masked, index, "[")
                index = _skip_space(masked, end + 1)
        _, end = _group(masked, index)
        index = _skip_space(masked, end + 1)
        if command.group(1) == "subcaptionbox":
            for _ in range(2):
                if index < len(masked) and masked[index] == "[":
                    _, end = _group(masked, index, "[")
                    index = _skip_space(masked, end + 1)
            _, end = _group(masked, index)
        spans.append((command.start(), end + 1))
    return spans


def extract_caption(source: str, label: str) -> Caption:
    """Select exactly one literal target label, then exactly one parent caption."""
    if not isinstance(label, str) or not label.strip() or label != label.strip() or any(c in label for c in "{}\\\r\n"):
        raise CaptionError("A nonempty literal label without TeX commands is required")
    masked = _mask_noncode(source)
    subfigure_spans = _subfigure_command_spans(masked)
    environments, figures, matches = [], [], []
    for command in COMMAND.finditer(masked):
        name = command.group(1)
        if name in CONDITIONALS:
            raise CaptionError("Conditional TeX is not evaluated; supply the resolved figure source")
        if name in {"begin", "end"}:
            a, b = _group(masked, command.end())
            environment = masked[a:b].strip()
            if name == "begin":
                if environment in {"figure", "figure*"}:
                    if any(env in {"figure", "figure*"} for env, _ in environments):
                        raise CaptionError("Nested figure environments are ambiguous")
                    figure = _Figure(environment, command.start())
                    figures.append(figure)
                else:
                    figure = None
                environments.append((environment, figure))
            else:
                if not environments or environments[-1][0] != environment:
                    raise CaptionError("Unmatched environment end: " + environment)
                _, figure = environments.pop()
                if figure is not None:
                    figure.end = b + 1
        elif name in {"caption", "label"}:
            owners = [figure for _, figure in environments if figure is not None]
            owner = owners[-1] if owners else None
            in_subfigure = any(env in SUBFIGURES for env, _ in environments) or any(
                start <= command.start() < end for start, end in subfigure_spans)
            if name == "label":
                a, b = _group(masked, command.end())
                if _without_comments(source[a:b]) == label:
                    matches.append((owner, in_subfigure))
            elif owner is not None and not in_subfigure:
                index = _skip_space(masked, command.end())
                starred = index < len(masked) and masked[index] == "*"
                if starred:
                    index = _skip_space(masked, index + 1)
                short = None
                if index < len(masked) and masked[index] == "[":
                    a, b = _group(masked, index, "[")
                    short = _without_comments(source[a:b])
                    index = b + 1
                a, b = _group(masked, index)
                owner.captions.append((a, b, short, starred, command.start()))
    if environments:
        raise CaptionError("Unclosed environment: " + environments[-1][0])
    if len(matches) != 1:
        raise CaptionError(f"Expected exactly one label {label!r}; found {len(matches)}")
    figure, subfigure = matches[0]
    if figure is None or subfigure:
        raise CaptionError("Target label must identify a figure, not a subfigure or an outside label")
    if len(figure.captions) != 1:
        raise CaptionError(f"Target figure needs exactly one complete caption; found {len(figure.captions)}")
    a, b, short, starred, start = figure.captions[0]
    caption = _without_comments(source[a:b])
    if starred or not caption:
        raise CaptionError("Target figure requires a nonempty numbered caption")
    return Caption(label, figure.environment, caption, short, (figure.start, figure.end),
                   (a, b), source.count("\n", 0, figure.start) + 1,
                   source.count("\n", 0, start) + 1, hashlib.sha256(source.encode("utf-8")).hexdigest())


def extract_file(path: Path, label: str) -> Caption:
    raw = path.read_bytes()
    result = extract_caption(raw.decode("utf-8-sig"), label)
    result.source_sha256 = hashlib.sha256(raw).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--format", choices=("json", "latex"), default="json")
    args = parser.parse_args()
    try:
        result = extract_file(args.source, args.label)
    except (OSError, UnicodeError, CaptionError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(result.caption_latex if args.format == "latex" else json.dumps(
        {"status": "EXTRACTED_NOT_TEX_EXPANDED", **asdict(result)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
