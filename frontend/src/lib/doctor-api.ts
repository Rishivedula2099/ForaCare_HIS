/**
 * Thin typed wrapper over `apiClient` for the Doctor Master (P3-F01)
 * backend endpoints, plus the camelCase (frontend `types/doctor.ts`) <->
 * snake_case (backend `DoctorOut`/`DoctorCreateRequest`) mapping.
 */

import { apiClient } from "@/lib/api-client";
import { Doctor, DoctorFormData } from "@/types/doctor";

export interface BackendDoctorOut {
  id: string;
  tenant_id: string;
  facility_id: string;
  department_id: string;
  doctor_code: string;
  full_name: string;
  specialization: string;
  qualification: string | null;
  phone: string | null;
  email: string | null;
  consultation_fee: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  department: { id: string; name: string; code: string };
}

export interface DoctorCreatePayload {
  department_id: string;
  full_name: string;
  specialization: string;
  qualification?: string | null;
  phone?: string | null;
  email?: string | null;
  consultation_fee?: number | null;
}

export type DoctorUpdatePayload = Partial<DoctorCreatePayload> & { is_active?: boolean };

export interface ListDoctorsParams {
  name?: string;
  department_id?: string;
}

export function fromBackendDoctor(doctor: BackendDoctorOut): Doctor {
  return {
    id: doctor.id,
    doctorCode: doctor.doctor_code,
    fullName: doctor.full_name,
    specialization: doctor.specialization,
    qualification: doctor.qualification ?? undefined,
    phone: doctor.phone ?? undefined,
    email: doctor.email ?? undefined,
    consultationFee: doctor.consultation_fee ?? undefined,
    isActive: doctor.is_active,
    departmentId: doctor.department_id,
    departmentName: doctor.department.name,
    departmentCode: doctor.department.code,
    createdAt: doctor.created_at,
    updatedAt: doctor.updated_at,
  };
}

export function toCreatePayload(data: DoctorFormData): DoctorCreatePayload {
  return {
    department_id: data.departmentId,
    full_name: data.fullName.trim(),
    specialization: data.specialization.trim(),
    qualification: data.qualification.trim() || null,
    phone: data.phone.trim() || null,
    email: data.email.trim() || null,
    consultation_fee: data.consultationFee ? Number(data.consultationFee) : null,
  };
}

export async function listDoctors(params: ListDoctorsParams = {}): Promise<Doctor[]> {
  const response = await apiClient.get<BackendDoctorOut[]>("/doctors", { params });
  return (response.data ?? []).map(fromBackendDoctor);
}

export async function createDoctor(payload: DoctorCreatePayload): Promise<Doctor> {
  const response = await apiClient.post<BackendDoctorOut>("/doctors", payload);
  if (!response.data) {
    throw new Error("Failed to create doctor");
  }
  return fromBackendDoctor(response.data);
}

export async function updateDoctor(id: string, payload: DoctorUpdatePayload): Promise<Doctor> {
  const response = await apiClient.patch<BackendDoctorOut>(`/doctors/${id}`, payload);
  if (!response.data) {
    throw new Error("Failed to update doctor");
  }
  return fromBackendDoctor(response.data);
}
