"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api } from "@/services/api";

interface FailedEmail {
  id: number;
  recipient: string;
  notification_type: string;
  attempt_count: number;
  last_error: string | null;
}

function ListContent() {
  const [failures, setFailures] = useState<FailedEmail[]>([]);

  useEffect(() => {
    api.get<FailedEmail[]>("/admin/notifications/failures").then((res) => setFailures(res.data));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Notification Failures</h1>
      <p className="mb-6 text-slate-500">
        Emails that failed after the maximum retry attempts (Celery keeps retrying with backoff before landing here).
      </p>
      <div className="space-y-2">
        {failures.map((f) => (
          <div key={f.id} className="rounded-lg border bg-white p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">{f.recipient}</span>
              <span className="text-xs text-slate-500">{f.notification_type}</span>
            </div>
            <p className="mt-1 text-sm text-red-600">{f.last_error}</p>
            <p className="text-xs text-slate-400">Attempts: {f.attempt_count}</p>
          </div>
        ))}
        {failures.length === 0 && <p className="text-slate-500">No permanent failures. Everything is healthy.</p>}
      </div>
    </div>
  );
}

export default function AdminNotificationsPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <ListContent />
    </ProtectedRoute>
  );
}
