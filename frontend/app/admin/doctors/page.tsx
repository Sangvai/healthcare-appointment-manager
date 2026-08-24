"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/services/api";
import { Doctor } from "@/types";

function ListContent() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    api.get<Doctor[]>("/doctors").then((res) => setDoctors(res.data));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Doctors</h1>
        <Link href="/admin/doctors/create" className="rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700">
          + Add Doctor
        </Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {doctors.map((d) => (
          <Link key={d.id} href={`/admin/doctors/${d.id}`} className="rounded-lg border bg-white p-4 hover:shadow-sm">
            <p className="font-medium">{d.full_name}</p>
            <p className="text-sm text-slate-500">{d.specializations.map((s) => s.name).join(", ") || "General"}</p>
            <p className={`mt-1 text-xs ${d.is_active ? "text-emerald-600" : "text-red-600"}`}>
              {d.is_active ? "Active" : "Inactive"}
            </p>
          </Link>
        ))}
        {doctors.length === 0 && <p className="text-slate-500">No doctors yet.</p>}
      </div>
    </div>
  );
}

export default function AdminDoctorsPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <ListContent />
    </ProtectedRoute>
  );
}
