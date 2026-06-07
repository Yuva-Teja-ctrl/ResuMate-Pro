# ResuMate Pro — AI-Based Recruitment Assistant

A production-grade, full-stack rebuild of an AI recruitment assistant. Recruiters
create job postings, upload candidate resumes, and instantly get a **ranked
shortlist** with explainable match scores plus **auto-generated interview
questions** tailored to each candidate.

> This is the engineered evolution of an earlier Streamlit prototype — rebuilt
> with a proper API, database, authentication, a real frontend, containerization,
> and CI so it reflects how a production system is actually structured.

## 🔗 Live Demo

- **App:** _<!-- TODO: paste your Vercel frontend URL here -->_
- **API docs:** _<!-- TODO: paste your Render backend URL + /docs here -->_

> The demo backend runs in **lite mode** (a torch-free embedding backend) so it
> fits comfortably on free hosting tiers. First request after idle may be slow
> while the free instance wakes up.

---

## ✨ Features

- **Resume parsing** — extracts name, email, phone, skills, **experience, education, and certifications** from PDF resumes.
- **Recruiter filters** — set the **required skills**, **shortlist size (Top N)**, and optional **minimum experience**, **education preference**, and **preferred certifications**.
- **Dynamic weighted scoring** — the weight given to Skills / Experience / Education / Certifications shifts based on which preferences are set (always totaling 100), producing an explainable **score breakdown** per candidate.
- **Explainable ranking** — candidates sorted by fit, each showing matched/missing skills, sub-score bars, education & certification match, strengths and gaps.
- **Shortlisting** — the top N candidates are flagged automatically.
- **Result filters** — narrow the ranked list by minimum score, specific skill, or shortlisted-only.
- **Interview question generation** — questions tailored to the role and the candidate's real skills.
- **Multi-tenant auth** — JWT login; each recruiter only sees their own jobs and candidates.
- **Runs free & offline by default** — local `sentence-transformers` embeddings + heuristic extraction, no API key required. Optionally upgrades to OpenAI by setting one env var.

## ⚖️ How scoring works

The recruiter's filters drive a dynamic weighting (mirrors the original ResuMate logic):

| Preferences set | Skills | Experience | Education | Certifications |
|---|---|---|---|---|
| none | 100 | – | – | – |
| one | 60 | 40 (if set) | 40 (if set) | 40 (if set) |
| two | 40 | 30 each (if set) | | |
| all three | 40 | 20 | 20 | 20 |

The **Skills** sub-score blends keyword overlap (against required skills) with **semantic similarity** (embedding cosine), so it captures meaning, not just exact keywords. The final score is the sum of the four sub-scores, capped at 100.

---

## 🏗️ Architecture

```
┌──────────────────┐        HTTPS/JSON        ┌───────────────────────┐
│   Next.js (React)│  ───────────────────────▶│   FastAPI  (Python)   │
│  Tailwind UI     │◀───────────────────────  │   REST API + JWT auth │
│  :3000           │                           │   :8000               │
└──────────────────┘                           └───────────┬───────────┘
                                                            │
                            ┌───────────────────────────────┼───────────────────────────────┐
                            │                                │                               │
                   ┌────────▼────────┐            ┌──────────▼──────────┐         ┌───────────▼──────────┐
                   │  AI Service     │            │  Matching/Ranking   │         │  PostgreSQL          │
                   │  (pluggable)    │            │  cosine sim + skills│         │  (SQLite for dev)    │
                   │  local | openai │            └─────────────────────┘         │  users/jobs/candidates│
                   └─────────────────┘                                            └──────────────────────┘
```

**Key design decisions (and why):**

