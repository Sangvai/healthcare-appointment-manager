import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center py-20 text-center">
      <h1 className="max-w-2xl text-4xl font-bold text-slate-900">
        Book appointments. Get AI-powered visit summaries. Never miss a follow-up.
      </h1>
      <p className="mt-4 max-w-xl text-slate-600">
        A clinic platform for patients, doctors, and admins — with symptom intake, pre-visit AI
        summaries, post-visit patient-friendly reports, and automatic reminders.
      </p>
      <div className="mt-8 flex gap-4">
        <Link href="/doctors" className="rounded-md bg-brand-600 px-5 py-2.5 text-white hover:bg-brand-700">
          Find a Doctor
        </Link>
        <Link href="/register" className="rounded-md border px-5 py-2.5 hover:bg-slate-50">
          Create Account
        </Link>
      </div>
    </div>
  );
}
