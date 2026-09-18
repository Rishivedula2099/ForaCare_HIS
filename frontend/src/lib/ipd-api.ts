/**
 * Thin typed wrapper over `apiClient` for the IPD Ward/Room/Bed (P4-B01/
 * P4-F01) backend endpoints, plus the camelCase (frontend `types/ipd.ts`)
 * <-> snake_case (backend `WardOut`/`RoomOut`/`BedOut`/...) mapping.
 */

import { apiClient } from "@/lib/api-client";
import {
  Admission,
  AdmissionStatus,
  AdmissionType,
  Bed,
  BedFormData,
  BedOccupant,
  BedStatus,
  Room,
  RoomFormData,
  RoomType,
  Ward,
  WardFormData,
  WardType,
} from "@/types/ipd";

// ---------------------------------------------------------------------------
// Backend shapes (snake_case)
// ---------------------------------------------------------------------------

export interface BackendWardOut {
  id: string;
  department_id: string | null;
  name: string;
  code: string;
  ward_type: string;
  floor: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackendRoomOut {
  id: string;
  ward_id: string;
  room_number: string;
  room_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  ward: BackendWardOut;
}

interface BackendPatientSummary {
  id: string;
  uid: string;
  mrn: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  gender: string;
  dob: string;
}

interface BackendCurrentOccupant {
  admission_id: string;
  admission_number: string;
  admitted_at: string;
  patient: BackendPatientSummary;
}

export interface BackendBedOut {
  id: string;
  ward_id: string;
  room_id: string;
  bed_number: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  ward: BackendWardOut;
  room: BackendRoomOut;
  current_occupant: BackendCurrentOccupant | null;
}

export interface BackendAdmissionOut {
  id: string;
  patient_id: string;
  admitting_doctor_id: string | null;
  department_id: string | null;
  admission_number: string;
  admission_type: string;
  status: string;
  notes: string | null;
  admitted_at: string;
}

// ---------------------------------------------------------------------------
// Mapping
// ---------------------------------------------------------------------------

export function fromBackendWard(ward: BackendWardOut): Ward {
  return {
    id: ward.id,
    departmentId: ward.department_id ?? undefined,
    name: ward.name,
    code: ward.code,
    wardType: ward.ward_type as WardType,
    floor: ward.floor ?? undefined,
    isActive: ward.is_active,
    createdAt: ward.created_at,
    updatedAt: ward.updated_at,
  };
}

export function fromBackendRoom(room: BackendRoomOut): Room {
  return {
    id: room.id,
    wardId: room.ward_id,
    roomNumber: room.room_number,
    roomType: room.room_type as RoomType,
    isActive: room.is_active,
    createdAt: room.created_at,
    updatedAt: room.updated_at,
    ward: fromBackendWard(room.ward),
  };
}

function fromBackendOccupant(occupant: BackendCurrentOccupant): BedOccupant {
  const patient = occupant.patient;
  return {
    admissionId: occupant.admission_id,
    admissionNumber: occupant.admission_number,
    admittedAt: occupant.admitted_at,
    patient: {
      id: patient.id,
      uid: patient.uid,
      mrn: patient.mrn,
      fullName: [patient.first_name, patient.middle_name, patient.last_name].filter(Boolean).join(" "),
      gender: patient.gender,
      dob: patient.dob,
    },
  };
}

export function fromBackendBed(bed: BackendBedOut): Bed {
  return {
    id: bed.id,
    wardId: bed.ward_id,
    roomId: bed.room_id,
    bedNumber: bed.bed_number,
    status: bed.status as BedStatus,
    isActive: bed.is_active,
    createdAt: bed.created_at,
    updatedAt: bed.updated_at,
    ward: fromBackendWard(bed.ward),
    room: fromBackendRoom(bed.room),
    currentOccupant: bed.current_occupant ? fromBackendOccupant(bed.current_occupant) : undefined,
  };
}

export function fromBackendAdmission(admission: BackendAdmissionOut): Admission {
  return {
    id: admission.id,
    patientId: admission.patient_id,
    admittingDoctorId: admission.admitting_doctor_id ?? undefined,
    departmentId: admission.department_id ?? undefined,
    admissionNumber: admission.admission_number,
    admissionType: admission.admission_type as AdmissionType,
    status: admission.status as AdmissionStatus,
    notes: admission.notes ?? undefined,
    admittedAt: admission.admitted_at,
  };
}

export function toWardCreatePayload(data: WardFormData) {
  return {
    department_id: data.departmentId || null,
    name: data.name.trim(),
    code: data.code.trim().toUpperCase(),
    ward_type: data.wardType,
    floor: data.floor.trim() || null,
  };
}

export function toRoomCreatePayload(data: RoomFormData) {
  return {
    ward_id: data.wardId,
    room_number: data.roomNumber.trim(),
    room_type: data.roomType,
  };
}

export function toBedCreatePayload(data: BedFormData) {
  return {
    ward_id: data.wardId,
    room_id: data.roomId,
    bed_number: data.bedNumber.trim(),
  };
}

// ---------------------------------------------------------------------------
// Ward
// ---------------------------------------------------------------------------

export async function listWards(): Promise<Ward[]> {
  const response = await apiClient.get<BackendWardOut[]>("/ipd/wards");
  return (response.data ?? []).map(fromBackendWard);
}

export async function createWard(payload: ReturnType<typeof toWardCreatePayload>): Promise<Ward> {
  const response = await apiClient.post<BackendWardOut>("/ipd/wards", payload);
  if (!response.data) throw new Error("Failed to create ward");
  return fromBackendWard(response.data);
}

export async function updateWard(
  id: string,
  payload: Partial<ReturnType<typeof toWardCreatePayload>> & { is_active?: boolean }
): Promise<Ward> {
  const response = await apiClient.patch<BackendWardOut>(`/ipd/wards/${id}`, payload);
  if (!response.data) throw new Error("Failed to update ward");
  return fromBackendWard(response.data);
}

// ---------------------------------------------------------------------------
// Room
// ---------------------------------------------------------------------------

export async function listRooms(params: { ward_id?: string } = {}): Promise<Room[]> {
  const response = await apiClient.get<BackendRoomOut[]>("/ipd/rooms", { params });
  return (response.data ?? []).map(fromBackendRoom);
}

export async function createRoom(payload: ReturnType<typeof toRoomCreatePayload>): Promise<Room> {
  const response = await apiClient.post<BackendRoomOut>("/ipd/rooms", payload);
  if (!response.data) throw new Error("Failed to create room");
  return fromBackendRoom(response.data);
}

export async function updateRoom(
  id: string,
  payload: Partial<Pick<ReturnType<typeof toRoomCreatePayload>, "room_number" | "room_type">> & {
    is_active?: boolean;
  }
): Promise<Room> {
  const response = await apiClient.patch<BackendRoomOut>(`/ipd/rooms/${id}`, payload);
  if (!response.data) throw new Error("Failed to update room");
  return fromBackendRoom(response.data);
}

// ---------------------------------------------------------------------------
// Bed
// ---------------------------------------------------------------------------

export interface ListBedsParams {
  ward_id?: string;
  room_id?: string;
  status?: BedStatus;
}

export async function listBeds(params: ListBedsParams = {}): Promise<Bed[]> {
  const response = await apiClient.get<BackendBedOut[]>("/ipd/beds", { params });
  return (response.data ?? []).map(fromBackendBed);
}

export async function createBed(payload: ReturnType<typeof toBedCreatePayload>): Promise<Bed> {
  const response = await apiClient.post<BackendBedOut>("/ipd/beds", payload);
  if (!response.data) throw new Error("Failed to create bed");
  return fromBackendBed(response.data);
}

export async function updateBedStatus(id: string, status: BedStatus): Promise<Bed> {
  const response = await apiClient.patch<BackendBedOut>(`/ipd/beds/${id}`, { status });
  if (!response.data) throw new Error("Failed to update bed");
  return fromBackendBed(response.data);
}

// ---------------------------------------------------------------------------
// Admission / Transfer / Discharge
// ---------------------------------------------------------------------------

export interface AdmitPatientPayload {
  patient_id: string;
  bed_id: string;
  admission_type: AdmissionType;
  notes?: string | null;
}

export async function admitPatient(payload: AdmitPatientPayload): Promise<Admission> {
  const response = await apiClient.post<BackendAdmissionOut>("/ipd/admissions", payload);
  if (!response.data) throw new Error("Failed to admit patient");
  return fromBackendAdmission(response.data);
}

export async function transferAdmission(
  admissionId: string,
  payload: { to_bed_id: string; reason?: string | null }
): Promise<void> {
  await apiClient.post(`/ipd/admissions/${admissionId}/transfer`, payload);
}

export interface DischargePayload {
  discharge_type: string;
  discharge_condition?: string | null;
  discharge_summary?: string | null;
  follow_up_instructions?: string | null;
}

export async function dischargeAdmission(admissionId: string, payload: DischargePayload): Promise<void> {
  await apiClient.post(`/ipd/admissions/${admissionId}/discharge`, payload);
}
