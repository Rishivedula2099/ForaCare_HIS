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
