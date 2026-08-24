"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";
import { AuthResponse, UserRole } from "@/types";

interface AuthState {
  token: string | null;
  role: UserRole | null;
  userId: number | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, phone?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function persistAuth(data: AuthResponse) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("role", data.role);
  localStorage.setItem("user_id", String(data.user_id));
}

function dashboardPathFor(role: UserRole): string {
  if (role === "PATIENT") return "/patient/dashboard";
  if (role === "DOCTOR") return "/doctor/dashboard";
  return "/admin/dashboard";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ token: null, role: null, userId: null, isLoading: true });

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const role = localStorage.getItem("role") as UserRole | null;
    const userId = localStorage.getItem("user_id");
    setState({ token, role, userId: userId ? Number(userId) : null, isLoading: false });
  }, []);

  const login = async (email: string, password: string) => {
    const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
    persistAuth(data);
    setState({ token: data.access_token, role: data.role, userId: data.user_id, isLoading: false });
    router.push(dashboardPathFor(data.role));
  };

  const register = async (email: string, password: string, fullName: string, phone?: string) => {
    const { data } = await api.post<AuthResponse>("/auth/register", {
      email,
      password,
      full_name: fullName,
      phone,
    });
    persistAuth(data);
    setState({ token: data.access_token, role: data.role, userId: data.user_id, isLoading: false });
    router.push(dashboardPathFor(data.role));
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");
    localStorage.removeItem("user_id");
    setState({ token: null, role: null, userId: null, isLoading: false });
    router.push("/login");
  };

  return <AuthContext.Provider value={{ ...state, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
