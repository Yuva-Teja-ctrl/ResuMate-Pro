"""
Resume parsing service.

Turns an uploaded PDF (bytes) into structured candidate data:
    raw_text, name, email, phone, skills

PDF text extraction uses pypdf. Field extraction is delegated to the active
AI provider (local heuristics by default, OpenAI if configured).
"""
from __future__ import annotations

import io
import re
from typing import Dict

from pypdf import PdfReader

from app.services.ai.provider import get_provider

# Strip NUL and other C0/C1 control characters (except tab/newline/carriage
# return). PostgreSQL rejects NUL (0x00) bytes in text columns, so failing to
# clean extracted PDF text causes the INSERT to throw a 500 -- only on Postgres,
# not SQLite, which is why it slips past local tests.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    """Remove control characters that would break a DB insert; keep Unicode."""
    if not text:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub("", str(text))
    # Collapse runs of spaces introduced by stripping.
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF byte stream (may raise on bad PDFs)."""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def parse_resume(file_bytes: bytes, content_type: str = "") -> Dict:
    """
    Parse a resume file into structured fields.

    Robust by design: a malformed, encrypted, or image-only PDF must never
    crash the request. We try PDF extraction first; for genuine PDFs that yield
    no text we leave ``raw_text`` empty (so the caller can return a friendly
    "couldn't read this file" message). For non-PDF uploads we decode the bytes
    as plain text. All extracted text is sanitized so it is safe to store.
    """
    is_pdf = "pdf" in (content_type or "").lower() or file_bytes[:5] == b"%PDF-"

    raw_text = ""
    # 1) Try to read it as a PDF.
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except Exception:
        raw_text = ""

    # 2) For non-PDF uploads, fall back to decoding the bytes as text.
    #    (We deliberately do NOT do this for PDFs, to avoid storing binary junk
    #     when a PDF is encrypted or image-only.)
    if not raw_text and not is_pdf:
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            raw_text = ""

    # 3) Sanitize before any downstream use / storage.
    raw_text = clean_text(raw_text)

    # 4) Extract structured fields (never raises for empty input).
    try:
        fields = get_provider().extract_resume_fields(raw_text)
    except Exception:
        fields = {"name": "", "email": "", "phone": "", "skills": []}

    fields["raw_text"] = raw_text
    return fields
