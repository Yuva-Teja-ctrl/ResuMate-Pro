import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <div className="max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          ResuMate <span className="text-brand-600">Pro</span>
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          AI-based recruitment assistant. Parse resumes, match them to a job
          description, rank candidates by fit, and generate tailored interview
          questions — all in one place.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            href="/register"
            className="rounded-lg bg-brand-600 px-6 py-3 font-medium text-white hover:bg-brand-700"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-slate-300 px-6 py-3 font-medium hover:bg-slate-100"
          >
            Log in
          </Link>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-4 text-left sm:grid-cols-2">
          {[
            ["📄 Resume parsing", "Extract name, contact, and skills from PDFs."],
            ["🎯 Smart matching", "Hybrid semantic + skill-overlap scoring."],
            ["📊 Ranking", "Candidates sorted by fit, with matched/missing skills."],
            ["💬 Interview prep", "Auto-generate questions tailored to each candidate."],
          ].map(([title, desc]) => (
            <div key={title} className="rounded-lg border bg-white p-4">
              <p className="font-semibold">{title}</p>
              <p className="text-sm text-slate-600">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
