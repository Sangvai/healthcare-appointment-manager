"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, apiErrorMessage } from "@/services/api";

interface PatientProfile {
  id: number;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  address: string | null;
}

function ProfileContent() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<PatientProfile>("/patients/me").then((res) => setProfile(res.data));
  }, []);

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const { data } = await api.patch<PatientProfile>("/patients/me", {
        full_name: profile.full_name,
        date_of_birth: profile.date_of_birth || null,
        gender: profile.gender || null,
        address: profile.address || null,
      });
      setProfile(data);
      setMessage("Profile updated.");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (!profile) return <p className="text-slate-500">Loading profile...</p>;

  return (
    <div className="mx-auto max-w-md rounded-lg border bg-white p-6">
      <h1 className="mb-4 text-2xl font-semibold">My Profile</h1>
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Full name</label>
          <input
            className="w-full rounded-md border px-3 py-2"
            value={profile.full_name}
            onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Date of birth</label>
          <input
            type="date"
            className="w-full rounded-md border px-3 py-2"
            value={profile.date_of_birth || ""}
            onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Gender</label>
          <input
            className="w-full rounded-md border px-3 py-2"
            value={profile.gender || ""}
            onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Address</label>
          <textarea
            className="w-full rounded-md border px-3 py-2"
            value={profile.address || ""}
            onChange={(e) => setProfile({ ...profile, address: e.target.value })}
          />
        </div>
        {message && <p className="text-sm text-emerald-700">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          onClick={save}
          disabled={saving}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "Saving..." : "Save changes"}
        </button>
      </div>
    </div>
  );
}

export default function PatientProfilePage() {
  return (
    <ProtectedRoute allow={["PATIENT"]}>
      <ProfileContent />
    </ProtectedRoute>
  );
}
