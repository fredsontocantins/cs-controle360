"""Minimal local FPDF-compatible fallback used by the PDF intelligence export.

This is intentionally small: it only implements the methods used by the
application's PDF fallback renderer.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class FPDF:
    def __init__(self) -> None:
        self.w = 595.28
        self.h = 841.89
        self.l_margin = 28.35
        self.r_margin = 28.35
        self.t_margin = 28.35
        self.b_margin = 28.35
        self._auto_page_break = True
        self._auto_page_break_margin = self.b_margin
        self._font_name = "Helvetica"
        self._font_size = 11
        self._pages: List[List[Tuple[float, float, float, str]]] = []
        self._cursor_y = self.t_margin
        self._current_page = -1

    def set_auto_page_break(self, auto: bool = True, margin: float = 12) -> None:
        self._auto_page_break = auto
        self._auto_page_break_margin = float(margin)
        self.b_margin = float(margin)

    def add_page(self) -> None:
        self._pages.append([])
        self._current_page += 1
        self._cursor_y = self.t_margin

    def set_font(self, family: str, style: str = "", size: float = 11) -> None:
        self._font_name = family or "Helvetica"
        self._font_size = float(size)

    def ln(self, h: float | None = None) -> None:
        self._cursor_y += float(h if h is not None else self._font_size * 0.6)

    def _ensure_page(self) -> None:
        if self._current_page < 0:
            self.add_page()

    def _wrap_text(self, text: str, width: float) -> List[str]:
        if not text:
            return [""]
        approx_char_width = max(self._font_size * 0.52, 1.0)
        max_chars = max(1, int(width / approx_char_width))
        lines: List[str] = []
        for paragraph in text.splitlines() or [""]:
            if not paragraph:
                lines.append("")
                continue
            start = 0
            while start < len(paragraph):
                chunk = paragraph[start : start + max_chars]
                if len(chunk) == max_chars and start + max_chars < len(paragraph):
                    split_at = chunk.rfind(" ")
                    if split_at > max_chars * 0.5:
                        chunk = chunk[:split_at]
                lines.append(chunk.rstrip())
                start += len(chunk)
                while start < len(paragraph) and paragraph[start] == " ":
                    start += 1
        return lines or [""]

    def multi_cell(self, width: float, height: float, text: str) -> None:
        self._ensure_page()
        usable_width = float(width) if width else self.w - self.l_margin - self.r_margin
        line_height = float(height) if height else self._font_size * 1.2
        lines = self._wrap_text(text, usable_width)

        for line in lines:
            if self._auto_page_break and self._cursor_y + line_height > self.h - self._auto_page_break_margin:
                self.add_page()
            x = self.l_margin
            y = self._cursor_y
            self._pages[self._current_page].append((x, y, self._font_size, line))
            self._cursor_y += line_height

    def _build_page_stream(self, page_items: List[Tuple[float, float, float, str]]) -> bytes:
        commands: List[str] = []
        current_font = None
        for x, y, font_size, text in page_items:
            if current_font != font_size:
                commands.append(f"BT /F1 {font_size:.2f} Tf")
                current_font = font_size
            pdf_y = self.h - y
            commands.append(f"1 0 0 1 {x:.2f} {pdf_y:.2f} Tm ({_escape_pdf_text(text)}) Tj ET")
        stream = "\n".join(commands)
        return stream.encode("latin-1", "replace")

    def output(self, name: str) -> str:
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self._pages:
            self.add_page()

        page_streams = [self._build_page_stream(page) for page in self._pages]
        objects: dict[int, bytes] = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: f"<< /Type /Pages /Kids [{' '.join(f'{4 + i * 2} 0 R' for i in range(len(self._pages)))}] /Count {len(self._pages)} >>".encode("latin-1"),
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        }

        for index, stream in enumerate(page_streams):
            page_obj_num = 4 + index * 2
            content_obj_num = page_obj_num + 1
            objects[page_obj_num] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.w:.2f} {self.h:.2f}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>"
            ).encode("latin-1")
            objects[content_obj_num] = f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"

        buffer = bytearray()
        buffer.extend(b"%PDF-1.4\n")
        offsets: dict[int, int] = {}
        for obj_num in sorted(objects):
            offsets[obj_num] = len(buffer)
            buffer.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
            buffer.extend(objects[obj_num])
            buffer.extend(b"\nendobj\n")

        xref_pos = len(buffer)
        max_obj_num = max(objects)
        buffer.extend(f"xref\n0 {max_obj_num + 1}\n".encode("latin-1"))
        buffer.extend(b"0000000000 65535 f \n")
        for obj_num in range(1, max_obj_num + 1):
            buffer.extend(f"{offsets[obj_num]:010d} 00000 n \n".encode("latin-1"))
        buffer.extend(
            (
                "trailer\n"
                f"<< /Size {max_obj_num + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_pos}\n%%EOF\n"
            ).encode("latin-1")
        )

        path.write_bytes(buffer)
        return str(path)
