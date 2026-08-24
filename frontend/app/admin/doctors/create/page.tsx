"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useFieldArray, useForm } from "react-hook-form";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, apiErrorMessage } from "@/services/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

interface CreateDoctorForm {
  email: string;
  password: string;
  full_name: string;
  phone: string;
  qualification: string;
  experience_years: number;
  specializations: string;
  working_hours: { day_of_week: number; start_time: string; end_time: string; slot_duration_minutes: number }[];
}

function CreateContent() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { register, control, handleSubmit } = useForm<CreateDoctorForm>({
    defaultValues: {
      working_hours: [{ day_of_week: 0, start_time: "10:00", end_time: "13:00", slot_duration_minutes: 30 }],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "working_hours" });

  const onSubmit = async (values: CreateDoctorForm) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/admin/doctors", {
        ...values,
        experience_years: Number(values.experience_years) || 0,
        specializations: values.specializations.split(",").map((s) => s.trim()).filter(Boolean),
      });
      router.push("/admin/doctors");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold">Add Doctor</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-lg border bg-white p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Full name</label>
            <input className="w-full rounded-md border px-3 py-2" {...register("full_name", { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input type="email" className="w-full rounded-md border px-3 py-2" {...register("email", { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Temporary password</label>
            <input className="w-full rounded-md border px-3 py-2" {...register("password", { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Phone</label>
            <input className="w-full rounded-md border px-3 py-2" {...register("phone")} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Qualification</label>
            <input className="w-full rounded-md border px-3 py-2" {...register("qualification")} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Experience (years)</label>
            <input type="number" className="w-full rounded-md border px-3 py-2" {...register("experience_years")} />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Specializations (comma separated)</label>
          <input placeholder="Cardiology, General Medicine" className="w-full rounded-md border px-3 py-2" {...register("specializations")} />
        </div>

        <h2 className="font-medium">Working Hours</h2>
        {fields.map((field, index) => (
          <div key={field.id} className="grid grid-cols-5 items-center gap-2">
            <select className="col-span-1 rounded-md border px-2 py-1.5 text-sm" {...register(`working_hours.${index}.day_of_week` as const, { valueAsNumber: true })}>
              {DAYS.map((d, i) => (
                <option key={i} value={i}>{d}</option>
              ))}
            </select>
            <input type="time" className="rounded-md border px-2 py-1.5 text-sm" {...register(`working_hours.${index}.start_time` as const)} />
            <input type="time" className="rounded-md border px-2 py-1.5 text-sm" {...register(`working_hours.${index}.end_time` as const)} />
            <input type="number" placeholder="Slot mins" className="rounded-md border px-2 py-1.5 text-sm" {...register(`working_hours.${index}.slot_duration_minutes` as const, { valueAsNumber: true })} />
            <button type="button" onClick={() => remove(index)} className="text-red-500">Remove</button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => append({ day_of_week: 0, start_time: "10:00", end_time: "13:00", slot_duration_minutes: 30 })}
          className="text-sm text-brand-600 hover:underline"
        >
          + Add working day
        </button>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {submitting ? "Creating..." : "Create Doctor"}
        </button>
      </form>
    </div>
  );
}

export default function AdminCreateDoctorPage() {
  return (
    <ProtectedRoute allow={["ADMIN"]}>
      <CreateContent />
    </ProtectedRoute>
  );
}
