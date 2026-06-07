"""Job posting model. Holds the job description and its embedding."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # Job Role
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- Recruiter filters / preferences (mirror the Streamlit app) ----
    required_skills: Mapped[str] = mapped_column(Text, default="")     # comma-separated
    shortlist_count: Mapped[int] = mapped_column(Integer, default=3)   # Shortlist Top N
    education_pref: Mapped[str] = mapped_column(String(255), default="")   # optional
    min_experience: Mapped[str] = mapped_column(String(64), default="")    # optional (years)
    certifications: Mapped[str] = mapped_column(String(512), default="")   # optional

    # Embedding stored as JSON text for portability across SQLite/Postgres.
    # In production this can be swapped for a pgvector column (see README).
    embedding: Mapped[str] = mapped_column(Text, nullable=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    owner: Mapped["User"] = relationship(back_populates="jobs")  # noqa: F821
    candidates: Mapped[list["Candidate"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )
