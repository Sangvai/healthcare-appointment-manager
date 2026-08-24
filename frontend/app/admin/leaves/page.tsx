"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/services/api";
import { Doctor } from "@/types";

function LeavesContent() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    api.get<Doctor[]>("/doctors").then((res) => setDoctors(res.data));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Doctor Leave</h1>
      <p className="mb-6 text-slate-500">Select a doctor to add or view leave days.</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {doctors.map((d) => (
          <Link key={d.id} href={`/admin/doctors/${d.id}`} className="rounded-lg border bg-white p-4 hover:shadow-sm">
            <p className="font-medium">{d.full_name}</p>
            <p className="text-sm text-slate-500">{d.specializations.map((s) => s.name).join(", ") || "General"}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function AdminLeavesPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <LeavesContent />
    </ProtectedRoute>
  );
}
