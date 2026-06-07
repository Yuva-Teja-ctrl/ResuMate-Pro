"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { api, Candidate, getToken, Job } from "@/lib/api";

// Mirror the backend get_weights() so the breakdown bars show the correct max.
function getWeights(job: Job): [number, number, number, number] {
  const n =
    (job.min_experience ? 1 : 0) +
    (job.education_pref ? 1 : 0) +
    (job.certifications ? 1 : 0);
  if (n === 0) return [100, 0, 0, 0];
  if (n === 1)
    return [
      60,
      job.min_experience ? 40 : 0,
      job.education_pref ? 40 : 0,
      job.certifications ? 40 : 0,
    ];
  if (n === 2)
    return [
      40,
      job.min_experience ? 30 : 0,
      job.education_pref ? 30 : 0,
      job.certifications ? 30 : 0,
    ];
  return [40, 20, 20, 20];
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? "bg-green-100 text-green-700"
      : score >= 40
        ? "bg-amber-100 text-amber-700"
        : "bg-red-100 text-red-700";
  const icon = score >= 70 ? "⭐" : score >= 40 ? "🔶" : "🔴";
  return (
    <span className={`rounded-full px-3 py-1 text-sm font-semibold ${color}`}>
      {icon} {score.toFixed(0)}/100
    </span>
  );
}

