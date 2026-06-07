"""
LLM provider abstraction.

Defines a single interface (`AIProvider`) for the two text-generation tasks
the app needs that benefit from an LLM:
    - extracting structured fields from raw resume text
    - generating tailored interview questions

Two implementations are provided:
    - LocalProvider : free, offline, heuristic/regex based. Default.
    - OpenAIProvider: higher quality, used only when AI_PROVIDER=openai and an
                      OPENAI_API_KEY is configured.

A factory (`get_provider`) returns the right one based on settings, so the
rest of the codebase never cares which is active.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, List

from app.core.config import settings

# A compact skill vocabulary used by the local provider to extract skills
# without any external model. Extend freely.
COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "nosql",
    "react", "next.js", "vue", "angular", "node.js", "express", "django",
    "flask", "fastapi", "spring", "spring boot", ".net", "rails",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
    "rabbitmq", "graphql", "rest", "grpc", "docker", "kubernetes", "terraform",
    "aws", "gcp", "azure", "ci/cd", "jenkins", "github actions", "linux",
    "git", "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "scikit-learn", "pandas", "numpy", "data analysis", "tableau", "power bi",
    "spark", "hadoop", "airflow", "html", "css", "tailwind", "sass",
    "agile", "scrum", "microservices", "system design", "pytest", "jest",
]


class AIProvider(ABC):
    @abstractmethod
    def extract_resume_fields(self, text: str) -> Dict:
        """Return {name, email, phone, skills:[...]} from raw resume text."""

    @abstractmethod
    def generate_interview_questions(
        self, job_title: str, job_description: str, candidate_skills: List[str], n: int
    ) -> List[str]:
        """Return a list of tailored interview questions."""


# --------------------------------------------------------------------------- #
# Shared helpers (used by both providers as fallbacks)
# --------------------------------------------------------------------------- #
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")


def _extract_email(text: str) -> str:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else ""


def _extract_phone(text: str) -> str:
    m = _PHONE_RE.search(text)
    return m.group(0).strip() if m else ""


def _extract_name(text: str) -> str:
    """Heuristic: the first non-empty line that looks like a person's name."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip lines that are clearly headings or contact info.
        if _EMAIL_RE.search(line) or _PHONE_RE.search(line):
            continue
        words = line.split()
        if 1 < len(words) <= 4 and all(w[:1].isalpha() for w in words):
            return line
    return ""


def _extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        # Word-boundary-ish match to avoid 'r' matching everything.
        pattern = r"(?<![a-zA-Z])" + re.escape(skill) + r"(?![a-zA-Z])"
        if re.search(pattern, lowered):
            found.append(skill)
    return sorted(set(found))


# Degrees ordered loosely by seniority so we can pick the "highest".
_DEGREE_PATTERNS = [
    ("PhD", r"\b(ph\.?\s?d|doctorate)\b"),
    ("MBA", r"\bm\.?b\.?a\b"),
    ("M.Tech", r"\bm\.?\s?tech\b"),
    ("M.E.", r"\bm\.?\s?e\b"),
    ("M.Sc", r"\bm\.?\s?sc\b"),
    ("MCA", r"\bm\.?c\.?a\b"),
    ("M.Com", r"\bm\.?\s?com\b"),
    ("Master", r"\bmaster(?:'s)?\b"),
    ("B.Tech", r"\bb\.?\s?tech\b"),
    ("B.E.", r"\bb\.?\s?e\b"),
    ("B.Sc", r"\bb\.?\s?sc\b"),
    ("BCA", r"\bb\.?c\.?a\b"),
    ("B.Com", r"\bb\.?\s?com\b"),
    ("Bachelor", r"\bbachelor(?:'s)?\b"),
]

_CERT_KEYWORDS = [
    "aws certified", "azure", "google cloud", "gcp certified", "pmp",
    "scrum master", "csm", "cissp", "ccna", "ckad", "cka", "oracle certified",
    "tensorflow developer", "comptia", "itil", "six sigma", "salesforce certified",
]


def _extract_experience_years(text: str) -> str:
    """Find the largest 'N years' figure mentioned in the resume."""
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:years|yrs|year)\b", text.lower())
    nums = [int(m) for m in matches if m.isdigit()]
    if nums:
        return f"{max(nums)} years"
    return "N/A"


