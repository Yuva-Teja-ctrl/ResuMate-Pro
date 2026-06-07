"""Job routes: create/list/get/delete job postings (scoped to the recruiter)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.schemas import JobCreate, JobOut
from app.services.ai.embeddings import serialize
from app.services.matching import embed_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Pre-compute and store the JD embedding so matching is fast later.
    embedding = serialize(embed_job(payload.description))
    job = Job(
        title=payload.title,
        description=payload.description,
        required_skills=payload.required_skills,
        shortlist_count=payload.shortlist_count,
        education_pref=payload.education_pref,
        min_experience=payload.min_experience,
        certifications=payload.certifications,
        embedding=embedding,
        owner_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Job)
        .filter(Job.owner_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )


def _get_owned_job(job_id: int, db: Session, user: User) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.owner_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_job(job_id, db, current_user)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(job_id, db, current_user)
    db.delete(job)
    db.commit()
