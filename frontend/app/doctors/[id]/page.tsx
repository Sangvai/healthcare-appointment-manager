"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { api, apiErrorMessage } from "@/services/api";
import { Doctor, SlotHold } from "@/types";
import { useAuth } from "@/hooks/useAuth";

interface SymptomForm {
  chief_complaint: string;
  symptoms: string;
  duration: string;
  severity: string;
  additional_notes: string;
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function DoctorDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { token, role } = useAuth();

  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [date, setDate] = useState(todayISO());
  const [slots, setSlots] = useState<string[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [hold, setHold] = useState<SlotHold | null>(null);
  const [step, setStep] = useState<"browse" | "symptoms" | "done">("browse");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<SymptomForm>();

  useEffect(() => {
    api.get<Doctor>(`/doctors/${params.id}`).then((res) => setDoctor(res.data));
  }, [params.id]);

  useEffect(() => {
    setLoadingSlots(true);
    api
      .get<{ available_slots: string[] }>(`/doctors/${params.id}/availability`, { params: { date } })
      .then((res) => setSlots(res.data.available_slots))
      .catch(() => setSlots([]))
      .finally(() => setLoadingSlots(false));
  }, [params.id, date]);

  const selectSlot = async (slot: string) => {
    setError(null);
    if (!token) {
      router.push("/login");
      return;
    }
    if (role !== "PATIENT") {
      setError("Only patients can book appointments.");
      return;
    }
    try {
      const { data } = await api.post<SlotHold>("/appointments/hold", {
        doctor_id: Number(params.id),
        start_time: slot,
      });
      setHold(data);
      setStep("symptoms");
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  const onSubmitSymptoms = async (form: SymptomForm) => {
    if (!hold) return;
    setSubmitting(true);
    setError(null);
    try {
      const { data: appointment } = await api.post("/appointments", { hold_id: hold.id });
      await api.post(`/appointments/${appointment.id}/symptoms`, form);
      setStep("done");
    } catch (e) {
      setError(apiErrorMessage(e));
      setStep("browse");
      setHold(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (!doctor) return <p className="text-slate-500">Loading doctor...</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 rounded-lg border bg-white p-4">
        <h1 className="text-2xl font-semibold">{doctor.full_name}</h1>
        <p className="text-slate-500">{doctor.qualification}</p>
        <p className="mt-1 text-sm text-slate-600">
          {doctor.specializations.map((s) => s.name).join(", ") || "General"} &middot;{" "}
          {doctor.experience_years ?? 0} yrs experience
        </p>
      </div>

      {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {step === "browse" && (
        <div className="rounded-lg border bg-white p-4">
          <label className="mb-1 block text-sm font-medium">Select a date</label>
          <input
            type="date"
            value={date}
            min={todayISO()}
            onChange={(e) => setDate(e.target.value)}
            className="mb-4 rounded-md border px-3 py-2"
          />
          {loadingSlots && <p className="text-slate-500">Loading slots...</p>}
          {!loadingSlots && slots.length === 0 && (
            <p className="text-slate-500">No available slots on this date (doctor may be on leave or fully booked).</p>
          )}
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {slots.map((slot) => (
              <button
                key={slot}
                onClick={() => selectSlot(slot)}
                className="rounded-md border px-2 py-2 text-sm hover:border-brand-500 hover:bg-brand-50"
              >
                {new Date(slot).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "symptoms" && hold && (
        <form onSubmit={handleSubmit(onSubmitSymptoms)} className="space-y-4 rounded-lg border bg-white p-4">
          <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            Slot held until {new Date(hold.expires_at).toLocaleTimeString()}. Please complete this form to confirm.
          </p>
          <div>
            <label className="mb-1 block text-sm font-medium">Chief complaint</label>
            <input className="w-full rounded-md border px-3 py-2" {...register("chief_complaint", { required: "Required" })} />
            {errors.chief_complaint && <p className="mt-1 text-sm text-red-600">{errors.chief_complaint.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Symptoms</label>
            <textarea className="w-full rounded-md border px-3 py-2" rows={3} {...register("symptoms", { required: "Required" })} />
            {errors.symptoms && <p className="mt-1 text-sm text-red-600">{errors.symptoms.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Duration</label>
              <input placeholder="e.g. 3 days" className="w-full rounded-md border px-3 py-2" {...register("duration")} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Severity</label>
              <select className="w-full rounded-md border px-3 py-2" {...register("severity")}>
                <option value="">Select</option>
                <option value="Mild">Mild</option>
                <option value="Moderate">Moderate</option>
                <option value="Severe">Severe</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Additional notes (optional)</label>
            <textarea className="w-full rounded-md border px-3 py-2" rows={2} {...register("additional_notes")} />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? "Confirming..." : "Confirm Appointment"}
          </button>
        </form>
      )}

      {step === "done" && (
        <div className="rounded-lg border bg-white p-6 text-center">
          <h2 className="text-xl font-semibold text-emerald-700">Appointment confirmed!</h2>
          <p className="mt-2 text-slate-600">
            A confirmation email is on its way. Your doctor will see an AI-generated summary of your symptoms
            before the visit.
          </p>
          <button
            onClick={() => router.push("/patient/appointments")}
            className="mt-4 rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700"
          >
            View my appointments
          </button>
        </div>
      )}
    </div>
  );
}
