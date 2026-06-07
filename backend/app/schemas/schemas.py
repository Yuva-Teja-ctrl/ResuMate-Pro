"""Pydantic schemas: the request/response contracts for the API."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---- Jobs ----
class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: str = ""
    shortlist_count: int = Field(default=3, ge=1, le=100)
    education_pref: str = ""
    min_experience: str = ""
    certifications: str = ""


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    required_skills: str
    shortlist_count: int
    education_pref: str
    min_experience: str
    certifications: str
    created_at: datetime


# ---- Candidates ----
class Education(BaseModel):
    highest_degree: str = "N/A"
    institution: str = "N/A"
    graduation_year: str = "N/A"


class ScoreBreakdown(BaseModel):
    skills_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    certification_score: float = 0.0


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    name: str
    email: str
    phone: str
    skills: List[str] = []
    score: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    experience_years: str = "N/A"
    education: Education = Education()
    certifications: List[str] = []
    strengths: str = ""
    weaknesses: str = ""
    education_match: str = "N/A"
    certification_match: str = "N/A"
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    shortlisted: bool = False
    created_at: datetime


# ---- Interview ----
class InterviewRequest(BaseModel):
    num_questions: int = 5


class InterviewResponse(BaseModel):
    candidate_id: int
    questions: List[str]
