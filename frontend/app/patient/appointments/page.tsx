"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/services/api";
import { Appointment } from "@/types";

function AppointmentsList() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Appointment[]>("/appointments").then((res) => setAppointments(res.data)).finally(() => setLoading(false));
  }, []);

  const now = Date.now();
  const upcoming = appointments.filter((a) => new Date(a.start_time).getTime() >= now && a.status !== "CANCELLED");
  const past = appointments.filter((a) => new Date(a.start_time).getTime() < now || a.status === "CANCELLED");

  const renderList = (list: Appointment[]) => (
    <div className="space-y-3">
      {list.map((a) => (
        <Link
          key={a.id}
          href={`/patient/appointments/${a.id}`}
          className="flex items-center justify-between rounded-lg border bg-white p-4 hover:shadow-sm"
        >
          <div>
            <p className="font-medium">{new Date(a.start_time).toLocaleString()}</p>
            {a.cancelled_reason && <p className="text-sm text-slate-500">Reason: {a.cancelled_reason}</p>}
          </div>
          <StatusBadge value={a.status} />
        </Link>
      ))}
      {list.length === 0 && <p className="text-slate-500">Nothing here yet.</p>}
    </div>
  );

  if (loading) return <p className="text-slate-500">Loading appointments...</p>;

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-semibold">Upcoming</h2>
        {renderList(upcoming)}
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Past / Cancelled</h2>
        {renderList(past)}
      </section>
    </div>
  );
}

export default function PatientAppointmentsPage() {
  return (
    <ProtectedRoute allow={["PATIENT"]}>
      <h1 className="mb-6 text-2xl font-semibold">My Appointments</h1>
      <AppointmentsList />
    </ProtectedRoute>
  );
}
