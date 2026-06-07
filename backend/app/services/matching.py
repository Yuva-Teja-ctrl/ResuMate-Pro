"""
Matching & scoring service.

Mirrors the scoring model of the original ResuMate Streamlit app, but works
with the free local provider as well as a hosted LLM.

Dynamic weighting (`get_weights`): the weight given to Skills / Experience /
Education / Certifications shifts depending on which optional preferences the
recruiter set, always totaling 100. The final score is the sum of four
sub-scores, which makes it both accurate and fully explainable.

    no preferences set   -> Skills 100
    one preference set   -> Skills 60,  that preference 40
    two preferences set  -> Skills 40,  each preference 30
    all three set        -> Skills 40,  each preference 20
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from app.services.ai.embeddings import cosine_similarity, embed_text
from app.services.ai.provider import _extract_skills


def get_weights(
    min_experience: str, education_pref: str, certifications: str
) -> Tuple[int, int, int, int]:
    """Return (skills, experience, education, certification) weights summing to 100."""
    n = sum([bool(min_experience), bool(education_pref), bool(certifications)])
    if n == 0:
        return 100, 0, 0, 0
    if n == 1:
        return (
            60,
            40 if min_experience else 0,
            40 if education_pref else 0,
            40 if certifications else 0,
        )
    if n == 2:
        return (
            40,
            30 if min_experience else 0,
            30 if education_pref else 0,
            30 if certifications else 0,
        )
    return 40, 20, 20, 20


def _parse_skill_list(raw: str) -> List[str]:
    """Split a comma/line separated skills string into a clean lowercase list."""
    if not raw:
        return []
    parts = re.split(r"[,;/\n]", raw)
    return sorted({p.strip().lower() for p in parts if p.strip()})


def _first_int(text: str) -> int:
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else 0


def _match_label(fraction: float) -> str:
    if fraction >= 0.7:
        return "Good Match"
    if fraction > 0:
        return "Partial Match"
    return "None Found"


def compute_match(
    *,
    job_description: str,
    job_embedding: List[float],
    required_skills: str,
    resume_text: str,
    resume_embedding: List[float],
    profile: Dict,
    min_experience: str = "",
    education_pref: str = "",
    certifications: str = "",
) -> Dict:
    """Return the full weighted scoring result for one candidate."""
    w_skills, w_exp, w_edu, w_cert = get_weights(
        min_experience, education_pref, certifications
    )

    # ---- Skills ----
    # Prefer the recruiter's explicit required-skills list; fall back to skills
    # mentioned in the job description.
    required = _parse_skill_list(required_skills) or _extract_skills(job_description)
    required_set = set(required)
    have = {s.lower() for s in profile.get("skills", [])}
    matched = sorted(required_set & have)
    missing = sorted(required_set - have)
    skill_overlap = (len(matched) / len(required_set)) if required_set else 0.0

    # Blend keyword overlap with semantic similarity (meaning, not just words).
    semantic = max(0.0, cosine_similarity(job_embedding, resume_embedding))
    skills_fraction = (
        0.6 * skill_overlap + 0.4 * semantic if required_set else semantic
    )
    skills_score = round(skills_fraction * w_skills, 1)

    # ---- Experience ----
    experience_score = 0.0
    if w_exp:
        need = _first_int(min_experience)
        have_exp = _first_int(profile.get("experience_years", ""))
        if need <= 0:
            frac = 1.0
        elif have_exp >= need:
            frac = 1.0
        else:
            frac = have_exp / need
        experience_score = round(frac * w_exp, 1)

    # ---- Education ----
    education_score = 0.0
    education_match = "N/A"
    if w_edu:
        edu = profile.get("education", {}) or {}
        haystack = " ".join(
            [
                str(edu.get("highest_degree", "")),
                str(edu.get("institution", "")),
                resume_text,
            ]
        ).lower()
        tokens = [t for t in re.split(r"[,\s]+", education_pref.lower()) if t]
        hits = sum(1 for t in tokens if t in haystack)
        frac = (hits / len(tokens)) if tokens else 0.0
        education_score = round(frac * w_edu, 1)
        education_match = _match_label(frac)

    # ---- Certifications ----
    certification_score = 0.0
    certification_match = "N/A"
    if w_cert:
        pref = _parse_skill_list(certifications)
        cand_certs = {c.lower() for c in profile.get("certifications", [])}
        text_lower = resume_text.lower()
        hits = sum(
            1
            for p in pref
            if any(p in c for c in cand_certs) or p in text_lower
        )
        frac = (hits / len(pref)) if pref else 0.0
        certification_score = round(frac * w_cert, 1)
        certification_match = _match_label(frac)

    total = skills_score + experience_score + education_score + certification_score
    score = max(0.0, min(100.0, round(total, 1)))

    strengths, weaknesses = _summarize(matched, missing, profile, min_experience)

    return {
        "score": score,
        "skills_score": skills_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "certification_score": certification_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "education_match": education_match,
        "certification_match": certification_match,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def _summarize(
    matched: List[str], missing: List[str], profile: Dict, min_experience: str
) -> Tuple[str, str]:
    """Generate a short strengths/gaps summary from the structured data."""
    strengths_parts = []
    if matched:
        strengths_parts.append(
            "Strong on " + ", ".join(matched[:4]) + "."
        )
    exp = profile.get("experience_years", "N/A")
    if exp and exp != "N/A":
        strengths_parts.append(f"Has {exp} of experience.")
    if profile.get("certifications"):
        strengths_parts.append(
            "Holds " + ", ".join(profile["certifications"][:3]) + "."
        )
    strengths = " ".join(strengths_parts) or "No standout strengths detected."

    weaknesses_parts = []
    if missing:
        weaknesses_parts.append("Missing " + ", ".join(missing[:4]) + ".")
    if min_experience and _first_int(profile.get("experience_years", "")) < _first_int(
        min_experience
    ):
        weaknesses_parts.append("Below the preferred experience level.")
    weaknesses = " ".join(weaknesses_parts) or "No major gaps detected."

    return strengths, weaknesses


def embed_job(job_description: str) -> List[float]:
    return embed_text(job_description)


def embed_resume(resume_text: str) -> List[float]:
    return embed_text(resume_text)


def rank_candidates(candidates: List[Dict]) -> List[Dict]:
    """Sort candidates by score descending (highest fit first)."""
    return sorted(candidates, key=lambda c: c.get("score", 0.0), reverse=True)
