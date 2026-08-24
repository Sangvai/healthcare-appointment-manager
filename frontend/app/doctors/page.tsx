"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, apiErrorMessage } from "@/services/api";
import { Doctor } from "@/types";

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [specialization, setSpecialization] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDoctors = async (spec?: string) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Doctor[]>("/doctors", { params: spec ? { specialization: spec } : {} });
      setDoctors(data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctors();
  }, []);

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Find a Doctor</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          fetchDoctors(specialization);
        }}
        className="mb-6 flex gap-2"
      >
        <input
          value={specialization}
          onChange={(e) => setSpecialization(e.target.value)}
          placeholder="Search by specialization (e.g. Pediatrics)"
          className="w-full max-w-sm rounded-md border px-3 py-2"
        />
        <button className="rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700">Search</button>
      </form>

      {loading && <p className="text-slate-500">Loading doctors...</p>}
      {error && <p className="text-red-600">{error}</p>}
      {!loading && !error && doctors.length === 0 && <p className="text-slate-500">No doctors found.</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {doctors.map((doctor) => (
          <Link
            key={doctor.id}
            href={`/doctors/${doctor.id}`}
            className="rounded-lg border bg-white p-4 shadow-sm transition hover:shadow-md"
          >
            <h2 className="font-semibold">{doctor.full_name}</h2>
            <p className="text-sm text-slate-500">{doctor.qualification}</p>
            <p className="mt-1 text-sm text-slate-600">
              {doctor.specializations.map((s) => s.name).join(", ") || "General"}
            </p>
            <p className="mt-1 text-xs text-slate-400">{doctor.experience_years ?? 0} yrs experience</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
