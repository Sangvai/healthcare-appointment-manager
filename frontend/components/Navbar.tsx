"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function Navbar() {
  const { token, role, logout } = useAuth();

  const dashboardHref = role === "PATIENT" ? "/patient/dashboard" : role === "DOCTOR" ? "/doctor/dashboard" : "/admin/dashboard";

  return (
    <nav className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-semibold text-brand-700">
          Healthcare Manager
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {!token && (
            <>
              <Link href="/doctors" className="hover:text-brand-600">Find Doctors</Link>
              <Link href="/login" className="hover:text-brand-600">Login</Link>
              <Link href="/register" className="rounded-md bg-brand-600 px-3 py-1.5 text-white hover:bg-brand-700">
                Register
              </Link>
            </>
          )}
          {token && (
            <>
              <Link href={dashboardHref} className="hover:text-brand-600">Dashboard</Link>
              {role === "PATIENT" && <Link href="/doctors" className="hover:text-brand-600">Find Doctors</Link>}
              <button onClick={logout} className="rounded-md border px-3 py-1.5 hover:bg-slate-50">
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
