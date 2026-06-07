"""
Interview question generation service.

Thin wrapper over the active AI provider so the API layer stays clean.
"""
from __future__ import annotations

from typing import List

from app.services.ai.provider import get_provider


def generate_questions(
    job_title: str,
    job_description: str,
    candidate_skills: List[str],
    n: int = 5,
) -> List[str]:
    n = max(1, min(n, 15))  # keep request sizes sane
    return get_provider().generate_interview_questions(
        job_title, job_description, candidate_skills, n
    )
