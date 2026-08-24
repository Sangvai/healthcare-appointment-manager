"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { useAuth } from "@/hooks/useAuth";
import { apiErrorMessage } from "@/services/api";

interface RegisterForm {
  full_name: string;
  email: string;
  password: string;
  phone?: string;
}

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (data: RegisterForm) => {
    setError(null);
    setSubmitting(true);
    try {
      await registerUser(data.email, data.password, data.full_name, data.phone);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-6 text-2xl font-semibold">Create your patient account</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Full name</label>
          <input className="w-full rounded-md border px-3 py-2" {...register("full_name", { required: "Required" })} />
          {errors.full_name && <p className="mt-1 text-sm text-red-600">{errors.full_name.message}</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <input type="email" className="w-full rounded-md border px-3 py-2" {...register("email", { required: "Required" })} />
          {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Phone (optional)</label>
          <input className="w-full rounded-md border px-3 py-2" {...register("phone")} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Password</label>
          <input
            type="password"
            className="w-full rounded-md border px-3 py-2"
            {...register("password", { required: "Required", minLength: { value: 8, message: "Min 8 characters" } })}
          />
          {errors.password && <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {submitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        Already have an account? <Link href="/login" className="text-brand-600 hover:underline">Log in</Link>
      </p>
    </div>
  );
}
