"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/services/api";
import { Appointment } from "@/types";

function ListContent() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    api.get<Appointment[]>("/admin/appointments").then((res) => setAppointments(res.data));
  }, []);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">All Appointments</h1>
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="p-3">ID</th>
              <th className="p-3">Doctor</th>
              <th className="p-3">Patient</th>
              <th className="p-3">Time</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((a) => (
              <tr key={a.id} className="border-b">
                <td className="p-3">{a.id}</td>
                <td className="p-3">#{a.doctor_id}</td>
                <td className="p-3">#{a.patient_id}</td>
                <td className="p-3">{new Date(a.start_time).toLocaleString()}</td>
                <td className="p-3">
                  <StatusBadge value={a.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {appointments.length === 0 && <p className="p-4 text-slate-500">No appointments yet.</p>}
      </div>
    </div>
  );
}

export default function AdminAppointmentsPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <ListContent />
    </ProtectedRoute>
  );
}
