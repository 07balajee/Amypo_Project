"""Deterministic writers: markdown, PDF, DOCX, CSV, JSONL. Same seed -> byte-identical files.

The PDF writer is a minimal hand-rolled one (Helvetica, text only) so generating PDFs needs no extra
dependency; pdfplumber reads it back like any other PDF. DOCX files are re-zipped with fixed
timestamps because python-docx stamps the current time into both the zip and the core properties.
"""
from __future__ import annotations

import csv
import io
import json
import textwrap
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.synth.content import Block

FIXED_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def render_markdown(blocks: list[Block]) -> str:
    out: list[str] = []
    for kind, text in blocks:
        if kind == "h1":
            out += [f"# {text}", ""]
        elif kind == "h2":
            out += [f"## {text}", ""]
        elif kind == "h3":
            out += [f"### {text}", ""]
        elif kind == "li":
            out.append(f"- {text}")
        else:
            if out and out[-1].startswith("- "):
                out.append("")
            out += [text, ""]
    if out and out[-1].startswith("- "):
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_markdown(path: Path, blocks: list[Block]) -> None:
    path.write_text(render_markdown(blocks), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- PDF

_PAGE_W, _PAGE_H, _MARGIN = 612, 792, 56
_BODY_SIZE, _LEADING, _WRAP = 10, 14, 92


def _pdf_escape(text: str) -> str:
    text = text.encode("ascii", "replace").decode("ascii")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_lines(blocks: list[Block]) -> list[tuple[str, str]]:
    """-> [(font, text)] with wrapping; blank entries separate paragraphs."""
    lines: list[tuple[str, str]] = []
    for kind, text in blocks:
        if kind in ("h1", "h2", "h3"):
            if lines:
                lines.append(("F1", ""))
            lines.append(("F2", text))
        elif kind == "li":
            wrapped = textwrap.wrap(text, _WRAP - 2) or [""]
            lines.append(("F1", f"- {wrapped[0]}"))
            lines += [("F1", f"  {w}") for w in wrapped[1:]]
        else:
            lines += [("F1", w) for w in textwrap.wrap(text, _WRAP)]
    return lines


def write_pdf(path: Path, blocks: list[Block]) -> None:
    lines = _pdf_lines(blocks)
    per_page = (_PAGE_H - 2 * _MARGIN) // _LEADING
    pages = [lines[i : i + per_page] for i in range(0, len(lines), per_page)] or [[]]

    objects: list[bytes] = []  # object n is objects[n-1]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")  # pages tree, filled in below
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for page in pages:
        ops = [f"BT {_LEADING} TL {_MARGIN} {_PAGE_H - _MARGIN} Td"]
        for font, text in page:
            size = _BODY_SIZE + 2 if font == "F2" else _BODY_SIZE
            ops.append(f"/{font} {size} Tf ({_pdf_escape(text)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_id = len(objects)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        page_ids.append(len(objects))
    kids = " ".join(f"{i} 0 R" for i in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(b"%d 0 obj\n" % n + body + b"\nendobj\n")
    xref = buf.tell()
    buf.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        buf.write(b"%010d 00000 n \n" % off)
    buf.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    path.write_bytes(buf.getvalue())


# ---------------------------------------------------------------- DOCX

def write_docx(path: Path, blocks: list[Block]) -> None:
    import docx  # python-docx

    document = docx.Document()
    props = document.core_properties
    props.author = "AMYPO synthetic data generator"
    props.created = props.modified = FIXED_TIME
    props.last_modified_by = "gen_synthetic"
    props.revision = 1
    for kind, text in blocks:
        if kind == "h1":
            document.add_heading(text, level=0)
        elif kind == "h2":
            document.add_heading(text, level=1)
        elif kind == "h3":
            document.add_heading(text, level=2)
        elif kind == "li":
            document.add_paragraph(text, style="List Bullet")
        else:
            document.add_paragraph(text)
    raw = io.BytesIO()
    document.save(raw)

    # Re-zip with a fixed timestamp so the file is reproducible.
    out = io.BytesIO()
    with zipfile.ZipFile(raw) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            fixed = zipfile.ZipInfo(info.filename, date_time=FIXED_TIME.timetuple()[:6])
            fixed.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(fixed, src.read(info.filename))
    path.write_bytes(out.getvalue())


# ---------------------------------------------------------------- tabular

def write_csv(path: Path, columns: tuple[str, ...] | list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(columns), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: "" if r[c] is None else r[c] for c in columns})


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
