"""Remove personal metadata from editable Visio and exported PDF figures."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


CORE_TAGS = {
    "{http://purl.org/dc/elements/1.1/}creator",
    "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy",
}
APP_LOCAL_NAMES = {"Company", "Manager", "HyperlinkBase"}
VSDX_TEXT_SUFFIXES = {".xml", ".rels", ".txt"}
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/][^\s<>'\"]+"),
    re.compile(r"(?i)file:/+[^\s<>'\"]+"),
    re.compile(r"\\\\[A-Za-z0-9._-]+\\[^\s<>'\"]+"),
    re.compile(r"(?i)/(?:Users|home)/[^\s<>'\"]+"),
)


def run_qpdf(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # qpdf exit code 3 means the requested operation succeeded with warnings.
    if completed.returncode not in {0, 3}:
        raise RuntimeError(completed.stderr.strip() or f"qpdf failed with {completed.returncode}")
    return completed


def sanitize_vsdx(path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        rebuilt = Path(tmp_name) / path.name
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            rebuilt, "w", compression=zipfile.ZIP_DEFLATED
        ) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename in {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}:
                    root = ET.fromstring(data)
                    for element in root.iter():
                        local_name = element.tag.rsplit("}", 1)[-1]
                        if (
                            element.tag in CORE_TAGS
                            or local_name in APP_LOCAL_NAMES
                            or info.filename == "docProps/custom.xml"
                        ):
                            element.text = ""
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                target.writestr(info, data)
        shutil.copy2(rebuilt, path)


def sanitize_pdf(path: Path, qpdf: Path) -> None:
    exported = run_qpdf([str(qpdf), "--json=2", "--json-output", str(path)])
    payload = json.loads(exported.stdout)
    objects = payload.get("qpdf", [{}, {}])[1]
    for wrapper in objects.values():
        obj = wrapper.get("value", {}) if isinstance(wrapper, dict) else {}
        if not isinstance(obj, dict):
            continue
        if "/Author" not in obj:
            continue
        for key in ("/Author", "/Creator", "/Producer", "/Subject", "/Keywords"):
            if key in obj:
                obj[key] = "u:"
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        patch_path = tmp / "metadata.json"
        output_path = tmp / path.name
        patch_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        run_qpdf([str(qpdf), str(path), f"--update-from-json={patch_path}", str(output_path)])
        shutil.copy2(output_path, path)

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        output_path = tmp / path.name
        compact_path = tmp / ("compact-" + path.name)
        reader = PdfReader(path)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer.root_object.pop(NameObject("/Metadata"), None)
        writer.metadata = {
            "/Title": "",
            "/Author": "",
            "/Subject": "",
            "/Creator": "",
            "/Producer": "",
            "/Keywords": "",
        }
        with output_path.open("wb") as stream:
            writer.write(stream)
        run_qpdf([str(qpdf), str(output_path), "--object-streams=generate", str(compact_path)])
        shutil.copy2(compact_path, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_vsdx_metadata(path: Path) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        for member in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
            if member not in archive.namelist():
                continue
            root = ET.fromstring(archive.read(member))
            for element in root.iter():
                local_name = element.tag.rsplit("}", 1)[-1]
                if (
                    element.tag in CORE_TAGS
                    or local_name in APP_LOCAL_NAMES
                    or member == "docProps/custom.xml"
                ) and (
                    element.text or ""
                ).strip():
                    findings.append(f"{member}:{local_name}")
        for member in archive.namelist():
            if Path(member).suffix.lower() not in VSDX_TEXT_SUFFIXES:
                continue
            raw = archive.read(member)
            text = raw.decode("utf-8", errors="ignore")
            if not text and raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = raw.decode("utf-16", errors="ignore")
            for pattern in ABSOLUTE_PATH_PATTERNS:
                match = pattern.search(text)
                if match:
                    findings.append(f"{member}:absolute-path:{match.group(0)[:120]}")
                    break
    return findings


def iter_pdf_content_bytes(page: object) -> list[bytes]:
    streams: list[bytes] = []
    seen: set[int] = set()

    def visit_stream(stream: object, resources: object | None = None) -> None:
        try:
            resolved = stream.get_object() if hasattr(stream, "get_object") else stream
            identity = id(resolved)
            if identity in seen:
                return
            seen.add(identity)
            if hasattr(resolved, "get_data"):
                streams.append(resolved.get_data())
            stream_resources = resolved.get("/Resources", resources) if hasattr(resolved, "get") else resources
            if stream_resources is not None and hasattr(stream_resources, "get_object"):
                stream_resources = stream_resources.get_object()
            xobjects = stream_resources.get("/XObject", {}) if hasattr(stream_resources, "get") else {}
            if hasattr(xobjects, "get_object"):
                xobjects = xobjects.get_object()
            if hasattr(xobjects, "values"):
                for child in xobjects.values():
                    visit_stream(child, stream_resources)
        except Exception:
            return

    contents = page.get_contents() if hasattr(page, "get_contents") else None
    if contents is not None:
        visit_stream(contents, page.get("/Resources") if hasattr(page, "get") else None)
    return streams


def extract_pdf_rgb_palette(path: Path, operator: bytes) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pattern = re.compile(
        rb"(?<![0-9.])([01](?:\.[0-9]+)?)\s+([01](?:\.[0-9]+)?)\s+"
        rb"([01](?:\.[0-9]+)?)\s+" + operator + rb"\b"
    )
    palette: list[str] = []
    for page in reader.pages:
        for data in iter_pdf_content_bytes(page):
            for match in pattern.findall(data):
                rgb = tuple(float(component) for component in match)
                if max(rgb) < 0.08 or min(rgb) > 0.94 or max(rgb) - min(rgb) < 0.04:
                    continue
                color = "#" + "".join(f"{round(component * 255):02X}" for component in rgb)
                if color not in palette:
                    palette.append(color)
    return palette


def extract_pdf_fonts(reader: object) -> list[str]:
    fonts: list[str] = []
    for page in getattr(reader, "pages", []):
        resources = page.get("/Resources", {})
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        font_map = resources.get("/Font", {}) if hasattr(resources, "get") else {}
        if hasattr(font_map, "get_object"):
            font_map = font_map.get_object()
        if not hasattr(font_map, "values"):
            continue
        for font in font_map.values():
            try:
                resolved = font.get_object() if hasattr(font, "get_object") else font
                name = str(resolved.get("/BaseFont", "")).lstrip("/")
                name = re.sub(r"^[A-Z]{6}\+", "", name)
                if name and name not in fonts:
                    fonts.append(name)
            except Exception:
                continue
    return fonts


def inspect_pdf_metadata(
    path: Path,
) -> tuple[list[str], bool, float, float, list[str], list[str], list[str]]:
    from pypdf import PdfReader
    from pypdf.generic import NameObject

    reader = PdfReader(path)
    findings: list[str] = []
    metadata = reader.metadata or {}
    for key in ("/Author", "/Creator", "/Subject", "/Keywords"):
        if str(metadata.get(key, "") or "").strip():
            findings.append(f"Info:{key}")
    if NameObject("/Metadata") in reader.trailer["/Root"]:
        findings.append("XMP:/Metadata")
    if not reader.pages:
        return findings, False, 0.0, 0.0, [], [], []
    media_box = reader.pages[0].mediabox
    return (
        findings,
        True,
        float(media_box.width),
        float(media_box.height),
        extract_pdf_rgb_palette(path, b"(?:sc|rg|scn)"),
        extract_pdf_rgb_palette(path, b"(?:SC|RG|SCN)"),
        extract_pdf_fonts(reader),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanitize VSDX core properties and PDF Info/XMP metadata without rasterizing."
    )
    parser.add_argument("--vsdx", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--qpdf", type=Path, default=Path(shutil.which("qpdf") or "qpdf"))
    args = parser.parse_args()
    if args.vsdx is None and args.pdf is None:
        parser.error("at least one of --vsdx or --pdf is required")
    result: dict[str, object] = {
        "status": "FAILED",
        "metadata_sanitized": False,
        "anonymous_check": False,
        "identity_findings": [],
        "pdf_reopened": False,
    }
    findings: list[str] = []
    if args.vsdx is not None:
        vsdx = args.vsdx.resolve()
        sanitize_vsdx(vsdx)
        findings.extend(inspect_vsdx_metadata(vsdx))
        result.update({"vsdx": str(vsdx), "vsdx_sha256": sha256_file(vsdx)})
    if args.pdf is not None:
        pdf = args.pdf.resolve()
        sanitize_pdf(pdf, args.qpdf.resolve())
        (
            pdf_findings,
            pdf_reopened,
            page_width_pt,
            page_height_pt,
            fill_palette,
            stroke_palette,
            pdf_fonts,
        ) = inspect_pdf_metadata(pdf)
        findings.extend(pdf_findings)
        result.update(
            {
                "pdf": str(pdf),
                "pdf_sha256": sha256_file(pdf),
                "pdf_reopened": pdf_reopened,
                "pdf_page_width_pt": page_width_pt,
                "pdf_page_height_pt": page_height_pt,
                "pdf_fill_palette": fill_palette,
                "pdf_stroke_palette": stroke_palette,
                "pdf_fonts": pdf_fonts,
            }
        )
    result["identity_findings"] = findings
    result["metadata_sanitized"] = True
    result["anonymous_check"] = not findings
    result["status"] = "PASSED" if not findings and (
        args.pdf is None or result["pdf_reopened"] is True
    ) else "FAILED"
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASSED":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
