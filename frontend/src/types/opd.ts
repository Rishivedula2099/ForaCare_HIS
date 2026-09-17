export const VISIT_TYPES = [
  { value: "WALK_IN", label: "Walk-in" },
  { value: "APPOINTMENT", label: "Appointment" },
] as const;

export type VisitType = (typeof VISIT_TYPES)[number]["value"];

export const TOKEN_PRIORITIES = [
  { value: "NORMAL", label: "Normal" },
  { value: "PRIORITY", label: "Priority" },
] as const;

export type TokenPriority = (typeof TOKEN_PRIORITIES)[number]["value"];

export const TOKEN_STATUSES = {
  WAITING: "WAITING",
  CALLED: "CALLED",
  IN_CONSULTATION: "IN_CONSULTATION",
  COMPLETED: "COMPLETED",
  SKIPPED: "SKIPPED",
  CANCELLED: "CANCELLED",
} as const;

export type TokenStatus = (typeof TOKEN_STATUSES)[keyof typeof TOKEN_STATUSES];

/** Maps each token status to the closest `Badge` variant already defined in
 * `components/ui/badge.tsx`, so status colors stay consistent with the rest
 * of the app instead of introducing a parallel palette. */
export const TOKEN_STATUS_BADGE_VARIANT: Record<TokenStatus, "waiting" | "active" | "completed" | "alert"> = {
  WAITING: "waiting",
  CALLED: "active",
  IN_CONSULTATION: "active",
  COMPLETED: "completed",
  SKIPPED: "alert",
  CANCELLED: "alert",
};

export const TOKEN_STATUS_LABEL: Record<TokenStatus, string> = {
  WAITING: "Waiting",
  CALLED: "Called",
  IN_CONSULTATION: "In Consultation",
  COMPLETED: "Completed",
  SKIPPED: "Skipped",
  CANCELLED: "Cancelled",
};

export interface OPDToken {
  id: string;
  tokenNumber: number;
  tokenDate: string;
  status: TokenStatus;
  priority: TokenPriority;
  calledAt?: string;
  startedAt?: string;
  completedAt?: string;
}

export const QR_STATUSES = {
  ACTIVE: "ACTIVE",
  REVOKED: "REVOKED",
} as const;

export type QRStatus = (typeof QR_STATUSES)[keyof typeof QR_STATUSES];

/** Why a scanned/entered QR did or didn't verify. */
export type QRVerifyReason = "OK" | "INVALID" | "EXPIRED" | "REVOKED";

export interface OPDEncounter {
  id: string;
  encounterNumber: string;
  visitType: VisitType;
  status: string;
  notes?: string;
  scheduledAt?: string;
  createdAt: string;
  patient: {
    id: string;
    uid: string;
    mrn: string;
    fullName: string;
    gender: string;
    dob: string;
  };
  department: { id: string; name: string; code: string };
  doctor: { id: string; doctorCode: string; fullName: string; specialization: string };
  token?: OPDToken;
  qrCode: string;
  qrStatus: QRStatus;
  qrExpiresAt: string;
}

export interface QRVerifyResult {
  valid: boolean;
  reason: QRVerifyReason;
  encounter?: OPDEncounter;
}

export interface OPDRegistrationFormState {
  patientId: string;
  departmentId: string;
  doctorId: string;
  visitType: VisitType;
  priority: TokenPriority;
  notes: string;
}

export const CONSULTATION_STATUSES = {
  IN_PROGRESS: "IN_PROGRESS",
  COMPLETED: "COMPLETED",
} as const;

export type ConsultationStatus = (typeof CONSULTATION_STATUSES)[keyof typeof CONSULTATION_STATUSES];

export interface Vitals {
  temperatureCelsius?: number;
  pulseBpm?: number;
  bpSystolic?: number;
  bpDiastolic?: number;
  spo2Percent?: number;
  respiratoryRate?: number;
  weightKg?: number;
  heightCm?: number;
}

export interface Consultation {
  id: string;
  encounterId: string;
  doctorId: string;
  status: ConsultationStatus;
  chiefComplaint?: string;
  history?: string;
  examination?: string;
  diagnosis?: string;
  allergies?: string;
  investigation?: string;
  treatment?: string;
  notes?: string;
  vitals: Vitals;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
  updatedAt: string;
  encounter: OPDEncounter;
  doctor: { id: string; doctorCode: string; fullName: string; specialization: string };
}

/** Every field is a plain string (including vitals) so controlled `<input>`
 * values never need a null/undefined branch - parsed to numbers only when
 * building the API payload. */
export interface ConsultationFormState {
  chiefComplaint: string;
  history: string;
  examination: string;
  diagnosis: string;
  allergies: string;
  investigation: string;
  treatment: string;
  notes: string;
  temperatureCelsius: string;
  pulseBpm: string;
  bpSystolic: string;
  bpDiastolic: string;
  spo2Percent: string;
  respiratoryRate: string;
  weightKg: string;
  heightCm: string;
}

export const EMPTY_CONSULTATION_FORM: ConsultationFormState = {
  chiefComplaint: "",
  history: "",
  examination: "",
  diagnosis: "",
  allergies: "",
  investigation: "",
  treatment: "",
  notes: "",
  temperatureCelsius: "",
  pulseBpm: "",
  bpSystolic: "",
  bpDiastolic: "",
  spo2Percent: "",
  respiratoryRate: "",
  weightKg: "",
  heightCm: "",
};

export const DRUG_ROUTES = [
  { value: "ORAL", label: "Oral" },
  { value: "IV", label: "IV" },
  { value: "IM", label: "IM" },
  { value: "SC", label: "Subcutaneous" },
  { value: "TOPICAL", label: "Topical" },
  { value: "INHALATION", label: "Inhalation" },
  { value: "SUBLINGUAL", label: "Sublingual" },
  { value: "RECTAL", label: "Rectal" },
  { value: "OTHER", label: "Other" },
] as const;

export type DrugRoute = (typeof DRUG_ROUTES)[number]["value"];

export interface PrescriptionItem {
  id: string;
  drugName: string;
  dosage: string;
  route: DrugRoute;
  frequency: string;
  duration: string;
  instructions?: string;
}

export interface Prescription {
  id: string;
  consultationId: string;
  doctorId: string;
  items: PrescriptionItem[];
  createdAt: string;
  updatedAt: string;
  doctor: { id: string; doctorCode: string; fullName: string; specialization: string };
}

/** One editable row in the prescription form - a client-only `key` (not
 * sent to the API) so React can key/remove rows before they have a
 * server-assigned id. */
export interface PrescriptionItemFormRow {
  key: string;
  drugName: string;
  dosage: string;
  route: DrugRoute;
  frequency: string;
  duration: string;
  instructions: string;
}

export function emptyPrescriptionItemRow(): PrescriptionItemFormRow {
  return {
    key: Math.random().toString(36).slice(2),
    drugName: "",
    dosage: "",
    route: "ORAL",
    frequency: "",
    duration: "",
    instructions: "",
  };
}