function MatchBadge({ label, text }: { label: string; text: string }) {
  if (!text || text === "N/A") return null;
  const color = text.includes("Good")
    ? "bg-green-50 text-green-700"
    : text.includes("Partial")
      ? "bg-orange-50 text-orange-700"
      : "bg-red-50 text-red-700";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${color}`}>
      {label}: {text}
    </span>
  );
}

function Bar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs font-medium">
        <span>{label}</span>
        {max === 0 ? (
          <span className="text-slate-400">Not weighted</span>
        ) : (
          <span className="text-slate-500">
            {value.toFixed(0)}/{max} pts
          </span>
        )}
      </div>
      <div className="mt-1 h-2 w-full rounded bg-slate-200">
        <div
          className={`h-2 rounded ${color}`}
          style={{ width: max === 0 ? "0%" : `${(value / max) * 100}%` }}
        />
      </div>
    </div>
  );
}

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState<Record<number, string[]>>({});
  const [loadingQ, setLoadingQ] = useState<number | null>(null);

  // ---- Result filters (client-side narrowing of the ranked list) ----
  const [minScore, setMinScore] = useState(0);
  const [onlyShortlisted, setOnlyShortlisted] = useState(false);
  const [skillFilter, setSkillFilter] = useState("");

  async function loadAll() {
    try {
      const [j, c] = await Promise.all([
        api.getJob(jobId),
        api.listCandidates(jobId),
      ]);
      setJob(j);
      setCandidates(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setError("");
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await api.uploadCandidate(jobId, file);
      }
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function getQuestions(candidateId: number) {
    setLoadingQ(candidateId);
    try {
      const res = await api.generateInterview(candidateId, 10);
      setQuestions((q) => ({ ...q, [candidateId]: res.questions }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate");
    } finally {
      setLoadingQ(null);
    }
  }

  const weights = job ? getWeights(job) : [100, 0, 0, 0];

  // Apply the client-side result filters.
  const visible = candidates.filter((c) => {
    if (c.score < minScore) return false;
    if (onlyShortlisted && !c.shortlisted) return false;
    if (skillFilter) {
      const want = skillFilter.toLowerCase();
      if (!c.skills.some((s) => s.toLowerCase().includes(want))) return false;
    }
    return true;
  });

  const shortlistedCount = candidates.filter((c) => c.shortlisted).length;
  const avg =
    candidates.length > 0
      ? Math.round(
          candidates.reduce((a, c) => a + c.score, 0) / candidates.length
        )
      : 0;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Link href="/dashboard" className="text-sm text-brand-600 hover:underline">
          &larr; Back to dashboard
        </Link>

        {error && (
          <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {job && (
          <div className="mt-4">
            <h1 className="text-2xl font-bold">{job.title}</h1>
            {job.required_skills && (
              <p className="mt-1 text-sm text-slate-600">
                <span className="font-medium">Required skills:</span>{" "}
                {job.required_skills}
              </p>
            )}
            {/* Active preference filters */}
            <div className="mt-2 flex flex-wrap gap-2">
              {job.min_experience && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                  💼 {job.min_experience}+ yrs
                </span>
              )}
              {job.education_pref && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                  🎓 {job.education_pref}
                </span>
              )}
              {job.certifications && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                  🏅 {job.certifications}
                </span>
              )}
              <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                👥 Shortlist top {job.shortlist_count}
              </span>
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">
              {job.description}
            </p>
          </div>
        )}

        {/* Upload */}
        <div className="mt-8 rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="font-semibold">Upload resumes</h2>
          <p className="text-sm text-slate-500">
            Select one or more PDF resumes. We parse, score and rank them.
          </p>
          <label className="mt-4 inline-block cursor-pointer rounded-md bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700">
            {uploading ? "Processing..." : "Choose resume(s)"}
            <input
              type="file"
              accept=".pdf,.txt"
              multiple
              hidden
              disabled={uploading}
              onChange={onUpload}
            />
          </label>
        </div>

        {/* Metrics */}
        {candidates.length > 0 && (
          <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ["Total Analysed", candidates.length],
              ["Shortlisted", shortlistedCount],
              ["Average Score", `${avg}/100`],
              ["Top Score", `${candidates[0]?.score.toFixed(0)}/100`],
            ].map(([label, val]) => (
              <div key={label} className="rounded-lg border bg-white p-4">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-xl font-bold">{val}</p>
              </div>
            ))}
          </div>
        )}

        {/* Result filters */}
        {candidates.length > 0 && (
          <div className="mt-6 flex flex-wrap items-center gap-4 rounded-lg border bg-white p-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Min score</label>
              <input
                type="range"
                min={0}
                max={100}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
              />
              <span className="w-8 text-sm text-slate-600">{minScore}</span>
            </div>
            <input
              placeholder="Filter by skill (e.g. python)"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              className="rounded-md border px-3 py-1.5 text-sm outline-none focus:border-brand-500"
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={onlyShortlisted}
                onChange={(e) => setOnlyShortlisted(e.target.checked)}
              />
              Shortlisted only
            </label>
          </div>
        )}

        {/* Ranked candidates */}
        <h2 className="mt-8 text-xl font-bold">
          Ranked candidates ({visible.length}
          {visible.length !== candidates.length && ` of ${candidates.length}`})
        </h2>
        <div className="mt-4 space-y-4">
          {candidates.length === 0 && (
            <p className="text-slate-500">
              No candidates yet. Upload resumes to see the ranking.
            </p>
          )}
          {visible.map((c) => {
            const rank = candidates.findIndex((x) => x.id === c.id) + 1;
            const sb = c.score_breakdown;
            return (
              <div key={c.id} className="rounded-xl border bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold">
                      #{rank} &nbsp;{c.name || "Unknown candidate"}
                      {c.shortlisted && (
                        <span className="ml-2 rounded-full bg-brand-600 px-2 py-0.5 text-xs text-white">
                          ✅ Shortlisted
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-slate-500">
                      {c.email} {c.phone && `· ${c.phone}`}
                    </p>
                  </div>
                  <ScoreBadge score={c.score} />
                </div>

                {/* Score breakdown */}
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Bar label="🛠️ Skills" value={sb.skills_score} max={weights[0]} color="bg-blue-500" />
                  <Bar label="💼 Experience" value={sb.experience_score} max={weights[1]} color="bg-green-500" />
                  <Bar label="🎓 Education" value={sb.education_score} max={weights[2]} color="bg-purple-500" />
                  <Bar label="🏅 Certifications" value={sb.certification_score} max={weights[3]} color="bg-orange-500" />
                </div>

                {/* Profile facts */}
                <div className="mt-4 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                  <p>
                    <span className="font-medium">Experience:</span>{" "}
                    {c.experience_years}
                  </p>
                  <p>
                    <span className="font-medium">Education:</span>{" "}
                    {c.education.highest_degree}
                    {c.education.institution !== "N/A" &&
                      ` — ${c.education.institution}`}
                    {c.education.graduation_year !== "N/A" &&
                      ` (${c.education.graduation_year})`}
                  </p>
                </div>

                <div className="mt-2 flex flex-wrap gap-2">
                  <MatchBadge label="Edu" text={c.education_match} />
                  <MatchBadge label="Certs" text={c.certification_match} />
                </div>

                {/* Skills */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {c.matched_skills.map((s) => (
                    <span key={s} className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-700">
                      ✓ {s}
                    </span>
                  ))}
                  {c.missing_skills.map((s) => (
                    <span key={s} className="rounded bg-red-50 px-2 py-0.5 text-xs text-red-700">
                      ✗ {s}
                    </span>
                  ))}
                </div>

                {c.certifications.length > 0 && (
                  <p className="mt-3 text-sm">
                    <span className="font-medium">🏅 Certifications:</span>{" "}
                    {c.certifications.join(", ")}
                  </p>
                )}

                <p className="mt-3 text-sm text-slate-600">
                  <span className="font-medium text-slate-800">💪 Strengths:</span>{" "}
                  {c.strengths}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  <span className="font-medium text-slate-800">⚠️ Gaps:</span>{" "}
                  {c.weaknesses}
                </p>

                <button
                  onClick={() => getQuestions(c.id)}
                  disabled={loadingQ === c.id}
                  className="mt-4 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-60"
                >
                  {loadingQ === c.id
                    ? "Generating..."
                    : "Generate interview questions"}
                </button>

                {questions[c.id] && (
                  <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                    {questions[c.id].map((q, qi) => (
                      <li key={qi}>{q}</li>
                    ))}
                  </ol>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
