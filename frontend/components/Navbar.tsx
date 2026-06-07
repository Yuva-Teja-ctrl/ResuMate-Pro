"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const router = useRouter();

  function logout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  return (
    <nav className="border-b bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="text-lg font-bold text-brand-600">
          ResuMate<span className="text-slate-900"> Pro</span>
        </Link>
        <button
          onClick={logout}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
