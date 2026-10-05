/**
 * Thin typed wrapper over `apiClient` for the Lab Master (P6-F01) backend
 * endpoints (backend/app/api/v1/lab.py), plus the camelCase
 * (frontend `types/lab.ts`) <-> snake_case (backend `*Out`/`*Request`)
 * mapping.
 */

import { apiClient } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import {
  Accession,
  Approval,
  BarcodeResolution,
  LabOrder,
  LabOrderStatus,
  LabParameter,
  LabParameterFormData,
  LabReferenceRange,
  LabReferenceRangeFormData,
  LabReport,
  LabTest,
  LabTestFormData,
  Result,
  ResultEntryField,
  ResultEntryForm,
  ResultFlag,
  ResultVersionEntry,
  Sample,
  Verification,
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

// ---------------------------------------------------------------------------
// LabOrder (P6-B02) / Accession / Sample (P6-B03)
// ---------------------------------------------------------------------------

export interface BackendLabOrderOut {
  id: string;
  patient_id: string;
  test_id: string;
  accession_id: string | null;
  sample_id: string | null;
  order_number: string;
  status: string;
  priority: string;
  clinical_notes: string | null;
  ordered_at: string;
}

export interface BackendAccessionOut {
  id: string;
  patient_id: string;
  accessioned_by: string | null;
  accession_number: string;
  status: string;
  accessioned_at: string;
}

export interface BackendSampleOut {
  id: string;
  accession_id: string;
  collected_by: string | null;
  barcode_id: string;
  specimen_type: string;
  container_type: string;
  status: string;
  rejection_reason: string | null;
  collected_at: string | null;
}

export interface BackendBarcodeResolveResponse {
  code_type: "ACCESSION" | "SAMPLE";
  accession: BackendAccessionOut;
  sample: BackendSampleOut | null;
  lab_orders: BackendLabOrderOut[];
}

export function fromBackendLabOrder(order: BackendLabOrderOut): LabOrder {
  return {
    id: order.id,
    patientId: order.patient_id,
    testId: order.test_id,
    accessionId: order.accession_id ?? undefined,
    sampleId: order.sample_id ?? undefined,
    orderNumber: order.order_number,
    status: order.status as LabOrderStatus,
    priority: order.priority,
    clinicalNotes: order.clinical_notes ?? undefined,
    orderedAt: order.ordered_at,
  };
}

export function fromBackendAccession(accession: BackendAccessionOut): Accession {
  return {
    id: accession.id,
    patientId: accession.patient_id,
    accessionedBy: accession.accessioned_by ?? undefined,
    accessionNumber: accession.accession_number,
    status: accession.status,
    accessionedAt: accession.accessioned_at,
  };
}

export function fromBackendSample(sample: BackendSampleOut): Sample {
  return {
    id: sample.id,
    accessionId: sample.accession_id,
    collectedBy: sample.collected_by ?? undefined,
    barcodeId: sample.barcode_id,
    specimenType: sample.specimen_type as Sample["specimenType"],
    containerType: sample.container_type as Sample["containerType"],
    status: sample.status,
    rejectionReason: sample.rejection_reason ?? undefined,
    collectedAt: sample.collected_at ?? undefined,
  };
}

function fromBackendBarcodeResolution(resolution: BackendBarcodeResolveResponse): BarcodeResolution {
  return {
    codeType: resolution.code_type,
    accession: fromBackendAccession(resolution.accession),
    sample: resolution.sample ? fromBackendSample(resolution.sample) : undefined,
    labOrders: resolution.lab_orders.map(fromBackendLabOrder),
  };
}

export interface ListLabOrdersParams {
  patient_id?: string;
  status?: string;
  accession_id?: string;
}

export async function listLabOrders(params: ListLabOrdersParams = {}): Promise<LabOrder[]> {
  const response = await apiClient.get<BackendLabOrderOut[]>("/lab/orders", { params });
  return (response.data ?? []).map(fromBackendLabOrder);
}

export async function createAccession(payload: {
  patient_id: string;
  lab_order_ids: string[];
}): Promise<Accession> {
  const response = await apiClient.post<BackendAccessionOut>("/lab/accessions", payload);
  if (!response.data) throw new Error("Failed to create accession");
  return fromBackendAccession(response.data);
}

export async function getAccession(id: string): Promise<Accession> {
  const response = await apiClient.get<BackendAccessionOut>(`/lab/accessions/${id}`);
  if (!response.data) throw new Error("Accession not found");
  return fromBackendAccession(response.data);
}

export async function collectSample(
  accessionId: string,
  payload: { specimen_type: string; container_type: string; lab_order_ids: string[] }
): Promise<Sample> {
  const response = await apiClient.post<BackendSampleOut>(`/lab/accessions/${accessionId}/samples`, payload);
  if (!response.data) throw new Error("Failed to create sample");
  return fromBackendSample(response.data);
}

export async function markSampleCollected(sampleId: string, remarks?: string): Promise<Sample> {
  const response = await apiClient.patch<BackendSampleOut>(`/lab/samples/${sampleId}/collect`, {
    remarks: remarks || null,
  });
  if (!response.data) throw new Error("Failed to mark sample collected");
  return fromBackendSample(response.data);
}

export async function rejectSample(sampleId: string, reason: string): Promise<Sample> {
  const response = await apiClient.patch<BackendSampleOut>(`/lab/samples/${sampleId}/reject`, { reason });
  if (!response.data) throw new Error("Failed to reject sample");
  return fromBackendSample(response.data);
}

export async function resolveBarcode(code: string): Promise<BarcodeResolution> {
  const response = await apiClient.get<BackendBarcodeResolveResponse>(
    `/lab/barcode/${encodeURIComponent(code)}`
  );
  if (!response.data) throw new Error("Barcode not found");
  return fromBackendBarcodeResolution(response.data);
}

export async function processSample(sampleId: string): Promise<Sample> {
  const response = await apiClient.patch<BackendSampleOut>(`/lab/samples/${sampleId}/process`, {});
  if (!response.data) throw new Error("Failed to process sample");
  return fromBackendSample(response.data);
}

export interface BackendSampleStatusHistoryOut {
  id: string;
  sample_id: string;
  status: string;
  remarks: string | null;
  changed_by: string | null;
  changed_at: string;
}

export interface SampleStatusHistoryEntry {
  id: string;
  sampleId: string;
  status: string;
  remarks?: string;
  changedBy?: string;
  changedAt: string;
}

export async function listSampleStatusHistory(sampleId: string): Promise<SampleStatusHistoryEntry[]> {
  const response = await apiClient.get<BackendSampleStatusHistoryOut[]>(
    `/lab/samples/${sampleId}/status-history`
  );
  return (response.data ?? []).map((row) => ({
    id: row.id,
    sampleId: row.sample_id,
    status: row.status,
    remarks: row.remarks ?? undefined,
    changedBy: row.changed_by ?? undefined,
    changedAt: row.changed_at,
  }));
}

// ---------------------------------------------------------------------------
// Result (P6-B05 result engine / P6-F05 result entry)
// ---------------------------------------------------------------------------

export interface BackendResultOut {
  id: string;
  lab_order_id: string;
  parameter_id: string;
  sample_id: string | null;
  entered_by: string | null;
  value: string;
  unit: string | null;
  flag: string;
  status: string;
  current_version: number;
  entered_at: string;
}

export interface BackendResultEntryFieldOut {
  parameter_id: string;
  parameter_code: string;
  name: string;
  unit: string | null;
  normal_min: number | null;
  normal_max: number | null;
  critical_low: number | null;
  critical_high: number | null;
  value: string | null;
  flag: string | null;
}

export interface BackendResultEntryFormOut {
  lab_order_id: string;
  order_number: string;
  order_status: string;
  test_name: string;
  fields: BackendResultEntryFieldOut[];
}

function fromBackendResult(result: BackendResultOut): Result {
  return {
    id: result.id,
    labOrderId: result.lab_order_id,
    parameterId: result.parameter_id,
    sampleId: result.sample_id ?? undefined,
    enteredBy: result.entered_by ?? undefined,
    value: result.value,
    unit: result.unit ?? undefined,
    flag: result.flag as ResultFlag,
    status: result.status,
    currentVersion: result.current_version,
    enteredAt: result.entered_at,
  };
}

function fromBackendResultEntryField(field: BackendResultEntryFieldOut): ResultEntryField {
  return {
    parameterId: field.parameter_id,
    parameterCode: field.parameter_code,
    name: field.name,
    unit: field.unit ?? undefined,
    normalMin: field.normal_min ?? undefined,
    normalMax: field.normal_max ?? undefined,
    criticalLow: field.critical_low ?? undefined,
    criticalHigh: field.critical_high ?? undefined,
    value: field.value ?? undefined,
    flag: (field.flag as ResultFlag | null) ?? undefined,
  };
}

export async function getResultEntryForm(labOrderId: string): Promise<ResultEntryForm> {
  const response = await apiClient.get<BackendResultEntryFormOut>(`/lab/orders/${labOrderId}/result-entry`);
  if (!response.data) throw new Error("Unable to load result entry form");
  const form = response.data;
  return {
    labOrderId: form.lab_order_id,
    orderNumber: form.order_number,
    orderStatus: form.order_status as LabOrderStatus,
    testName: form.test_name,
    fields: form.fields.map(fromBackendResultEntryField),
  };
}

export async function enterResults(
  labOrderId: string,
  items: { parameter_id: string; value: string; unit?: string | null }[]
): Promise<Result[]> {
  const response = await apiClient.post<BackendResultOut[]>(`/lab/orders/${labOrderId}/results`, { items });
  return (response.data ?? []).map(fromBackendResult);
}

export async function listResults(labOrderId: string): Promise<Result[]> {
  const response = await apiClient.get<BackendResultOut[]>(`/lab/orders/${labOrderId}/results`);
  return (response.data ?? []).map(fromBackendResult);
}

export interface BackendResultVersionOut {
  id: string;
  result_id: string;
  changed_by: string | null;
  version_number: number;
  value: string;
  flag: string;
  change_reason: string | null;
  recorded_at: string;
}

export async function listResultVersions(resultId: string): Promise<ResultVersionEntry[]> {
  const response = await apiClient.get<BackendResultVersionOut[]>(`/lab/results/${resultId}/versions`);
  return (response.data ?? []).map((v) => ({
    id: v.id,
    resultId: v.result_id,
    changedBy: v.changed_by ?? undefined,
    versionNumber: v.version_number,
    value: v.value,
    flag: v.flag as ResultFlag,
    changeReason: v.change_reason ?? undefined,
    recordedAt: v.recorded_at,
  }));
}

export async function amendResult(resultId: string, value: string, reason: string, unit?: string): Promise<Result> {
  const response = await apiClient.patch<BackendResultOut>(`/lab/results/${resultId}/amend`, {
    value,
    unit: unit || null,
    reason,
  });
  if (!response.data) throw new Error("Failed to amend result");
  return fromBackendResult(response.data);
}

// ---------------------------------------------------------------------------
// Verification / Approval (P6-F06)
// ---------------------------------------------------------------------------

export interface BackendVerificationOut {
  id: string;
  lab_order_id: string;
  verified_by: string | null;
  status: string;
  remarks: string | null;
  verified_at: string;
}

export interface BackendApprovalOut {
  id: string;
  lab_order_id: string;
  approved_by: string | null;
  status: string;
  remarks: string | null;
  report_checksum: string | null;
  report_qr_token: string | null;
  approved_at: string;
}

function fromBackendVerification(v: BackendVerificationOut): Verification {
  return {
    id: v.id,
    labOrderId: v.lab_order_id,
    verifiedBy: v.verified_by ?? undefined,
    status: v.status as Verification["status"],
    remarks: v.remarks ?? undefined,
    verifiedAt: v.verified_at,
  };
}

function fromBackendApproval(a: BackendApprovalOut): Approval {
  return {
    id: a.id,
    labOrderId: a.lab_order_id,
    approvedBy: a.approved_by ?? undefined,
    status: a.status as Approval["status"],
    remarks: a.remarks ?? undefined,
    reportChecksum: a.report_checksum ?? undefined,
    reportQrToken: a.report_qr_token ?? undefined,
    approvedAt: a.approved_at,
  };
}

export async function verifyResults(labOrderId: string, remarks?: string): Promise<Verification> {
  const response = await apiClient.post<BackendVerificationOut>(`/lab/orders/${labOrderId}/verify`, {
    remarks: remarks || null,
  });
  if (!response.data) throw new Error("Failed to verify results");
  return fromBackendVerification(response.data);
}

export async function rejectVerification(labOrderId: string, reason: string): Promise<Verification> {
  const response = await apiClient.post<BackendVerificationOut>(`/lab/orders/${labOrderId}/verify/reject`, {
    reason,
  });
  if (!response.data) throw new Error("Failed to reject verification");
  return fromBackendVerification(response.data);
}

export async function listVerifications(labOrderId: string): Promise<Verification[]> {
  const response = await apiClient.get<BackendVerificationOut[]>(`/lab/orders/${labOrderId}/verifications`);
  return (response.data ?? []).map(fromBackendVerification);
}

export async function approveResults(labOrderId: string, remarks?: string): Promise<Approval> {
  const response = await apiClient.post<BackendApprovalOut>(`/lab/orders/${labOrderId}/approve`, {
    remarks: remarks || null,
  });
  if (!response.data) throw new Error("Failed to approve results");
  return fromBackendApproval(response.data);
}

export async function rejectApproval(labOrderId: string, reason: string): Promise<Approval> {
  const response = await apiClient.post<BackendApprovalOut>(`/lab/orders/${labOrderId}/approve/reject`, {
    reason,
  });
  if (!response.data) throw new Error("Failed to reject approval");
  return fromBackendApproval(response.data);
}

export async function listApprovals(labOrderId: string): Promise<Approval[]> {
  const response = await apiClient.get<BackendApprovalOut[]>(`/lab/orders/${labOrderId}/approvals`);
  return (response.data ?? []).map(fromBackendApproval);
}

export async function finalizeOrder(labOrderId: string): Promise<LabOrder> {
  const response = await apiClient.post<BackendLabOrderOut>(`/lab/orders/${labOrderId}/finalize`, {});
  if (!response.data) throw new Error("Failed to finalize order");
  return fromBackendLabOrder(response.data);
}

// ---------------------------------------------------------------------------
// Report (P6-F07)
// ---------------------------------------------------------------------------

export interface BackendReportResultRowOut {
  parameter_id: string;
  parameter_code: string;
  parameter_name: string;
  value: string;
  unit: string | null;
  normal_min: number | null;
  normal_max: number | null;
  critical_low: number | null;
  critical_high: number | null;
  flag: string;
  version: number;
  is_amended: boolean;
}

export interface BackendLabReportOut {
  lab_order_id: string;
  order_number: string;
  accession_number: string | null;
  status: string;
  test_name: string;
  priority: string;
  ordered_at: string;
  collected_at: string | null;
  facility_name: string;
  facility_code: string;
  patient_name: string;
  patient_uid: string;
  patient_mrn: string;
  patient_gender: string;
  patient_age_years: number;
  referring_doctor_name: string | null;
  rows: BackendReportResultRowOut[];
  verified_by_name: string | null;
  verified_at: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  report_checksum: string | null;
  report_qr_token: string | null;
  generated_at: string;
}

export async function getLabReport(labOrderId: string): Promise<LabReport> {
  const response = await apiClient.get<BackendLabReportOut>(`/lab/orders/${labOrderId}/report`);
  if (!response.data) throw new Error("Unable to load this report");
  const r = response.data;
  return {
    labOrderId: r.lab_order_id,
    orderNumber: r.order_number,
    accessionNumber: r.accession_number ?? undefined,
    status: r.status as LabOrderStatus,
    testName: r.test_name,
    priority: r.priority,
    orderedAt: r.ordered_at,
    collectedAt: r.collected_at ?? undefined,
    facilityName: r.facility_name,
    facilityCode: r.facility_code,
    patientName: r.patient_name,
    patientUid: r.patient_uid,
    patientMrn: r.patient_mrn,
    patientGender: r.patient_gender,
    patientAgeYears: r.patient_age_years,
    referringDoctorName: r.referring_doctor_name ?? undefined,
    rows: r.rows.map((row) => ({
      parameterId: row.parameter_id,
      parameterCode: row.parameter_code,
      parameterName: row.parameter_name,
      value: row.value,
      unit: row.unit ?? undefined,
      normalMin: row.normal_min ?? undefined,
      normalMax: row.normal_max ?? undefined,
      criticalLow: row.critical_low ?? undefined,
      criticalHigh: row.critical_high ?? undefined,
      flag: row.flag as ResultFlag,
      version: row.version,
      isAmended: row.is_amended,
    })),
    verifiedByName: r.verified_by_name ?? undefined,
    verifiedAt: r.verified_at ?? undefined,
    approvedByName: r.approved_by_name ?? undefined,
    approvedAt: r.approved_at ?? undefined,
    reportChecksum: r.report_checksum ?? undefined,
    reportQrToken: r.report_qr_token ?? undefined,
    generatedAt: r.generated_at,
  };
}

export function getLabReportPdfUrl(labOrderId: string): string {
  return `${API_BASE_URL}/lab/orders/${labOrderId}/report.pdf`;
}
