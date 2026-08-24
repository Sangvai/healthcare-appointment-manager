import Link from "next/link";

export default function CalendarConnectedPage() {
  return (
    <div className="mx-auto max-w-md rounded-lg border bg-white p-6 text-center">
      <h1 className="mb-3 text-2xl font-semibold text-emerald-700">Google Calendar Connected</h1>
      <p className="mb-6 text-slate-600">
        Your future appointments will now sync automatically to your Google Calendar.
      </p>
      <Link href="/patient/dashboard" className="rounded-md bg-brand-600 px-5 py-2.5 text-white hover:bg-brand-700">
        Back to Dashboard
      </Link>
    </div>
  );
}
