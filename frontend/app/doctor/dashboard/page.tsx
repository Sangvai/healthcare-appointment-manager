"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/services/api";
import { Appointment } from "@/types";

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return d.toDateString() === now.toDateString();
}

function DashboardContent() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    api.get<Appointment[]>("/appointments").then((res) => setAppointments(res.data));
  }, []);

  const today = appointments.filter((a) => isToday(a.start_time) && a.status !== "CANCELLED");
  const upcoming = appointments.filter(
    (a) => !isToday(a.start_time) && new Date(a.start_time).getTime() > Date.now() && a.status !== "CANCELLED"
  );

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Doctor Dashboard</h1>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Today&apos;s Appointments</h2>
        <div className="space-y-2">
          {today.map((a) => (
            <Link key={a.id} href={`/doctor/appointments/${a.id}`} className="flex items-center justify-between rounded-lg border bg-white p-3 hover:shadow-sm">
              <span>{new Date(a.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
              <StatusBadge value={a.status} />
            </Link>
          ))}
          {today.length === 0 && <p className="text-slate-500">No appointments today.</p>}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Upcoming</h2>
        <div className="space-y-2">
          {upcoming.slice(0, 10).map((a) => (
            <Link key={a.id} href={`/doctor/appointments/${a.id}`} className="flex items-center justify-between rounded-lg border bg-white p-3 hover:shadow-sm">
              <span>{new Date(a.start_time).toLocaleString()}</span>
              <StatusBadge value={a.status} />
            </Link>
          ))}
          {upcoming.length === 0 && <p className="text-slate-500">Nothing upcoming.</p>}
        </div>
      </section>
    </div>
  );
}

export default function DoctorDashboardPage() {
  return (
    <ProtectedRoute allow={["DOCTOR"]}>
      <DashboardContent />
    </ProtectedRoute>
  );
}
