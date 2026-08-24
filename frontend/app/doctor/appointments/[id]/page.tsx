"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useFieldArray, useForm } from "react-hook-form";
import ProtectedRoute from "@/components/ProtectedRoute";
import StatusBadge from "@/components/StatusBadge";
import { api, apiErrorMessage } from "@/services/api";
import { Appointment, PreVisitSummary } from "@/types";

interface ConsultationFormValues {
  notes: string;
  diagnosis: string;
  follow_up_instructions: string;
  medications: { medicine_name: string; dose: string; frequency: string; duration_days: number }[];
}

interface SymptomFormData {
  chief_complaint: string;
  symptoms: string;
  duration: string | null;
  severity: string | null;
  additional_notes: string | null;
}

function DetailContent() {
  const params = useParams<{ id: string }>();
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [preVisit, setPreVisit] = useState<PreVisitSummary | null>(null);
  const [symptoms, setSymptoms] = useState<SymptomFormData | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { register, control, handleSubmit } = useForm<ConsultationFormValues>({
    defaultValues: { medications: [{ medicine_name: "", dose: "", frequency: "Once daily", duration_days: 5 }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "medications" });

  useEffect(() => {
    api.get<Appointment>(`/appointments/${params.id}`).then((res) => setAppointment(res.data));
    api
      .get<PreVisitSummary>(`/appointments/${params.id}/pre-visit-summary`)
      .then((res) => setPreVisit(res.data))
      .catch(() => setPreVisit(null));
    api
      .get<SymptomFormData>(`/appointments/${params.id}/symptoms`)
      .then((res) => setSymptoms(res.data))
      .catch(() => setSymptoms(null));
  }, [params.id]);

  const onSubmit = async (values: ConsultationFormValues) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/appointments/${params.id}/consultation`, {
        ...values,
        medications: values.medications.filter((m) => m.medicine_name),
      });
      setSubmitted(true);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (!appointment) return <p className="text-slate-500">Loading...</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between rounded-lg border bg-white p-4">
        <h1 className="text-xl font-semibold">{new Date(appointment.start_time).toLocaleString()}</h1>
        <StatusBadge value={appointment.status} />
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">AI Pre-Visit Summary</h2>
        {!preVisit && <p className="text-slate-500">Not available yet.</p>}
        {preVisit && preVisit.status === "FAILED" && (
          <div>
            <p className="mb-3 text-amber-700">AI summary unavailable. Please review the patient&apos;s original symptoms below.</p>
            {symptoms && (
              <dl className="space-y-1 text-sm">
                <div><dt className="inline text-slate-500">Chief complaint: </dt><dd className="inline">{symptoms.chief_complaint}</dd></div>
                <div><dt className="inline text-slate-500">Symptoms: </dt><dd className="inline">{symptoms.symptoms}</dd></div>
                <div><dt className="inline text-slate-500">Duration: </dt><dd className="inline">{symptoms.duration || "-"}</dd></div>
                <div><dt className="inline text-slate-500">Severity: </dt><dd className="inline">{symptoms.severity || "-"}</dd></div>
              </dl>
            )}
          </div>
        )}
        {preVisit && preVisit.status === "SUCCESS" && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">Urgency:</span>
              <StatusBadge value={preVisit.urgency_level || ""} />
            </div>
            <p>
              <span className="text-sm text-slate-500">Chief complaint: </span>
              {preVisit.chief_complaint}
            </p>
            {preVisit.suggested_questions && (
              <div>
                <p className="text-sm text-slate-500">Suggested questions:</p>
                <ul className="list-disc pl-5">
                  {preVisit.suggested_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-slate-400">
              This is AI-generated decision support, not a diagnosis. Always verify with the patient directly.
            </p>
          </div>
        )}
      </div>

      {appointment.status !== "COMPLETED" && !submitted && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-lg border bg-white p-4">
          <h2 className="font-semibold">Consultation Notes</h2>
          <textarea placeholder="Clinical notes" className="w-full rounded-md border px-3 py-2" rows={3} {...register("notes", { required: true })} />
          <input placeholder="Diagnosis / assessment" className="w-full rounded-md border px-3 py-2" {...register("diagnosis")} />
          <textarea placeholder="Follow-up instructions" className="w-full rounded-md border px-3 py-2" rows={2} {...register("follow_up_instructions")} />

          <h3 className="font-medium">Prescription</h3>
          {fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-5 gap-2">
              <input placeholder="Medicine" className="col-span-2 rounded-md border px-2 py-1.5 text-sm" {...register(`medications.${index}.medicine_name` as const)} />
              <input placeholder="Dose" className="rounded-md border px-2 py-1.5 text-sm" {...register(`medications.${index}.dose` as const)} />
              <input placeholder="Frequency" className="rounded-md border px-2 py-1.5 text-sm" {...register(`medications.${index}.frequency` as const)} />
              <div className="flex gap-1">
                <input type="number" placeholder="Days" className="w-full rounded-md border px-2 py-1.5 text-sm" {...register(`medications.${index}.duration_days` as const, { valueAsNumber: true })} />
                <button type="button" onClick={() => remove(index)} className="text-red-500">
                  &times;
                </button>
              </div>
            </div>
          ))}
          <button
            type="button"
            onClick={() => append({ medicine_name: "", dose: "", frequency: "Once daily", duration_days: 5 })}
            className="text-sm text-brand-600 hover:underline"
          >
            + Add medication
          </button>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? "Saving..." : "Complete Consultation"}
          </button>
        </form>
      )}

      {(submitted || appointment.status === "COMPLETED") && (
        <p className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
          Consultation recorded. A patient-friendly summary is being generated automatically.
        </p>
      )}
    </div>
  );
}

export default function DoctorAppointmentDetailPage() {
  return (
    <ProtectedRoute allow={["DOCTOR"]}>
      <DetailContent />
    </ProtectedRoute>
  );
}
