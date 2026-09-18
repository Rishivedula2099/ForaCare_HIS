export const WARD_TYPES = [
  { value: "GENERAL", label: "General" },
  { value: "ICU", label: "ICU" },
  { value: "PRIVATE", label: "Private" },
  { value: "SEMI_PRIVATE", label: "Semi-Private" },
  { value: "ISOLATION", label: "Isolation" },
] as const;
export type WardType = (typeof WARD_TYPES)[number]["value"];

export const ROOM_TYPES = WARD_TYPES;
export type RoomType = WardType;

export type BedStatus = "AVAILABLE" | "OCCUPIED" | "RESERVED" | "MAINTENANCE" | "CLEANING" | "BLOCKED";

export const BED_STATUSES: { value: BedStatus; label: string }[] = [
  { value: "AVAILABLE", label: "Available" },
  { value: "OCCUPIED", label: "Occupied" },
  { value: "RESERVED", label: "Reserved" },
  { value: "MAINTENANCE", label: "Maintenance" },
  { value: "CLEANING", label: "Cleaning" },
  { value: "BLOCKED", label: "Blocked" },
];

export const BED_STATUS_BADGE_CLASS: Record<BedStatus, string> = {
  AVAILABLE: "bg-emerald-50 text-emerald-700 border-emerald-300",
  OCCUPIED: "bg-rose-50 text-rose-700 border-rose-300",
  RESERVED: "bg-amber-50 text-amber-700 border-amber-300",
  MAINTENANCE: "bg-slate-100 text-slate-500 border-slate-300",
  CLEANING: "bg-sky-50 text-sky-700 border-sky-300",
  BLOCKED: "bg-violet-50 text-violet-700 border-violet-300",
};

// Mirrors `BED_TRANSITIONS` in backend/app/modules/ipd/service.py (P4-B02).
// Used only to offer sensible options in the bed-status-change dialog; the
// backend is the source of truth and rejects anything outside this map with
// `INVALID_TRANSITION`.
export const BED_STATUS_TRANSITIONS: Record<BedStatus, BedStatus[]> = {
  AVAILABLE: ["RESERVED", "MAINTENANCE", "BLOCKED"],
  RESERVED: ["AVAILABLE", "BLOCKED"],
  OCCUPIED: [],
  CLEANING: ["AVAILABLE", "MAINTENANCE", "BLOCKED"],
  MAINTENANCE: ["AVAILABLE", "BLOCKED"],
  BLOCKED: ["AVAILABLE", "MAINTENANCE"],
};

export interface Ward {
  id: string;
  departmentId?: string;
  name: string;
  code: string;
  wardType: WardType;
  floor?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface WardFormData {
  departmentId: string;
  name: string;
  code: string;
  wardType: WardType;
  floor: string;
}

export interface Room {
  id: string;
  wardId: string;
  roomNumber: string;
  roomType: RoomType;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  ward: Ward;
}

export interface RoomFormData {
  wardId: string;
  roomNumber: string;
  roomType: RoomType;
}

export interface BedOccupantPatient {
  id: string;
  uid: string;
  mrn: string;
  fullName: string;
  gender: string;
  dob: string;
}

export interface BedOccupant {
  admissionId: string;
  admissionNumber: string;
  admittedAt: string;
  patient: BedOccupantPatient;
}

export interface Bed {
  id: string;
  wardId: string;
  roomId: string;
  bedNumber: string;
  status: BedStatus;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  ward: Ward;
  room: Room;
  currentOccupant?: BedOccupant;
}

export interface BedFormData {
  wardId: string;
  roomId: string;
  bedNumber: string;
}

export const ADMISSION_TYPES = [
  { value: "ELECTIVE", label: "Elective" },
  { value: "EMERGENCY", label: "Emergency" },
  { value: "TRANSFER_IN", label: "Transfer In" },
] as const;
export type AdmissionType = (typeof ADMISSION_TYPES)[number]["value"];

export type AdmissionStatus = "ADMITTED" | "DISCHARGED" | "CANCELLED";

export const REFERRAL_SOURCES = [
  { value: "SELF", label: "Self" },
  { value: "DOCTOR", label: "Referring Doctor" },
  { value: "HOSPITAL", label: "Referring Hospital" },
  { value: "CAMP", label: "Health Camp" },
  { value: "INSURANCE_TPA", label: "Insurance / TPA" },
  { value: "OTHER", label: "Other" },
] as const;
export type ReferralSource = (typeof REFERRAL_SOURCES)[number]["value"];

export const PAYMENT_CATEGORIES = [
  { value: "CASH", label: "Cash" },
  { value: "INSURANCE", label: "Insurance" },
  { value: "CORPORATE", label: "Corporate" },
  { value: "GOVERNMENT_SCHEME", label: "Government Scheme" },
] as const;
export type PaymentCategory = (typeof PAYMENT_CATEGORIES)[number]["value"];

export const PAYMENT_MODES = [
  { value: "CASH", label: "Cash" },
  { value: "CARD", label: "Card" },
  { value: "UPI", label: "UPI" },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "CHEQUE", label: "Cheque" },
] as const;
export type PaymentMode = (typeof PAYMENT_MODES)[number]["value"];

export interface Deposit {
  id: string;
  admissionId: string;
  amount: number;
  paymentMode: PaymentMode;
  notes?: string;
  recordedAt: string;
}

export interface BedAssignment {
  id: string;
  admissionId: string;
  bedId: string;
  status: "ACTIVE" | "RELEASED";
  assignedAt: string;
  releasedAt?: string;
  bed: Bed;
}

export interface Admission {
  id: string;
  patientId: string;
  admittingDoctorId?: string;
  departmentId?: string;
  admissionNumber: string;
  admissionType: AdmissionType;
  status: AdmissionStatus;
  referralSource: ReferralSource;
  referralDetail?: string;
  paymentCategory: PaymentCategory;
  notes?: string;
  admittedAt: string;
  bedAssignments: BedAssignment[];
  deposits: Deposit[];
}

export const DISCHARGE_TYPES = [
  { value: "NORMAL", label: "Normal" },
  { value: "DAMA", label: "Discharge Against Medical Advice" },
  { value: "TRANSFER_OUT", label: "Transfer Out" },
  { value: "DEATH", label: "Death" },
] as const;
export type DischargeType = (typeof DISCHARGE_TYPES)[number]["value"];

export interface Discharge {
  id: string;
  admissionId: string;
  dischargeType: DischargeType;
  dischargeCondition?: string;
  dischargeSummary?: string;
  followUpInstructions?: string;
  dischargedAt: string;
}

export const CONSENT_TYPES = [
  { value: "GENERAL_ADMISSION", label: "General Admission Consent" },
  { value: "SURGICAL", label: "Surgical Consent" },
  { value: "ANESTHESIA", label: "Anesthesia Consent" },
  { value: "HIGH_RISK", label: "High-Risk Consent" },
  { value: "BLOOD_TRANSFUSION", label: "Blood Transfusion Consent" },
] as const;
export type ConsentType = (typeof CONSENT_TYPES)[number]["value"];

export interface Consent {
  id: string;
  admissionId: string;
  consentType: ConsentType;
  consentGiven: boolean;
  givenByName: string;
  relationshipToPatient?: string;
  notes?: string;
  recordedAt: string;
}
