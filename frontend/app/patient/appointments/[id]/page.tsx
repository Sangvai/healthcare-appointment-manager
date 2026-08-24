"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api, apiErrorMessage } from "@/services/api";
import { Appointment, PostVisitSummary } from "@/types";

function DetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [summary, setSummary] = useState<PostVisitSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newTime, setNewTime] = useState("");

  const load = async () => {
    const { data } = await api.get<Appointment>(`/appointments/${params.id}`);
    setAppointment(data);
    if (data.status === "COMPLETED") {
      try {
        const { data: s } = await api.get<PostVisitSummary>(`/appointments/${params.id}/post-visit-summary`);
        setSummary(s);
      } catch {
        // summary not ready yet, ignore
      }
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const cancel = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.patch(`/appointments/${params.id}/cancel`, { reason: "Cancelled by patient" });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const reschedule = async () => {
    if (!newTime) return;
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.patch(`/appointments/${params.id}/reschedule`, {
        new_start_time: new Date(newTime).toISOString(),
      });
      router.push(`/patient/appointments/${data.id}`);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!appointment) return <p className="text-slate-500">Loading...</p>;

  const canModify = appointment.status === "PENDING" || appointment.status === "CONFIRMED";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="rounded-lg border bg-white p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">{new Date(appointment.start_time).toLocaleString()}</h1>
          <StatusBadge value={appointment.status} />
        </div>
        {appointment.cancelled_reason && <p className="mt-2 text-sm text-slate-500">Reason: {appointment.cancelled_reason}</p>}
      </div>

      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {canModify && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 font-semibold">Manage appointment</h2>
          <div className="mb-3 flex gap-2">
            <input
              type="datetime-local"
              value={newTime}
              onChange={(e) => setNewTime(e.target.value)}
              className="rounded-md border px-3 py-2"
            />
            <button onClick={reschedule} disabled={busy} className="rounded-md border px-4 py-2 hover:bg-slate-50">
              Reschedule
            </button>
          </div>
          <button onClick={cancel} disabled={busy} className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700">
            Cancel Appointment
          </button>
        </div>
      )}

      {appointment.status === "COMPLETED" && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 font-semibold">Visit Summary</h2>
          {!summary && <p className="text-slate-500">Summary is being generated, check back shortly.</p>}
          {summary && summary.status === "FAILED" && (
            <p className="text-amber-700">AI summary unavailable. Please contact the clinic for your visit details.</p>
          )}
          {summary && summary.status === "SUCCESS" && (
            <div className="space-y-4">
              <p>{summary.summary}</p>
              {summary.medication_schedule && summary.medication_schedule.length > 0 && (
                <div>
                  <h3 className="mb-2 font-medium">Medication Schedule</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-slate-500">
                        <th className="pb-1">Medicine</th>
                        <th className="pb-1">Dose</th>
                        <th className="pb-1">Frequency</th>
                        <th className="pb-1">Duration</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.medication_schedule.map((m, i) => (
                        <tr key={i} className="border-t">
                          <td className="py-1">{m.medicine}</td>
                          <td className="py-1">{m.dose}</td>
                          <td className="py-1">{m.frequency}</td>
                          <td className="py-1">{m.duration}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {summary.follow_up_steps && summary.follow_up_steps.length > 0 && (
                <div>
                  <h3 className="mb-2 font-medium">Follow-up Steps</h3>
                  <ul className="list-disc pl-5">
                    {summary.follow_up_steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function PatientAppointmentDetailPage() {
  return (
    <ProtectedRoute allow={["PATIENT"]}>
      <DetailContent />
    </ProtectedRoute>
  );
}
