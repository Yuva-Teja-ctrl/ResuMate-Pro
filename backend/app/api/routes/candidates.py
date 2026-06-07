"""
Candidate routes: the core workflow.

    POST /api/jobs/{job_id}/candidates        -> upload + parse + match a resume
    GET  /api/jobs/{job_id}/candidates        -> list candidates ranked by score
    POST /api/candidates/{id}/interview       -> generate interview questions
    DELETE /api/candidates/{id}               -> remove a candidate
"""
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.schemas.schemas import CandidateOut, InterviewRequest, InterviewResponse
from app.services.ai.embeddings import deserialize, serialize
from app.services.interview import generate_questions
from app.services.matching import compute_match, embed_resume
from app.services.resume_parser import parse_resume

router = APIRouter(tags=["candidates"])


def _owned_job(job_id: int, db: Session, user: User) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.owner_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _owned_candidate(candidate_id: int, db: Session, user: User) -> Candidate:
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == candidate_id, Job.owner_id == user.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def _to_out(c: Candidate, shortlisted: bool = False) -> CandidateOut:
    """Deserialize JSON list columns into real lists for the response model."""
    return CandidateOut(
        id=c.id,
        job_id=c.job_id,
        name=c.name,
        email=c.email,
        phone=c.phone,
        skills=json.loads(c.skills or "[]"),
        score=c.score,
        matched_skills=json.loads(c.matched_skills or "[]"),
        missing_skills=json.loads(c.missing_skills or "[]"),
        experience_years=c.experience_years,
        education={
            "highest_degree": c.education_degree,
            "institution": c.education_institution,
            "graduation_year": c.education_year,
        },
        certifications=json.loads(c.certifications or "[]"),
        strengths=c.strengths,
        weaknesses=c.weaknesses,
        education_match=c.education_match,
        certification_match=c.certification_match,
        score_breakdown={
            "skills_score": c.skills_score,
            "experience_score": c.experience_score,
            "education_score": c.education_score,
            "certification_score": c.certification_score,
        },
        shortlisted=shortlisted,
        created_at=c.created_at,
    )


@router.post("/api/jobs/{job_id}/candidates", response_model=CandidateOut, status_code=201)
async def upload_candidate(
    job_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _owned_job(job_id, db, current_user)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        # 1) Parse the resume into a structured profile.
        profile = parse_resume(file_bytes, file.content_type or "")
        resume_text = profile.get("raw_text", "")

        # A scanned/image-only or encrypted PDF yields no extractable text.
        if not resume_text.strip():
            raise HTTPException(
                status_code=422,
                detail="Could not extract any text from this file. It may be "
                "a scanned/image-only or password-protected PDF. Please upload "
                "a text-based PDF.",
            )

        skills = profile.get("skills", [])
        education = profile.get("education", {}) or {}
        certifications = profile.get("certifications", [])

        # 2) Embed the resume and score it against the job using the recruiter's
        #    filters (required skills + optional experience/education/cert prefs).
        resume_embedding = embed_resume(resume_text)
        match = compute_match(
            job_description=job.description,
            job_embedding=deserialize(job.embedding),
            required_skills=job.required_skills,
            resume_text=resume_text,
            resume_embedding=resume_embedding,
            profile=profile,
            min_experience=job.min_experience,
            education_pref=job.education_pref,
            certifications=job.certifications,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Convert any unexpected failure into a proper HTTP error so the
        # response still carries CORS headers (otherwise the browser just
        # reports a generic "Load failed").
        raise HTTPException(
            status_code=500, detail=f"Failed to process resume: {exc}"
        ) from exc

    # 3) Persist everything.
    candidate = Candidate(
        job_id=job.id,
        name=profile.get("name", ""),
        email=profile.get("email", ""),
        phone=profile.get("phone", ""),
        skills=json.dumps(skills),
        raw_text=resume_text,
        embedding=serialize(resume_embedding),
        experience_years=profile.get("experience_years", "N/A"),
        education_degree=education.get("highest_degree", "N/A"),
        education_institution=education.get("institution", "N/A"),
        education_year=education.get("graduation_year", "N/A"),
        certifications=json.dumps(certifications),
        strengths=match["strengths"],
        weaknesses=match["weaknesses"],
        education_match=match["education_match"],
        certification_match=match["certification_match"],
        score=match["score"],
        matched_skills=json.dumps(match["matched_skills"]),
        missing_skills=json.dumps(match["missing_skills"]),
        skills_score=match["skills_score"],
        experience_score=match["experience_score"],
        education_score=match["education_score"],
        certification_score=match["certification_score"],
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return _to_out(candidate)


@router.get("/api/jobs/{job_id}/candidates", response_model=list[CandidateOut])
def list_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _owned_job(job_id, db, current_user)
    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_id == job_id)
        .order_by(Candidate.score.desc())  # ranking: best fit first
        .all()
    )
    # Mark the top N (the job's shortlist_count) as shortlisted.
    return [
        _to_out(c, shortlisted=(i < job.shortlist_count))
        for i, c in enumerate(candidates)
    ]


@router.post("/api/candidates/{candidate_id}/interview", response_model=InterviewResponse)
def candidate_interview(
    candidate_id: int,
    payload: InterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _owned_candidate(candidate_id, db, current_user)
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    questions = generate_questions(
        job_title=job.title,
        job_description=job.description,
        candidate_skills=json.loads(candidate.skills or "[]"),
        n=payload.num_questions,
    )
    return InterviewResponse(candidate_id=candidate.id, questions=questions)


@router.delete("/api/candidates/{candidate_id}", status_code=204)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _owned_candidate(candidate_id, db, current_user)
    db.delete(candidate)
    db.commit()
