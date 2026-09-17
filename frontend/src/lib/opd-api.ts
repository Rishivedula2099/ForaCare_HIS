/**
 * Thin typed wrapper over `apiClient` for the OPD Registration (P3-F02) and
 * Token Engine (P3-B02/P3-F03) backend endpoints, plus the camelCase
 * (frontend `types/opd.ts`) <-> snake_case (backend `EncounterOut`/
 * `EncounterCreateRequest`) mapping.
 */

import { apiClient } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import {
  Consultation,
  ConsultationFormState,
  ConsultationStatus,
  DrugRoute,
  OPDEncounter,
  OPDRegistrationFormState,
  Prescription,
  PrescriptionItemFormRow,
  QRStatus,
  QRVerifyReason,
  QRVerifyResult,
  TokenPriority,
  TokenStatus,
} from "@/types/opd";

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

interface BackendDepartmentSummary {
  id: string;
  name: string;
  code: string;
}

interface BackendDoctorSummary {
  id: string;
  doctor_code: string;
  full_name: string;
  specialization: string;
}

interface BackendTokenOut {
  id: string;
  token_number: number;
  token_date: string;
  status: string;
  priority: string;
  called_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface BackendEncounterOut {
  id: string;
  encounter_number: string;
  visit_type: string;
  status: string;
  notes: string | null;
  scheduled_at: string | null;
  created_at: string;
  patient: BackendPatientSummary;
  department: BackendDepartmentSummary;
  doctor: BackendDoctorSummary;
  token: BackendTokenOut | null;
  qr_code: string;
  qr_status: string;
  qr_expires_at: string;
}

export interface BackendQRVerifyResult {
  valid: boolean;
  reason: string;
  encounter: BackendEncounterOut | null;
}

export interface EncounterCreatePayload {
  patient_id: string;
  department_id: string;
  doctor_id: string;
  visit_type: string;
  priority: string;
  notes?: string | null;
}

export interface ListEncountersParams {
  patient_id?: string;
  doctor_id?: string;
  department_id?: string;
  visit_date?: string;
}

export function fromBackendEncounter(encounter: BackendEncounterOut): OPDEncounter {
  const patient = encounter.patient;
  return {
    id: encounter.id,
    encounterNumber: encounter.encounter_number,
    visitType: encounter.visit_type as OPDEncounter["visitType"],
    status: encounter.status,
    notes: encounter.notes ?? undefined,
    scheduledAt: encounter.scheduled_at ?? undefined,
    createdAt: encounter.created_at,
    patient: {
      id: patient.id,
      uid: patient.uid,
      mrn: patient.mrn,
      fullName: [patient.first_name, patient.middle_name, patient.last_name].filter(Boolean).join(" "),
      gender: patient.gender,
      dob: patient.dob,
    },
    department: encounter.department,
    doctor: {
      id: encounter.doctor.id,
      doctorCode: encounter.doctor.doctor_code,
      fullName: encounter.doctor.full_name,
      specialization: encounter.doctor.specialization,
    },
    token: encounter.token
      ? {
          id: encounter.token.id,
          tokenNumber: encounter.token.token_number,
          tokenDate: encounter.token.token_date,
          status: encounter.token.status as TokenStatus,
          priority: encounter.token.priority as TokenPriority,
          calledAt: encounter.token.called_at ?? undefined,
          startedAt: encounter.token.started_at ?? undefined,
          completedAt: encounter.token.completed_at ?? undefined,
        }
      : undefined,
    qrCode: encounter.qr_code,
    qrStatus: encounter.qr_status as QRStatus,
    qrExpiresAt: encounter.qr_expires_at,
  };
}

export function fromBackendQRVerifyResult(result: BackendQRVerifyResult): QRVerifyResult {
  return {
    valid: result.valid,
    reason: result.reason as QRVerifyReason,
    encounter: result.encounter ? fromBackendEncounter(result.encounter) : undefined,
  };
}

export function toCreatePayload(data: OPDRegistrationFormState): EncounterCreatePayload {
  return {
    patient_id: data.patientId,
    department_id: data.departmentId,
    doctor_id: data.doctorId,
    visit_type: data.visitType,
    priority: data.priority,
    notes: data.notes.trim() || null,
  };
}

export async function registerVisit(payload: EncounterCreatePayload): Promise<OPDEncounter> {
  const response = await apiClient.post<BackendEncounterOut>("/opd/encounters", payload);
  if (!response.data) {
    throw new Error("Failed to register OPD visit");
  }
  return fromBackendEncounter(response.data);
}

export async function listEncounters(params: ListEncountersParams = {}): Promise<OPDEncounter[]> {
  const response = await apiClient.get<BackendEncounterOut[]>("/opd/encounters", { params });
  return (response.data ?? []).map(fromBackendEncounter);
}

export async function getDoctorQueue(doctorId: string, queueDate?: string): Promise<OPDEncounter[]> {
  const response = await apiClient.get<BackendEncounterOut[]>(`/opd/doctors/${doctorId}/queue`, {
    params: queueDate ? { queue_date: queueDate } : undefined,
  });
  return (response.data ?? []).map(fromBackendEncounter);
}

export async function callNextToken(doctorId: string, queueDate?: string): Promise<OPDEncounter> {
  const response = await apiClient.post<BackendEncounterOut>(
    `/opd/doctors/${doctorId}/queue/call-next`,
    null,
    { params: queueDate ? { queue_date: queueDate } : undefined }
  );
  if (!response.data) {
    throw new Error("Failed to call the next token");
  }
  return fromBackendEncounter(response.data);
}

export async function updateTokenStatus(tokenId: string, status: TokenStatus): Promise<OPDEncounter> {
  const response = await apiClient.patch<BackendEncounterOut>(`/opd/tokens/${tokenId}/status`, {
    status,
  });
  if (!response.data) {
    throw new Error("Failed to update token status");
  }
  return fromBackendEncounter(response.data);
}

export async function verifyQrCode(qrCode: string): Promise<QRVerifyResult> {
  const response = await apiClient.post<BackendQRVerifyResult>("/opd/qr/verify", { qr_code: qrCode });
  if (!response.data) {
    throw new Error("Failed to verify QR code");
  }
  return fromBackendQRVerifyResult(response.data);
}

/**
 * P3-B03: the WebSocket push channel for a doctor's queue. Carries no
 * payload beyond a "something changed" signal - callers refetch
 * `getDoctorQueue` on message, keeping the REST endpoint as the single
 * source of truth for the queue's actual shape (see the backend route's
 * docstring in app/api/v1/opd.py for why).
 */
export function getDoctorQueueWebSocketUrl(doctorId: string): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/opd/doctors/${doctorId}/queue/ws`;
}

export async function revokeQr(encounterId: string): Promise<OPDEncounter> {
  const response = await apiClient.post<BackendEncounterOut>(`/opd/encounters/${encounterId}/qr/revoke`);
  if (!response.data) {
    throw new Error("Failed to revoke QR code");
  }
  return fromBackendEncounter(response.data);
}

export async function getEncounter(encounterId: string): Promise<OPDEncounter> {
  const response = await apiClient.get<BackendEncounterOut>(`/opd/encounters/${encounterId}`);
  if (!response.data) {
    throw new Error("Encounter not found");
  }
  return fromBackendEncounter(response.data);
}

// ---------------------------------------------------------------------------
// Consultation (P3-F05/P3-B04)
// ---------------------------------------------------------------------------

interface BackendConsultationOut {
  id: string;
  encounter_id: string;
  doctor_id: string;
  status: string;
  chief_complaint: string | null;
  history: string | null;
  examination: string | null;
  diagnosis: string | null;
  allergies: string | null;
  investigation: string | null;
  treatment: string | null;
  notes: string | null;
  temperature_celsius: number | null;
  pulse_bpm: number | null;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  spo2_percent: number | null;
  respiratory_rate: number | null;
  weight_kg: number | null;
  height_cm: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  encounter: BackendEncounterOut;
  doctor: BackendDoctorSummary;
}

export interface VitalsPayload {
  temperature_celsius?: number | null;
  pulse_bpm?: number | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  spo2_percent?: number | null;
  respiratory_rate?: number | null;
  weight_kg?: number | null;
  height_cm?: number | null;
}

export interface ConsultationCreatePayload {
  chief_complaint?: string | null;
  history?: string | null;
  examination?: string | null;
  diagnosis?: string | null;
  allergies?: string | null;
  investigation?: string | null;
  treatment?: string | null;
  notes?: string | null;
  vitals: VitalsPayload;
}

export type ConsultationUpdatePayload = Partial<ConsultationCreatePayload> & { status?: ConsultationStatus };

function fromBackendConsultation(consultation: BackendConsultationOut): Consultation {
  return {
    id: consultation.id,
    encounterId: consultation.encounter_id,
    doctorId: consultation.doctor_id,
    status: consultation.status as ConsultationStatus,
    chiefComplaint: consultation.chief_complaint ?? undefined,
    history: consultation.history ?? undefined,
    examination: consultation.examination ?? undefined,
    diagnosis: consultation.diagnosis ?? undefined,
    allergies: consultation.allergies ?? undefined,
    investigation: consultation.investigation ?? undefined,
    treatment: consultation.treatment ?? undefined,
    notes: consultation.notes ?? undefined,
    vitals: {
      temperatureCelsius: consultation.temperature_celsius ?? undefined,
      pulseBpm: consultation.pulse_bpm ?? undefined,
      bpSystolic: consultation.bp_systolic ?? undefined,
      bpDiastolic: consultation.bp_diastolic ?? undefined,
      spo2Percent: consultation.spo2_percent ?? undefined,
      respiratoryRate: consultation.respiratory_rate ?? undefined,
      weightKg: consultation.weight_kg ?? undefined,
      heightCm: consultation.height_cm ?? undefined,
    },
    startedAt: consultation.started_at ?? undefined,
    completedAt: consultation.completed_at ?? undefined,
    createdAt: consultation.created_at,
    updatedAt: consultation.updated_at,
    encounter: fromBackendEncounter(consultation.encounter),
    doctor: {
      id: consultation.doctor.id,
      doctorCode: consultation.doctor.doctor_code,
      fullName: consultation.doctor.full_name,
      specialization: consultation.doctor.specialization,
    },
  };
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number(trimmed);
}

export function toConsultationPayload(form: ConsultationFormState): ConsultationCreatePayload {
  return {
    chief_complaint: form.chiefComplaint.trim() || null,
    history: form.history.trim() || null,
    examination: form.examination.trim() || null,
    diagnosis: form.diagnosis.trim() || null,
    allergies: form.allergies.trim() || null,
    investigation: form.investigation.trim() || null,
    treatment: form.treatment.trim() || null,
    notes: form.notes.trim() || null,
    vitals: {
      temperature_celsius: numberOrNull(form.temperatureCelsius),
      pulse_bpm: numberOrNull(form.pulseBpm),
      bp_systolic: numberOrNull(form.bpSystolic),
      bp_diastolic: numberOrNull(form.bpDiastolic),
      spo2_percent: numberOrNull(form.spo2Percent),
      respiratory_rate: numberOrNull(form.respiratoryRate),
      weight_kg: numberOrNull(form.weightKg),
      height_cm: numberOrNull(form.heightCm),
    },
  };
}

export function formStateFromConsultation(consultation: Consultation): ConsultationFormState {
  const toStr = (n: number | undefined) => (n === undefined ? "" : String(n));
  return {
    chiefComplaint: consultation.chiefComplaint ?? "",
    history: consultation.history ?? "",
    examination: consultation.examination ?? "",
    diagnosis: consultation.diagnosis ?? "",
    allergies: consultation.allergies ?? "",
    investigation: consultation.investigation ?? "",
    treatment: consultation.treatment ?? "",
    notes: consultation.notes ?? "",
    temperatureCelsius: toStr(consultation.vitals.temperatureCelsius),
    pulseBpm: toStr(consultation.vitals.pulseBpm),
    bpSystolic: toStr(consultation.vitals.bpSystolic),
    bpDiastolic: toStr(consultation.vitals.bpDiastolic),
    spo2Percent: toStr(consultation.vitals.spo2Percent),
    respiratoryRate: toStr(consultation.vitals.respiratoryRate),
    weightKg: toStr(consultation.vitals.weightKg),
    heightCm: toStr(consultation.vitals.heightCm),
  };
}

export async function getConsultation(encounterId: string): Promise<Consultation | null> {
  try {
    const response = await apiClient.get<BackendConsultationOut>(`/opd/encounters/${encounterId}/consultation`);
    return response.data ? fromBackendConsultation(response.data) : null;
  } catch (error) {
    const apiError = error as { code?: string };
    if (apiError?.code === "NOT_FOUND") return null;
    throw error;
  }
}

export async function createConsultation(
  encounterId: string,
  payload: ConsultationCreatePayload
): Promise<Consultation> {
  const response = await apiClient.post<BackendConsultationOut>(
    `/opd/encounters/${encounterId}/consultation`,
    payload
  );
  if (!response.data) {
    throw new Error("Failed to create consultation");
  }
  return fromBackendConsultation(response.data);
}

export async function updateConsultation(
  encounterId: string,
  payload: ConsultationUpdatePayload
): Promise<Consultation> {
  const response = await apiClient.patch<BackendConsultationOut>(
    `/opd/encounters/${encounterId}/consultation`,
    payload
  );
  if (!response.data) {
    throw new Error("Failed to update consultation");
  }
  return fromBackendConsultation(response.data);
}

export async function listPatientConsultationHistory(patientId: string): Promise<Consultation[]> {
  const response = await apiClient.get<BackendConsultationOut[]>(`/opd/patients/${patientId}/consultations`);
  return (response.data ?? []).map(fromBackendConsultation);
}

// ---------------------------------------------------------------------------
// Prescription (P3-F06/P3-B05)
// ---------------------------------------------------------------------------

interface BackendPrescriptionItemOut {
  id: string;
  drug_name: string;
  dosage: string;
  route: string;
  frequency: string;
  duration: string;
  instructions: string | null;
}

interface BackendPrescriptionOut {
  id: string;
  consultation_id: string;
  doctor_id: string;
  items: BackendPrescriptionItemOut[];
  created_at: string;
  updated_at: string;
  doctor: BackendDoctorSummary;
}

interface BackendPrescriptionItemIn {
  drug_name: string;
  dosage: string;
  route: string;
  frequency: string;
  duration: string;
  instructions?: string | null;
}

export interface PrescriptionPayload {
  items: BackendPrescriptionItemIn[];
}

function fromBackendPrescription(prescription: BackendPrescriptionOut): Prescription {
  return {
    id: prescription.id,
    consultationId: prescription.consultation_id,
    doctorId: prescription.doctor_id,
    items: prescription.items.map((item) => ({
      id: item.id,
      drugName: item.drug_name,
      dosage: item.dosage,
      route: item.route as DrugRoute,
      frequency: item.frequency,
      duration: item.duration,
      instructions: item.instructions ?? undefined,
    })),
    createdAt: prescription.created_at,
    updatedAt: prescription.updated_at,
    doctor: {
      id: prescription.doctor.id,
      doctorCode: prescription.doctor.doctor_code,
      fullName: prescription.doctor.full_name,
      specialization: prescription.doctor.specialization,
    },
  };
}

export function toPrescriptionPayload(rows: PrescriptionItemFormRow[]): PrescriptionPayload {
  return {
    items: rows.map((row) => ({
      drug_name: row.drugName.trim(),
      dosage: row.dosage.trim(),
      route: row.route,
      frequency: row.frequency.trim(),
      duration: row.duration.trim(),
      instructions: row.instructions.trim() || null,
    })),
  };
}

export function rowsFromPrescription(prescription: Prescription): PrescriptionItemFormRow[] {
  return prescription.items.map((item) => ({
    key: item.id,
    drugName: item.drugName,
    dosage: item.dosage,
    route: item.route,
    frequency: item.frequency,
    duration: item.duration,
    instructions: item.instructions ?? "",
  }));
}

export async function getPrescription(encounterId: string): Promise<Prescription | null> {
  try {
    const response = await apiClient.get<BackendPrescriptionOut>(`/opd/encounters/${encounterId}/prescription`);
    return response.data ? fromBackendPrescription(response.data) : null;
  } catch (error) {
    const apiError = error as { code?: string };
    if (apiError?.code === "NOT_FOUND") return null;
    throw error;
  }
}

export async function createPrescription(
  encounterId: string,
  payload: PrescriptionPayload
): Promise<Prescription> {
  const response = await apiClient.post<BackendPrescriptionOut>(
    `/opd/encounters/${encounterId}/prescription`,
    payload
  );
  if (!response.data) {
    throw new Error("Failed to create prescription");
  }
  return fromBackendPrescription(response.data);
}

export async function updatePrescription(
  encounterId: string,
  payload: PrescriptionPayload
): Promise<Prescription> {
  const response = await apiClient.patch<BackendPrescriptionOut>(
    `/opd/encounters/${encounterId}/prescription`,
    payload
  );
  if (!response.data) {
    throw new Error("Failed to update prescription");
  }
  return fromBackendPrescription(response.data);
}
