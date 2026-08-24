export type UserRole = "PATIENT" | "DOCTOR" | "ADMIN";

export type AppointmentStatus =
  | "PENDING"
  | "CONFIRMED"
  | "COMPLETED"
  | "CANCELLED"
  | "RESCHEDULED"
  | "NO_SHOW";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: number;
}

export interface Specialization {
  id: number;
  name: string;
}

export interface WorkingHours {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
}

export interface Doctor {
  id: number;
  full_name: string;
  qualification: string | null;
  experience_years: number | null;
  is_active: boolean;
  specializations: Specialization[];
  working_hours: WorkingHours[];
}

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  cancelled_reason: string | null;
}

export interface SlotHold {
  id: number;
  doctor_id: number;
  start_time: string;
  end_time: string;
  expires_at: string;
  status: string;
}

export interface PreVisitSummary {
  urgency_level: "Low" | "Medium" | "High" | null;
  chief_complaint: string | null;
  suggested_questions: string[] | null;
  status: "SUCCESS" | "FAILED" | "PENDING";
  raw_error: string | null;
}

export interface MedicationScheduleItem {
  medicine: string;
  dose: string;
  frequency: string;
  duration: string;
}

export interface PostVisitSummary {
  summary: string | null;
  medication_schedule: MedicationScheduleItem[] | null;
  follow_up_steps: string[] | null;
  status: "SUCCESS" | "FAILED" | "PENDING";
  raw_error: string | null;
}

export interface ApiError {
  success: false;
  message: string;
  error_code: string;
  details: Record<string, unknown>;
}
