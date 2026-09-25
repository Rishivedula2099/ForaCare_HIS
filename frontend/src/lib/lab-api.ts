/**
 * Thin typed wrapper over `apiClient` for the Lab Master (P6-F01) backend
 * endpoints (backend/app/api/v1/lab.py), plus the camelCase
 * (frontend `types/lab.ts`) <-> snake_case (backend `*Out`/`*Request`)
 * mapping.
 */

import { apiClient } from "@/lib/api-client";
import {
  LabParameter,
  LabParameterFormData,
  LabReferenceRange,
  LabReferenceRangeFormData,
  LabTest,
  LabTestFormData,
} from "@/types/lab";

// ---------------------------------------------------------------------------
// Backend shapes (snake_case)
// ---------------------------------------------------------------------------

export interface BackendTestOut {
  id: string;
  department_id: string | null;
  test_code: string;
  name: string;
  specimen_type: string;
  container_type: string;
  tat_minutes: number;
  unit_price: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackendParameterOut {
  id: string;
  test_id: string;
  parameter_code: string;
  name: string;
  unit: string | null;
  sequence_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackendReferenceRangeOut {
  id: string;
  parameter_id: string;
  gender: string;
  age_min_days: number;
  age_max_days: number | null;
  normal_min: number;
  normal_max: number;
  critical_low: number | null;
  critical_high: number | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// snake_case <-> camelCase mapping
// ---------------------------------------------------------------------------

export function fromBackendTest(test: BackendTestOut): LabTest {
  return {
    id: test.id,
    departmentId: test.department_id ?? undefined,
    testCode: test.test_code,
    name: test.name,
    specimenType: test.specimen_type as LabTest["specimenType"],
    containerType: test.container_type as LabTest["containerType"],
    tatMinutes: test.tat_minutes,
    unitPrice: Number(test.unit_price),
    isActive: test.is_active,
    createdAt: test.created_at,
    updatedAt: test.updated_at,
  };
}

export function fromBackendParameter(parameter: BackendParameterOut): LabParameter {
  return {
    id: parameter.id,
    testId: parameter.test_id,
    parameterCode: parameter.parameter_code,
    name: parameter.name,
    unit: parameter.unit ?? undefined,
    sequenceOrder: parameter.sequence_order,
    isActive: parameter.is_active,
    createdAt: parameter.created_at,
    updatedAt: parameter.updated_at,
  };
}

export function fromBackendReferenceRange(range: BackendReferenceRangeOut): LabReferenceRange {
  return {
    id: range.id,
    parameterId: range.parameter_id,
    gender: range.gender as LabReferenceRange["gender"],
    ageMinDays: range.age_min_days,
    ageMaxDays: range.age_max_days ?? undefined,
    normalMin: Number(range.normal_min),
    normalMax: Number(range.normal_max),
    criticalLow: range.critical_low === null ? undefined : Number(range.critical_low),
    criticalHigh: range.critical_high === null ? undefined : Number(range.critical_high),
    createdAt: range.created_at,
    updatedAt: range.updated_at,
  };
}

export function toTestCreatePayload(data: LabTestFormData) {
  return {
    test_code: data.testCode.trim().toUpperCase(),
    name: data.name.trim(),
    specimen_type: data.specimenType,
    container_type: data.containerType,
    department_id: data.departmentId || null,
    tat_minutes: Number(data.tatMinutes || "60"),
    unit_price: Number(data.unitPrice || "0"),
  };
}

export function toParameterCreatePayload(data: LabParameterFormData) {
  return {
    parameter_code: data.parameterCode.trim().toUpperCase(),
    name: data.name.trim(),
    unit: data.unit.trim() || null,
    sequence_order: Number(data.sequenceOrder || "0"),
  };
}

export function toReferenceRangeCreatePayload(data: LabReferenceRangeFormData) {
  return {
    gender: data.gender,
    age_min_days: Number(data.ageMinDays || "0"),
    age_max_days: data.ageMaxDays.trim() === "" ? null : Number(data.ageMaxDays),
    normal_min: Number(data.normalMin),
    normal_max: Number(data.normalMax),
    critical_low: data.criticalLow.trim() === "" ? null : Number(data.criticalLow),
    critical_high: data.criticalHigh.trim() === "" ? null : Number(data.criticalHigh),
  };
}

// ---------------------------------------------------------------------------
// Test master
// ---------------------------------------------------------------------------

export interface ListTestsParams {
  name?: string;
  is_active?: boolean;
}

export async function listTests(params: ListTestsParams = {}): Promise<LabTest[]> {
  const response = await apiClient.get<BackendTestOut[]>("/lab/tests", { params });
  return (response.data ?? []).map(fromBackendTest);
}

export async function getTest(id: string): Promise<LabTest> {
  const response = await apiClient.get<BackendTestOut>(`/lab/tests/${id}`);
  if (!response.data) throw new Error("Test not found");
  return fromBackendTest(response.data);
}

export async function createTest(payload: ReturnType<typeof toTestCreatePayload>): Promise<LabTest> {
  const response = await apiClient.post<BackendTestOut>("/lab/tests", payload);
  if (!response.data) throw new Error("Failed to create test");
  return fromBackendTest(response.data);
}

export async function updateTest(
  id: string,
  payload: Partial<ReturnType<typeof toTestCreatePayload>> & { is_active?: boolean }
): Promise<LabTest> {
  const response = await apiClient.patch<BackendTestOut>(`/lab/tests/${id}`, payload);
  if (!response.data) throw new Error("Failed to update test");
  return fromBackendTest(response.data);
}

// ---------------------------------------------------------------------------
// Parameter master
// ---------------------------------------------------------------------------

export async function listParameters(testId: string): Promise<LabParameter[]> {
  const response = await apiClient.get<BackendParameterOut[]>(`/lab/tests/${testId}/parameters`);
  return (response.data ?? []).map(fromBackendParameter);
}

export async function createParameter(
  testId: string,
  payload: ReturnType<typeof toParameterCreatePayload>
): Promise<LabParameter> {
  const response = await apiClient.post<BackendParameterOut>(`/lab/tests/${testId}/parameters`, payload);
  if (!response.data) throw new Error("Failed to create parameter");
  return fromBackendParameter(response.data);
}

export async function updateParameter(
  id: string,
  payload: Partial<ReturnType<typeof toParameterCreatePayload>> & { is_active?: boolean }
): Promise<LabParameter> {
  const response = await apiClient.patch<BackendParameterOut>(`/lab/parameters/${id}`, payload);
  if (!response.data) throw new Error("Failed to update parameter");
  return fromBackendParameter(response.data);
}

// ---------------------------------------------------------------------------
// ReferenceRange master
// ---------------------------------------------------------------------------

export async function listReferenceRanges(parameterId: string): Promise<LabReferenceRange[]> {
  const response = await apiClient.get<BackendReferenceRangeOut[]>(
    `/lab/parameters/${parameterId}/reference-ranges`
  );
  return (response.data ?? []).map(fromBackendReferenceRange);
}

export async function createReferenceRange(
  parameterId: string,
  payload: ReturnType<typeof toReferenceRangeCreatePayload>
): Promise<LabReferenceRange> {
  const response = await apiClient.post<BackendReferenceRangeOut>(
    `/lab/parameters/${parameterId}/reference-ranges`,
    payload
  );
  if (!response.data) throw new Error("Failed to create reference range");
  return fromBackendReferenceRange(response.data);
}

export async function updateReferenceRange(
  id: string,
  payload: Partial<ReturnType<typeof toReferenceRangeCreatePayload>>
): Promise<LabReferenceRange> {
  const response = await apiClient.patch<BackendReferenceRangeOut>(`/lab/reference-ranges/${id}`, payload);
  if (!response.data) throw new Error("Failed to update reference range");
  return fromBackendReferenceRange(response.data);
}
