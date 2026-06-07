"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { api, getToken, Job } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [shortlistCount, setShortlistCount] = useState(3);
  const [educationPref, setEducationPref] = useState("");
  const [minExperience, setMinExperience] = useState("");
  const [certifications, setCertifications] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadJobs() {
    try {
      setJobs(await api.listJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    }
  }

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.createJob({
        title,
        description,
        required_skills: requiredSkills,
        shortlist_count: shortlistCount,
        education_pref: educationPref,
        min_experience: minExperience,
        certifications,
      });
      setTitle("");
      setDescription("");
      setRequiredSkills("");
      setShortlistCount(3);
      setEducationPref("");
      setMinExperience("");
      setCertifications("");
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setLoading(false);
    }
  }

  async function removeJob(id: number) {
    await api.deleteJob(id);
    await loadJobs();
  }

  const activeFilters = [
    educationPref && `🎓 ${educationPref}`,
    minExperience && `💼 ${minExperience}+ yrs`,
    certifications && `🏅 ${certifications}`,
  ].filter(Boolean);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="text-2xl font-bold">Your job postings</h1>

        {error && (
          <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Create job */}
        <form
          onSubmit={createJob}
          className="mt-6 rounded-xl border bg-white p-6 shadow-sm"
        >
          <h2 className="font-semibold">
            Job Requirements{" "}
            <span className="text-sm font-normal text-slate-400">(required)</span>
          </h2>

          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-5">
            <input
              placeholder="🎯 Job role (e.g. Backend Engineer)"
              value={title}
              required
              onChange={(e) => setTitle(e.target.value)}
              className="rounded-md border px-3 py-2 outline-none focus:border-brand-500 sm:col-span-2"
            />
            <input
              placeholder="🛠️ Required skills (e.g. Python, React, SQL)"
              value={requiredSkills}
              required
              onChange={(e) => setRequiredSkills(e.target.value)}
              className="rounded-md border px-3 py-2 outline-none focus:border-brand-500 sm:col-span-2"
            />
            <div>
              <label className="block text-xs text-slate-500">Shortlist Top N</label>
              <input
                type="number"
                min={1}
                max={100}
                value={shortlistCount}
                onChange={(e) => setShortlistCount(Number(e.target.value))}
                className="w-full rounded-md border px-3 py-2 outline-none focus:border-brand-500"
              />
            </div>
          </div>

          <textarea
            placeholder="Paste the full job description here..."
            value={description}
            required
            rows={4}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-3 w-full rounded-md border px-3 py-2 outline-none focus:border-brand-500"
          />

          <h3 className="mt-5 font-medium text-slate-700">
            Additional Preferences{" "}
            <span className="text-sm font-normal text-slate-400">— optional</span>
          </h3>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <input
                placeholder="🎓 Education (e.g. B.Tech)"
                value={educationPref}
                onChange={(e) => setEducationPref(e.target.value)}
                className="w-full rounded-md border px-3 py-2 outline-none focus:border-brand-500"
              />
              <p className="mt-1 text-xs text-slate-400">
                Leave blank to accept any background
              </p>
            </div>
            <div>
              <input
                placeholder="💼 Min experience (years)"
                value={minExperience}
                onChange={(e) => setMinExperience(e.target.value)}
                className="w-full rounded-md border px-3 py-2 outline-none focus:border-brand-500"
              />
              <p className="mt-1 text-xs text-slate-400">
                Leave blank to consider freshers too
              </p>
            </div>
            <div>
              <input
                placeholder="🏅 Certifications (e.g. AWS Certified)"
                value={certifications}
                onChange={(e) => setCertifications(e.target.value)}
                className="w-full rounded-md border px-3 py-2 outline-none focus:border-brand-500"
              />
              <p className="mt-1 text-xs text-slate-400">
                Leave blank if not required
              </p>
            </div>
          </div>

          {activeFilters.length > 0 && (
            <div className="mt-4 rounded-md bg-green-50 p-3 text-sm text-green-800">
              <span className="font-semibold">Active Filters:</span>{" "}
              {activeFilters.join("  |  ")}
            </div>
          )}

          <button
            disabled={loading}
            className="mt-4 rounded-md bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? "Creating..." : "Create job"}
          </button>
        </form>

        {/* Job list */}
        <div className="mt-8 space-y-3">
          {jobs.length === 0 && (
            <p className="text-slate-500">No jobs yet. Create one above.</p>
          )}
          {jobs.map((job) => (
            <div
              key={job.id}
              className="flex items-center justify-between rounded-lg border bg-white p-4"
            >
              <div>
                <Link
                  href={`/jobs/${job.id}`}
                  className="font-semibold text-brand-600 hover:underline"
                >
                  {job.title}
                </Link>
                <p className="line-clamp-1 max-w-xl text-sm text-slate-500">
                  {job.description}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href={`/jobs/${job.id}`}
                  className="rounded-md border px-3 py-1.5 text-sm hover:bg-slate-100"
                >
                  Open
                </Link>
                <button
                  onClick={() => removeJob(job.id)}
                  className="text-sm text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
