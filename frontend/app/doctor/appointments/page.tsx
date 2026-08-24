"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/services/api";
import { Appointment } from "@/types";

function ListContent() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    api.get<Appointment[]>("/appointments").then((res) => setAppointments(res.data));
  }, []);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">All Appointments</h1>
      <div className="space-y-2">
        {appointments.map((a) => (
          <Link key={a.id} href={`/doctor/appointments/${a.id}`} className="flex items-center justify-between rounded-lg border bg-white p-4 hover:shadow-sm">
            <span>{new Date(a.start_time).toLocaleString()}</span>
            <StatusBadge value={a.status} />
          </Link>
        ))}
        {appointments.length === 0 && <p className="text-slate-500">No appointments yet.</p>}
      </div>
    </div>
  );
}

export default function DoctorAppointmentsPage() {
  return (
    <ProtectedRoute allow={["DOCTOR"]}>
      <ListContent />
    </ProtectedRoute>
  );
}
