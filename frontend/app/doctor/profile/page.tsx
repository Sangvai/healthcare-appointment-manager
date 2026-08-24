"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/services/api";
import { Doctor } from "@/types";

function ProfileContent() {
  const [doctor, setDoctor] = useState<Doctor | null>(null);

  useEffect(() => {
    api.get<Doctor>("/doctors/me").then((res) => setDoctor(res.data));
  }, []);

  if (!doctor) return <p className="text-slate-500">Loading profile...</p>;

  return (
    <div className="mx-auto max-w-md rounded-lg border bg-white p-6">
      <h1 className="mb-4 text-2xl font-semibold">{doctor.full_name}</h1>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between border-b pb-2">
          <dt className="text-slate-500">Qualification</dt>
          <dd>{doctor.qualification || "-"}</dd>
        </div>
        <div className="flex justify-between border-b pb-2">
          <dt className="text-slate-500">Experience</dt>
          <dd>{doctor.experience_years ?? 0} years</dd>
        </div>
        <div className="flex justify-between border-b pb-2">
          <dt className="text-slate-500">Specializations</dt>
          <dd>{doctor.specializations.map((s) => s.name).join(", ") || "-"}</dd>
        </div>
      </dl>
      <div className="mt-4">
        <h2 className="mb-2 font-medium">Working Hours</h2>
        <ul className="space-y-1 text-sm text-slate-600">
          {doctor.working_hours.map((wh) => (
            <li key={wh.id}>
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][wh.day_of_week]}: {wh.start_time}–{wh.end_time} ({wh.slot_duration_minutes} min slots)
            </li>
          ))}
          {doctor.working_hours.length === 0 && <li>Not configured by admin yet.</li>}
        </ul>
      </div>
      <p className="mt-4 text-xs text-slate-400">
        Working hours, specializations, and leave are managed by the clinic admin.
      </p>
    </div>
  );
}

export default function DoctorProfilePage() {
  return (
    <ProtectedRoute allow={["DOCTOR"]}>
      <ProfileContent />
    </ProtectedRoute>
  );
}