def _extract_education(text: str) -> Dict[str, str]:
    lowered = text.lower()
    degree = "N/A"
    for label, pattern in _DEGREE_PATTERNS:
        if re.search(pattern, lowered):
            degree = label
            break

    institution = "N/A"
    for line in text.splitlines():
        if re.search(r"\b(university|institute|college|school of)\b", line, re.I):
            institution = line.strip()[:120]
            break

    years = re.findall(r"\b((?:19|20)\d{2})\b", text)
    year = max(years) if years else "N/A"

    return {"highest_degree": degree, "institution": institution, "graduation_year": year}


def _extract_certifications(text: str) -> List[str]:
    lowered = text.lower()
    found = [c.title() for c in _CERT_KEYWORDS if c in lowered]
    return sorted(set(found))


# --------------------------------------------------------------------------- #
# Local (free, offline) provider
# --------------------------------------------------------------------------- #
class LocalProvider(AIProvider):
    def extract_resume_fields(self, text: str) -> Dict:
        return {
            "name": _extract_name(text),
            "email": _extract_email(text),
            "phone": _extract_phone(text),
            "skills": _extract_skills(text),
            "experience_years": _extract_experience_years(text),
            "education": _extract_education(text),
            "certifications": _extract_certifications(text),
        }

    def generate_interview_questions(
        self, job_title: str, job_description: str, candidate_skills: List[str], n: int
    ) -> List[str]:
        """Template-driven questions grounded in the candidate's real skills."""
        questions: List[str] = []
        title = job_title or "this role"

        templates = [
            "Walk me through a challenging project where you used {skill}.",
            "How do you approach debugging issues in a {skill} codebase?",
            "What trade-offs have you faced when working with {skill}?",
            "Describe a time {skill} helped you improve performance or quality.",
            "How would you mentor a junior engineer who is new to {skill}?",
        ]
        for i, skill in enumerate(candidate_skills[:n]):
            questions.append(templates[i % len(templates)].format(skill=skill))

        # Fill remaining slots with role-level behavioural questions.
        generic = [
            f"Why are you interested in {title}?",
            "Tell me about a time you disagreed with a teammate and how you resolved it.",
            "Describe a production incident you helped resolve.",
            "How do you keep your technical skills current?",
            "What does a well-designed system look like to you?",
        ]
        gi = 0
        while len(questions) < n and gi < len(generic):
            questions.append(generic[gi])
            gi += 1
        return questions[:n]


# --------------------------------------------------------------------------- #
# OpenAI provider (used only when configured)
# --------------------------------------------------------------------------- #
class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def extract_resume_fields(self, text: str) -> Dict:
        prompt = (
            "Extract the following from the resume below and respond ONLY with "
            "JSON in exactly this shape: "
            '{"name":"","email":"","phone":"","skills":[],'
            '"experience_years":"X years",'
            '"education":{"highest_degree":"","institution":"","graduation_year":""},'
            '"certifications":[]}.\n\nResume:\n'
            + text[:6000]
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content)
            # Backfill any missing keys with local heuristics so callers always
            # get a complete profile.
            local = LocalProvider().extract_resume_fields(text)
            for key, default in local.items():
                data.setdefault(key, default)
            return data
        except Exception:
            # Never fail the request because of the LLM; fall back to heuristics.
            return LocalProvider().extract_resume_fields(text)

    def generate_interview_questions(
        self, job_title: str, job_description: str, candidate_skills: List[str], n: int
    ) -> List[str]:
        prompt = (
            f"Generate {n} concise, specific interview questions for a "
            f"'{job_title}' role. Tailor them to these candidate skills: "
            f"{', '.join(candidate_skills) or 'general software engineering'}. "
            f"Job description:\n{job_description[:3000]}\n\n"
            "Respond as a JSON array of strings."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            questions = json.loads(resp.choices[0].message.content)
            if isinstance(questions, dict):  # tolerate {"questions": [...]}
                questions = next(iter(questions.values()))
            return [str(q) for q in questions][:n]
        except Exception:
            return LocalProvider().generate_interview_questions(
                job_title, job_description, candidate_skills, n
            )


def get_provider() -> AIProvider:
    """Factory: pick provider based on settings, with safe fallback to local."""
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        try:
            return OpenAIProvider()
        except Exception:
            return LocalProvider()
    return LocalProvider()
