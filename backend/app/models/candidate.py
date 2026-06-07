"""Candidate model. A parsed resume linked to a job, with match score."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)

    # ---- Parsed resume fields ----
    name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    skills: Mapped[str] = mapped_column(Text, default="")          # JSON list
    raw_text: Mapped[str] = mapped_column(Text, default="")        # full resume text
    embedding: Mapped[str] = mapped_column(Text, nullable=True)    # JSON float list

    # ---- Extracted profile (mirror the Streamlit app) ----
    experience_years: Mapped[str] = mapped_column(String(64), default="N/A")
    education_degree: Mapped[str] = mapped_column(String(255), default="N/A")
    education_institution: Mapped[str] = mapped_column(String(255), default="N/A")
    education_year: Mapped[str] = mapped_column(String(32), default="N/A")
    certifications: Mapped[str] = mapped_column(Text, default="")  # JSON list
    strengths: Mapped[str] = mapped_column(Text, default="")
    weaknesses: Mapped[str] = mapped_column(Text, default="")
    education_match: Mapped[str] = mapped_column(String(64), default="N/A")
    certification_match: Mapped[str] = mapped_column(String(64), default="N/A")

    # ---- Match results ----
    score: Mapped[float] = mapped_column(Float, default=0.0)       # 0..100
    matched_skills: Mapped[str] = mapped_column(Text, default="")  # JSON list
    missing_skills: Mapped[str] = mapped_column(Text, default="")  # JSON list

    # ---- Weighted score breakdown (sub-scores total the final score) ----
    skills_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, default=0.0)
    certification_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    job: Mapped["Job"] = relationship(back_populates="candidates")  # noqa: F821
