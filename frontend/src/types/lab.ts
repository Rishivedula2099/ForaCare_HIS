// Mirrors backend/app/modules/lab/schemas.py (P6-F01: Lab Master).

export const SPECIMEN_TYPES = [
  { value: "EDTA_BLOOD", label: "EDTA Blood" },
  { value: "SERUM", label: "Serum" },
  { value: "PLASMA", label: "Plasma" },
  { value: "URINE", label: "Urine" },
  { value: "STOOL", label: "Stool" },
  { value: "SWAB", label: "Swab" },
  { value: "OTHER", label: "Other" },
] as const;
export type SpecimenType = (typeof SPECIMEN_TYPES)[number]["value"];

export const CONTAINER_TYPES = [
  { value: "LAVENDER_TOP", label: "Lavender Top" },
  { value: "RED_TOP", label: "Red Top" },
  { value: "GRAY_TOP", label: "Gray Top" },
  { value: "STERILE_CONTAINER", label: "Sterile Container" },
  { value: "OTHER", label: "Other" },
] as const;
export type ContainerType = (typeof CONTAINER_TYPES)[number]["value"];

export const REFERENCE_RANGE_GENDERS = [
  { value: "ALL", label: "All" },
  { value: "MALE", label: "Male" },
  { value: "FEMALE", label: "Female" },
] as const;
export type ReferenceRangeGender = (typeof REFERENCE_RANGE_GENDERS)[number]["value"];

export interface LabTest {
  id: string;
  departmentId?: string;
  testCode: string;
  name: string;
  specimenType: SpecimenType;
  containerType: ContainerType;
  tatMinutes: number;
  unitPrice: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface LabTestFormData {
  testCode: string;
  name: string;
  specimenType: SpecimenType;
  containerType: ContainerType;
  departmentId: string;
  tatMinutes: string;
  unitPrice: string;
}

export interface LabParameter {
  id: string;
  testId: string;
  parameterCode: string;
  name: string;
  unit?: string;
  sequenceOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface LabParameterFormData {
  parameterCode: string;
  name: string;
  unit: string;
  sequenceOrder: string;
}

export interface LabReferenceRange {
  id: string;
  parameterId: string;
  gender: ReferenceRangeGender;
  ageMinDays: number;
  ageMaxDays?: number;
  normalMin: number;
  normalMax: number;
  criticalLow?: number;
  criticalHigh?: number;
  createdAt: string;
  updatedAt: string;
}

export interface LabReferenceRangeFormData {
  gender: ReferenceRangeGender;
  ageMinDays: string;
  ageMaxDays: string;
  normalMin: string;
  normalMax: string;
  criticalLow: string;
  criticalHigh: string;
}

// ---------------------------------------------------------------------------
// LabOrder (P6-B02 state machine) / Accession / Sample (P6-B03 barcodes)
// ---------------------------------------------------------------------------

export const LAB_ORDER_STATUSES = [
  "ORDERED",
  "BILLED",
  "ACCESSIONED",
  "COLLECTION_PENDING",
  "COLLECTED",
  "PROCESSING",
  "RESULT_ENTERED",
  "TECHNICALLY_VERIFIED",
  "PENDING_APPROVAL",
  "APPROVED",
  "FINALIZED",
  "CANCELLED",
] as const;
export type LabOrderStatus = (typeof LAB_ORDER_STATUSES)[number];

export interface LabOrder {
  id: string;
  patientId: string;
  testId: string;
  accessionId?: string;
  sampleId?: string;
  orderNumber: string;
  status: LabOrderStatus;
  priority: string;
  clinicalNotes?: string;
  orderedAt: string;
}

export interface Accession {
  id: string;
  patientId: string;
  accessionedBy?: string;
  accessionNumber: string;
  status: string;
  accessionedAt: string;
}

export interface Sample {
  id: string;
  accessionId: string;
  collectedBy?: string;
  barcodeId: string;
  specimenType: SpecimenType;
  containerType: ContainerType;
  status: string;
  rejectionReason?: string;
  collectedAt?: string;
}

export interface BarcodeResolution {
  codeType: "ACCESSION" | "SAMPLE";
  accession: Accession;
  sample?: Sample;
  labOrders: LabOrder[];
}

// ---------------------------------------------------------------------------
// Result (P6-B05 result engine / P6-F05 result entry)
// ---------------------------------------------------------------------------

export type ResultFlag = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";

export interface Result {
  id: string;
  labOrderId: string;
  parameterId: string;
  sampleId?: string;
  enteredBy?: string;
  value: string;
  unit?: string;
  flag: ResultFlag;
  status: string;
  currentVersion: number;
  enteredAt: string;
}

export interface ResultEntryField {
  parameterId: string;
  parameterCode: string;
  name: string;
  unit?: string;
  normalMin?: number;
  normalMax?: number;
  criticalLow?: number;
  criticalHigh?: number;
  value?: string;
  flag?: ResultFlag;
}

export interface ResultEntryForm {
  labOrderId: string;
  orderNumber: string;
  orderStatus: LabOrderStatus;
  testName: string;
  fields: ResultEntryField[];
}

export interface ResultVersionEntry {
  id: string;
  resultId: string;
  changedBy?: string;
  versionNumber: number;
  value: string;
  flag: ResultFlag;
  changeReason?: string;
  recordedAt: string;
}

// ---------------------------------------------------------------------------
// Verification / Approval (P6-F06)
// ---------------------------------------------------------------------------

export interface Verification {
  id: string;
  labOrderId: string;
  verifiedBy?: string;
  status: "VERIFIED" | "REJECTED";
  remarks?: string;
  verifiedAt: string;
}

export interface Approval {
  id: string;
  labOrderId: string;
  approvedBy?: string;
  status: "APPROVED" | "REJECTED";
  remarks?: string;
  reportChecksum?: string;
  reportQrToken?: string;
  approvedAt: string;
}

// ---------------------------------------------------------------------------
// Report (P6-F07 lab report UI)
// ---------------------------------------------------------------------------

export interface ReportResultRow {
  parameterId: string;
  parameterCode: string;
  parameterName: string;
  value: string;
  unit?: string;
  normalMin?: number;
  normalMax?: number;
  criticalLow?: number;
  criticalHigh?: number;
  flag: ResultFlag;
  version: number;
  isAmended: boolean;
}

export interface LabReport {
  labOrderId: string;
  orderNumber: string;
  accessionNumber?: string;
  status: LabOrderStatus;
  testName: string;
  priority: string;
  orderedAt: string;
  collectedAt?: string;

  facilityName: string;
  facilityCode: string;

  patientName: string;
  patientUid: string;
  patientMrn: string;
  patientGender: string;
  patientAgeYears: number;

  referringDoctorName?: string;

  rows: ReportResultRow[];

  verifiedByName?: string;
  verifiedAt?: string;
  approvedByName?: string;
  approvedAt?: string;

  reportChecksum?: string;
  reportQrToken?: string;
  generatedAt: string;
}
