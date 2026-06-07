"""
Resume parsing service.

Turns an uploaded PDF (bytes) into structured candidate data:
    raw_text, name, email, phone, skills

PDF text extraction uses pypdf. Field extraction is delegated to the active
AI provider (local heuristics by default, OpenAI if configured).
"""
from __future__ import annotations

import io
from typing import Dict

from pypdf import PdfReader

from app.services.ai.provider import get_provider


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF byte stream."""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def parse_resume(file_bytes: bytes, content_type: str = "") -> Dict:
    """
    Parse a resume file into structured fields.

    Currently supports PDF. Plain-text uploads are also accepted as a
    convenience (treated as raw text directly).
    """
    if "pdf" in (content_type or "").lower():
        raw_text = extract_text_from_pdf(file_bytes)
    else:
        # Best-effort: try PDF first, fall back to decoding as text.
        try:
            raw_text = extract_text_from_pdf(file_bytes)
        except Exception:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

    fields = get_provider().extract_resume_fields(raw_text)
    fields["raw_text"] = raw_text
    return fields