| Decision | Why |
|---|---|
| Pluggable AI provider (`local` / `openai`) behind one interface | App runs with zero cost/keys, but upgrades to a hosted LLM with one env var. No code changes. |
| Hybrid score (semantic + skill overlap) | Pure keyword match misses meaning; pure embeddings aren't explainable. The blend is both accurate **and** interpretable for recruiters. |
| Embeddings stored as JSON text | Portable across SQLite (dev) and Postgres (prod). Documented upgrade path to native `pgvector`. |
| JWT + per-user row scoping | Real multi-tenancy — handlers only ever query rows owned by the authenticated recruiter. |
| SQLite fallback | Clone-and-run in seconds with no database to install. |

---

## 🧰 Tech Stack

**Backend:** FastAPI · SQLAlchemy · Pydantic · python-jose (JWT) · passlib (bcrypt) · pypdf · sentence-transformers
**Frontend:** Next.js 14 (App Router) · React · TypeScript · Tailwind CSS
**Infra:** Docker · docker-compose · PostgreSQL (pgvector image) · GitHub Actions CI

---

## 🚀 Quick start

### Option A — Docker (whole stack, one command)

```bash
docker compose up --build
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Option B — Run locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # works as-is; no edits required
uvicorn app.main:app --reload # http://localhost:8000/docs
```

**Frontend** (in a second terminal)
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                   # http://localhost:3000
```

---

## 🔌 Using a hosted LLM (optional)

By default the app uses free local models. To use OpenAI for higher-quality
parsing and interview questions, set in `backend/.env`:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

The app falls back to the local provider automatically if a call fails — it
never crashes a request because of the LLM.

---

## 📡 API overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create a recruiter account |
| `POST` | `/api/auth/login` | Get a JWT |
| `POST` | `/api/jobs` | Create a job (embeds the JD) |
| `GET`  | `/api/jobs` | List your jobs |
| `POST` | `/api/jobs/{id}/candidates` | Upload + parse + score a resume |
| `GET`  | `/api/jobs/{id}/candidates` | List candidates ranked by fit |
| `POST` | `/api/candidates/{id}/interview` | Generate interview questions |

Full interactive docs at `/docs` (Swagger UI) when the backend is running.

---

## 🧪 Tests

```bash
cd backend && source .venv/bin/activate
pytest -q
```

CI (GitHub Actions) runs backend lint + tests and a frontend build on every push.

---

## 🚢 Deployment (free tier)

Deploy the **backend + database on Render** and the **frontend on Vercel**.

### 1. Backend + Postgres → Render (via included `render.yaml`)

1. Push this repo to GitHub (done).
2. Go to [Render](https://render.com) → **New** → **Blueprint** → connect this repo.
3. Render reads `render.yaml` and provisions:
   - a free **Postgres** database, and
   - the **API** web service (installs `requirements-deploy.txt`, runs in torch-free `lite` mode).
4. When it finishes, copy the service URL, e.g. `https://resumate-pro-api.onrender.com`.
   Visit `/docs` on it to confirm the API is live.

### 2. Frontend → Vercel

1. Go to [Vercel](https://vercel.com) → **Add New Project** → import this repo.
2. Set **Root Directory** to `frontend`.
3. Add an environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL (from step 1, no trailing slash).
4. Deploy. Copy the resulting URL, e.g. `https://resumate-pro.vercel.app`.

### 3. Wire them together

- Paste both URLs into the **Live Demo** section at the top of this README.
- (Optional, tighter security) On Render, set `CORS_ORIGINS` to your exact Vercel
  URL instead of `*`, then redeploy.

> **Why lite mode for the demo?** The full neural embedding backend
> (sentence-transformers + PyTorch) needs more memory than free tiers provide.
> The app auto-detects this and uses a torch-free hashing embedding, so the demo
> stays free and fast. Run the full neural backend locally or on a larger
> instance by installing `requirements.txt` (no code change needed).

## 🗺️ Roadmap / possible extensions

- Swap the JSON embedding column for native `pgvector` + ANN index for scale.
- Background processing (Celery/Redis) for bulk resume uploads.
- Resume↔JD gap report and candidate emailing.
- Alembic migrations.

---

## 📄 License

MIT — see [LICENSE](LICENSE).
