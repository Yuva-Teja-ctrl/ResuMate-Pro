"""
End-to-end API tests covering the core recruiter workflow.

These run against the local (free) AI provider so CI needs no API keys.
A fresh SQLite file is used per test session and cleaned up afterwards.
"""
import io
import os

import pytest
from fastapi.testclient import TestClient

# Use an isolated test database before importing the app.
os.environ["DATABASE_URL"] = "sqlite:///./test_resumate.db"

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_RESUME = """
Asha Verma
asha.verma@example.com
+91 98765 43210
Skills: Python, FastAPI, PostgreSQL, Docker, AWS, REST, Git
Built microservices in Python and FastAPI deployed on AWS with Docker.
"""

JD = """
Backend Engineer. Required: Python, FastAPI, PostgreSQL, Docker, Kubernetes,
REST, system design. Build scalable microservices and APIs.
"""


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c
    if os.path.exists("./test_resumate.db"):
        os.remove("./test_resumate.db")


@pytest.fixture(scope="module")
def auth_headers(client):
    client.post("/api/auth/register", json={
        "email": "ci@example.com", "password": "secret123", "full_name": "CI"
    })
    resp = client.post("/api/auth/login", json={
        "email": "ci@example.com", "password": "secret123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_requires_auth(client):
    assert client.get("/api/jobs").status_code == 401


def test_full_flow(client, auth_headers):
    # create job WITH filters (required skills + optional preferences)
    r = client.post(
        "/api/jobs",
        json={
            "title": "Backend Engineer",
            "description": JD,
            "required_skills": "Python, FastAPI, PostgreSQL, Docker, Kubernetes",
            "shortlist_count": 2,
            "min_experience": "2",
            "education_pref": "B.Tech",
            "certifications": "AWS Certified",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    job = r.json()
    assert job["required_skills"].startswith("Python")
    assert job["shortlist_count"] == 2
    job_id = job["id"]

    # upload + parse + score
    files = {"file": ("asha.txt", io.BytesIO(SAMPLE_RESUME.encode()), "text/plain")}
    r = client.post(f"/api/jobs/{job_id}/candidates", files=files, headers=auth_headers)
    assert r.status_code == 201
    cand = r.json()
    assert cand["email"] == "asha.verma@example.com"
    assert "python" in cand["skills"]
    assert 0 <= cand["score"] <= 100
    assert "kubernetes" in cand["missing_skills"]

    # weighted breakdown is present and the sub-scores sum to the total
    sb = cand["score_breakdown"]
    total = (
        sb["skills_score"]
        + sb["experience_score"]
        + sb["education_score"]
        + sb["certification_score"]
    )
    assert abs(total - cand["score"]) < 0.5
    # with experience + education + certs set, skills weight caps at 40
    assert sb["skills_score"] <= 40.0

    # ranking + shortlisting (top N flagged)
    r = client.get(f"/api/jobs/{job_id}/candidates", headers=auth_headers)
    assert r.status_code == 200
    listed = r.json()
    assert len(listed) == 1
    assert listed[0]["shortlisted"] is True

    # interview questions
    r = client.post(f"/api/candidates/{cand['id']}/interview",
                    json={"num_questions": 4}, headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 4


def test_weights_no_preferences(client, auth_headers):
    # With no optional preferences, skills carry the full 100 weight.
    r = client.post(
        "/api/jobs",
        json={
            "title": "Dev",
            "description": JD,
            "required_skills": "Python, FastAPI",
            "shortlist_count": 1,
        },
        headers=auth_headers,
    )
    job_id = r.json()["id"]
    files = {"file": ("asha.txt", io.BytesIO(SAMPLE_RESUME.encode()), "text/plain")}
    r = client.post(f"/api/jobs/{job_id}/candidates", files=files, headers=auth_headers)
    cand = r.json()
    sb = cand["score_breakdown"]
    assert sb["experience_score"] == 0.0
    assert sb["education_score"] == 0.0
    assert sb["certification_score"] == 0.0
    assert sb["skills_score"] == cand["score"]
