"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";

function DashboardContent() {
  const links = [
    { href: "/admin/doctors", label: "Manage Doctors", desc: "Create, edit, activate/deactivate doctors" },
    { href: "/admin/leaves", label: "Doctor Leave", desc: "Mark leave days, view affected appointments" },
    { href: "/admin/appointments", label: "All Appointments", desc: "System-wide appointment overview" },
    { href: "/admin/notifications", label: "Notification Failures", desc: "Emails that failed after retries" },
  ];
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Admin Dashboard</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className="rounded-lg border bg-white p-4 hover:shadow-sm">
            <p className="font-medium">{l.label}</p>
            <p className="text-sm text-slate-500">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <DashboardContent />
    </ProtectedRoute>
  );
}
