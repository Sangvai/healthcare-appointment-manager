"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/services/api";
import { Appointment } from "@/types";

function DashboardContent() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    api.get<Appointment[]>("/appointments").then((res) => setAppointments(res.data));
  }, []);

  const next = appointments
    .filter((a) => new Date(a.start_time).getTime() >= Date.now() && (a.status === "PENDING" || a.status === "CONFIRMED"))
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Welcome back</h1>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link href="/doctors" className="rounded-lg border bg-white p-4 hover:shadow-sm">
          <p className="font-medium">Book an appointment</p>
          <p className="text-sm text-slate-500">Search doctors by specialization</p>
        </Link>
        <Link href="/patient/appointments" className="rounded-lg border bg-white p-4 hover:shadow-sm">
          <p className="font-medium">My appointments</p>
          <p className="text-sm text-slate-500">{appointments.length} total</p>
        </Link>
        <Link href="/patient/calendar" className="rounded-lg border bg-white p-4 hover:shadow-sm">
          <p className="font-medium">Google Calendar</p>
          <p className="text-sm text-slate-500">Sync your appointments</p>
        </Link>
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-semibold">Next appointment</h2>
        {next ? (
          <Link href={`/patient/appointments/${next.id}`} className="flex items-center justify-between">
            <span>{new Date(next.start_time).toLocaleString()}</span>
            <StatusBadge value={next.status} />
          </Link>
        ) : (
          <p className="text-slate-500">No upcoming appointments.</p>
        )}
      </div>
    </div>
  );
}

export default function PatientDashboardPage() {
  return (
    <ProtectedRoute allow={["PATIENT"]}>
      <DashboardContent />
    </ProtectedRoute>
  );
}
