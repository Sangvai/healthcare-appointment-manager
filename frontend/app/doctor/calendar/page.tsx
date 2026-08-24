"use client";

import { useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, apiErrorMessage } from "@/services/api";

function CalendarContent() {
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  const connect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const { data } = await api.post<{ authorization_url: string }>("/google/connect");
      window.location.href = data.authorization_url;
    } catch (e) {
      setError(apiErrorMessage(e));
      setConnecting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md rounded-lg border bg-white p-6 text-center">
      <h1 className="mb-3 text-2xl font-semibold">Connect Google Calendar</h1>
      <p className="mb-6 text-slate-600">
        Connect your Google account so your confirmed appointments automatically appear on your calendar.
      </p>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <button
        onClick={connect}
        disabled={connecting}
        className="rounded-md bg-brand-600 px-5 py-2.5 text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {connecting ? "Redirecting..." : "Connect Google Calendar"}
      </button>
    </div>
  );
}

export default function DoctorCalendarPage() {
  return (
    <ProtectedRoute allow={["DOCTOR"]}>
      <CalendarContent />
    </ProtectedRoute>
  );
}
