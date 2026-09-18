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

export interface Admission {
  id: string;
  patientId: string;
  admittingDoctorId?: string;
  departmentId?: string;
  admissionNumber: string;
  admissionType: AdmissionType;
  status: AdmissionStatus;
  notes?: string;
  admittedAt: string;
}

export const DISCHARGE_TYPES = [
  { value: "NORMAL", label: "Normal" },
  { value: "DAMA", label: "Discharge Against Medical Advice" },
  { value: "TRANSFER_OUT", label: "Transfer Out" },
  { value: "DEATH", label: "Death" },
] as const;
