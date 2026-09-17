/**
 * Thin typed wrapper over `apiClient` for the Department Master (P3-F01)
 * backend endpoints, plus the camelCase (frontend `types/department.ts`) <->
 * snake_case (backend `DepartmentOut`/`DepartmentCreateRequest`) mapping.
 */

import { apiClient } from "@/lib/api-client";
import { Department, DepartmentFormData } from "@/types/department";

export interface BackendDepartmentOut {
  id: string;
  tenant_id: string;
  facility_id: string;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DepartmentCreatePayload {
  name: string;
  code: string;
  description?: string | null;
}

export type DepartmentUpdatePayload = Partial<DepartmentCreatePayload> & { is_active?: boolean };

export interface ListDepartmentsParams {
  name?: string;
}

export function fromBackendDepartment(department: BackendDepartmentOut): Department {
  return {
    id: department.id,
    name: department.name,
    code: department.code,
    description: department.description ?? undefined,
    isActive: department.is_active,
    createdAt: department.created_at,
    updatedAt: department.updated_at,
  };
}

export function toCreatePayload(data: DepartmentFormData): DepartmentCreatePayload {
  return {
    name: data.name.trim(),
    code: data.code.trim().toUpperCase(),
    description: data.description.trim() || null,
  };
}

export async function listDepartments(params: ListDepartmentsParams = {}): Promise<Department[]> {
  const response = await apiClient.get<BackendDepartmentOut[]>("/departments", { params });
  return (response.data ?? []).map(fromBackendDepartment);
}

export async function createDepartment(payload: DepartmentCreatePayload): Promise<Department> {
  const response = await apiClient.post<BackendDepartmentOut>("/departments", payload);
  if (!response.data) {
    throw new Error("Failed to create department");
  }
  return fromBackendDepartment(response.data);
}

export async function updateDepartment(
  id: string,
  payload: DepartmentUpdatePayload
): Promise<Department> {
  const response = await apiClient.patch<BackendDepartmentOut>(`/departments/${id}`, payload);
  if (!response.data) {
    throw new Error("Failed to update department");
  }
  return fromBackendDepartment(response.data);
}
