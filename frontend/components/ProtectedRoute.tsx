"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { UserRole } from "@/types";

export default function ProtectedRoute({ allow, children }: { allow: UserRole[]; children: ReactNode }) {
  const { token, role, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    if (role && !allow.includes(role)) {
      router.replace("/login");
    }
  }, [isLoading, token, role, allow, router]);

  if (isLoading || !token || (role && !allow.includes(role))) {
    return <div className="p-8 text-center text-slate-500">Loading...</div>;
  }
  return <>{children}</>;
}
