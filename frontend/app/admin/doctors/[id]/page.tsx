"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, apiErrorMessage } from "@/services/api";
import { Doctor } from "@/types";

function DetailContent() {
  const params = useParams<{ id: string }>();
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [leaveDate, setLeaveDate] = useState("");
  const [leaveReason, setLeaveReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get<Doctor>(`/doctors/${params.id}`).then((res) => setDoctor(res.data));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const toggleActive = async () => {
    if (!doctor) return;
    setBusy(true);
    try {
      await api.patch(`/admin/doctors/${doctor.id}`, { is_active: !doctor.is_active });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const addLeave = async () => {
    if (!leaveDate) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.post(`/admin/doctors/${params.id}/leave`, { leave_date: leaveDate, reason: leaveReason });
      setMessage("Leave added. Affected patients (if any) are being notified automatically.");
      setLeaveDate("");
      setLeaveReason("");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!doctor) return <p className="text-slate-500">Loading...</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between rounded-lg border bg-white p-4">
        <div>
          <h1 className="text-xl font-semibold">{doctor.full_name}</h1>
          <p className="text-sm text-slate-500">{doctor.qualification}</p>
        </div>
        <button
          onClick={toggleActive}
          disabled={busy}
          className={`rounded-md px-4 py-2 text-white ${doctor.is_active ? "bg-red-600 hover:bg-red-700" : "bg-emerald-600 hover:bg-emerald-700"}`}
        >
          {doctor.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Working Hours</h2>
        <ul className="space-y-1 text-sm">
          {doctor.working_hours.map((wh) => (
            <li key={wh.id}>
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][wh.day_of_week]}: {wh.start_time}–{wh.end_time} ({wh.slot_duration_minutes} min)
            </li>
          ))}
          {doctor.working_hours.length === 0 && <li className="text-slate-500">Not configured.</li>}
        </ul>
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Mark Leave</h2>
        <p className="mb-3 text-sm text-slate-500">
          If the doctor has confirmed appointments on this date, they will be cancelled and both the patient and
          doctor will be notified by email automatically.
        </p>
        <div className="flex flex-wrap gap-2">
          <input type="date" value={leaveDate} onChange={(e) => setLeaveDate(e.target.value)} className="rounded-md border px-3 py-2" />
          <input
            placeholder="Reason (optional)"
            value={leaveReason}
            onChange={(e) => setLeaveReason(e.target.value)}
            className="rounded-md border px-3 py-2"
          />
          <button onClick={addLeave} disabled={busy} className="rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700">
            Add Leave
          </button>
        </div>
        {message && <p className="mt-3 text-sm text-emerald-700">{message}</p>}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}

export default function AdminDoctorDetailPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <DetailContent />
    </ProtectedRoute>
  );
}
