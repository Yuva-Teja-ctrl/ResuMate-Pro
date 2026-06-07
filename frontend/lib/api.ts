// Thin typed client for the ResuMate Pro backend.
// Centralizes the base URL, auth header, and error handling so components
// stay clean.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Job {
  id: number;
  title: string;
  description: string;
  required_skills: string;
  shortlist_count: number;
  education_pref: string;
  min_experience: string;
  certifications: string;
  created_at: string;
}

export interface Education {
  highest_degree: string;
  institution: string;
  graduation_year: string;
}

export interface ScoreBreakdown {
  skills_score: number;
  experience_score: number;
  education_score: number;
  certification_score: number;
}

export interface Candidate {
  id: number;
  job_id: number;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  experience_years: string;
  education: Education;
  certifications: string[];
  strengths: string;
  weaknesses: string;
  education_match: string;
  certification_match: string;
  score_breakdown: ScoreBreakdown;
  shortlisted: boolean;
  created_at: string;
}

export interface JobInput {
  title: string;
  description: string;
  required_skills: string;
  shortlist_count: number;
  education_pref: string;
  min_experience: string;
  certifications: string;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // Only set JSON content-type when we're not sending FormData.
  if (!(options.body instanceof FormData) && options.body) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (email: string, password: string, full_name: string) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listJobs: () => request<Job[]>("/api/jobs"),

  createJob: (data: JobInput) =>
    request<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),

  deleteJob: (id: number) =>
    request<void>(`/api/jobs/${id}`, { method: "DELETE" }),

  listCandidates: (jobId: number) =>
    request<Candidate[]>(`/api/jobs/${jobId}/candidates`),

  uploadCandidate: (jobId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Candidate>(`/api/jobs/${jobId}/candidates`, {
      method: "POST",
      body: form,
    });
  },

  generateInterview: (candidateId: number, num_questions = 5) =>
    request<{ candidate_id: number; questions: string[] }>(
      `/api/candidates/${candidateId}/interview`,
      { method: "POST", body: JSON.stringify({ num_questions }) }
    ),
};

export { getToken };
