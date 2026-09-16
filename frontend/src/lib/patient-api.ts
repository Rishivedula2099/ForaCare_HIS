/**
 * Thin typed wrapper over `apiClient` for the Patient Master (P2-F01/F02)
 * backend endpoints, plus the camelCase (frontend `types/patient.ts`)
 * <-> snake_case (backend `PatientOut`/`PatientCreateRequest`) mapping
 * helpers. This is the single source of truth for that mapping - other
 * modules (e.g. `app/patients/[id]/page.tsx`) should import from here
 * instead of redefining their own copies.
 */

import { apiClient } from "@/lib/api-client";
import { calculateAgeFromDob } from "@/lib/patient-store";
import {
  ABHAVerificationStatus,
  BloodGroup,
  Gender,
  IdentityType,
  Patient,
  PatientRegistrationFormData,
} from "@/types/patient";

// ---------------------------------------------------------------------------
// Backend shapes (snake_case) - mirrors backend/app/modules/patients/schemas.py
// ---------------------------------------------------------------------------

export interface BackendPatientAddress {
  address_type?: string;
  street: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
}

export interface BackendPatientContact {
  contact_type: string;
  value: string;
  is_primary: boolean;
}

export interface BackendPatientPhoto {
  id: string;
  storage_path: string;
  content_type?: string | null;
  is_primary: boolean;
  captured_at: string;
}

export interface BackendPatientIdentifier {
  identity_type: string;
  id_number: string;
  is_verified: boolean;
  verified_at?: string | null;
}

export interface BackendPatientIdentityLink {
  system: string;
  external_id: string | null;
  external_address: string | null;
  status: string;
  linked_at: string | null;
}

export interface BackendPatientListItem {
  id: string;
  uid: string;
  mrn: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  gender: string;
  dob: string;
  status: string;
}

// Backend `PatientOut` shape (snake_case, nested arrays) - see
// backend/app/modules/patients/schemas.py.
export interface BackendPatientOut {
  id: string;
  uid: string;
  mrn: string;
  title: string | null;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  gender: string;
  dob: string;
  blood_group: string;
  marital_status: string | null;
  occupation: string | null;
  preferred_language: string | null;
  is_minor: boolean;
  guardian_name: string | null;
  guardian_relationship: string | null;
  guardian_phone: string | null;
  guardian_address: string | null;
  status: string;
  created_at: string;
  address: BackendPatientAddress | null;
  contacts: BackendPatientContact[];
  photos: BackendPatientPhoto[];
  identifiers: BackendPatientIdentifier[];
  identity_links: BackendPatientIdentityLink[];
}

export interface PatientCreatePayload {
  title?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  gender: string;
  dob: string;
  blood_group: string;
  marital_status?: string | null;
  occupation?: string | null;
  preferred_language?: string | null;
  guardian_name?: string | null;
  guardian_relationship?: string | null;
  guardian_phone?: string | null;
  guardian_address?: string | null;
  address: {
    address_type?: string;
    street: string;
    city: string;
    state: string;
    pincode: string;
    country?: string;
  };
  contacts: { contact_type: string; value: string; is_primary: boolean }[];
  identifiers: { identity_type: string; id_number: string }[];
}

export type PatientUpdatePayload = Partial<PatientCreatePayload> & { status?: string };

export interface DuplicateCheckPayload {
  mobile?: string;
  id_number?: string;
  first_name?: string;
  last_name?: string;
  dob?: string;
}

export interface ListPatientsParams {
  uid?: string;
  mrn?: string;
  name?: string;
  mobile?: string;
}

// ---------------------------------------------------------------------------
// Frontend view-model used by the Patient 360 page
// ---------------------------------------------------------------------------

export interface PatientViewModel {
  id: string;
  uid: string;
  mrn: string;
  displayName: string;
  gender: string;
  dob: string;
  ageYears: number;
  bloodGroup: string;
  maritalStatus?: string;
  occupation?: string;
  preferredLanguage?: string;
  isMinor: boolean;
  status: string;
  photoUrl?: string;
  primaryPhotoId?: string;
  mobile?: string;
  secondaryPhone?: string;
  email?: string;
  address?: { street: string; city: string; state: string; pincode: string; country: string };
  guardian?: { name?: string; relationship?: string; phone?: string; address?: string };
  identifiers: { type: string; idNumber: string; isVerified: boolean }[];
  abha: { abhaNumber?: string; abhaAddress?: string; status: string; verifiedAt?: string };
  registeredAt?: string;
  registeredBy?: string;
  facilityName?: string;
}

export function fromBackendPatient(patient: BackendPatientOut): PatientViewModel {
  const mobile = patient.contacts.find((c) => c.contact_type === "MOBILE")?.value;
  const secondaryPhone = patient.contacts.find((c) => c.contact_type === "SECONDARY_PHONE")?.value;
  const email = patient.contacts.find((c) => c.contact_type === "EMAIL")?.value;
  const abhaLink = patient.identity_links.find((link) => link.system === "ABHA");
  const primaryPhoto = patient.photos.find((p) => p.is_primary) ?? patient.photos[0];

  return {
    id: patient.id,
    uid: patient.uid,
    mrn: patient.mrn,
    displayName: [patient.title, patient.first_name, patient.middle_name, patient.last_name]
      .filter(Boolean)
      .join(" "),
    gender: patient.gender,
    dob: patient.dob,
    ageYears: calculateAgeFromDob(patient.dob).years,
    bloodGroup: patient.blood_group,
    maritalStatus: patient.marital_status ?? undefined,
    occupation: patient.occupation ?? undefined,
    preferredLanguage: patient.preferred_language ?? undefined,
    isMinor: patient.is_minor,
    status: patient.status,
    photoUrl: undefined,
    primaryPhotoId: primaryPhoto?.id,
    mobile,
    secondaryPhone,
    email,
    address: patient.address ?? undefined,
    guardian: patient.guardian_name
      ? {
          name: patient.guardian_name,
          relationship: patient.guardian_relationship ?? undefined,
          phone: patient.guardian_phone ?? undefined,
          address: patient.guardian_address ?? undefined,
        }
      : undefined,
    identifiers: patient.identifiers.map((identifier) => ({
      type: identifier.identity_type,
      idNumber: identifier.id_number,
      isVerified: identifier.is_verified,
    })),
    abha: {
      abhaNumber: abhaLink?.external_id ?? undefined,
      abhaAddress: abhaLink?.external_address ?? undefined,
      status: abhaLink?.status ?? "UNVERIFIED",
      verifiedAt: abhaLink?.linked_at ?? undefined,
    },
    registeredAt: patient.created_at,
  };
}

/**
 * Maps a full backend `PatientOut` into the camelCase `Patient` shape used
 * by legacy UI (the registration success dialog, the directory table/grid,
 * duplicate-alert). Fields the backend doesn't return (tenant/facility
 * display name, registeredBy display name) are filled with safe defaults
 * since none of those views render them as required content.
 */
export function toPatient(patient: BackendPatientOut): Patient {
  const vm = fromBackendPatient(patient);
  const age = calculateAgeFromDob(patient.dob);

  return {
    id: patient.id,
    uid: patient.uid,
    mrn: patient.mrn,
    title: patient.title || "",
    firstName: patient.first_name,
    middleName: patient.middle_name || undefined,
    lastName: patient.last_name,
    fullName: vm.displayName,
    gender: patient.gender as Gender,
    dob: patient.dob,
    ageYears: age.years,
    ageMonths: age.months,
    ageDays: age.days,
    isMinor: patient.is_minor,
    bloodGroup: patient.blood_group as BloodGroup,
    maritalStatus: patient.marital_status ?? undefined,
    occupation: patient.occupation ?? undefined,
    preferredLanguage: patient.preferred_language ?? undefined,
    mobile: vm.mobile || "",
    secondaryPhone: vm.secondaryPhone,
    email: vm.email,
    address: patient.address
      ? {
          street: patient.address.street,
          city: patient.address.city,
          state: patient.address.state,
          pincode: patient.address.pincode,
          country: patient.address.country,
        }
      : { street: "", city: "", state: "", pincode: "", country: "India" },
    guardian: vm.guardian,
    primaryIdentity: patient.identifiers[0]
      ? {
          type: patient.identifiers[0].identity_type as IdentityType,
          idNumber: patient.identifiers[0].id_number,
          isVerified: patient.identifiers[0].is_verified,
        }
      : undefined,
    photoUrl: "",
    abha: {
      abhaNumber: vm.abha.abhaNumber,
      abhaAddress: vm.abha.abhaAddress,
      status: (vm.abha.status as ABHAVerificationStatus) || "UNVERIFIED",
      verifiedAt: vm.abha.verifiedAt,
    },
    tenantId: patient.id ? "" : "",
    facilityId: "",
    facilityName: "",
    registeredAt: patient.created_at,
    updatedAt: patient.created_at,
    registeredBy: "",
    status: (patient.status as Patient["status"]) || "ACTIVE",
  };
}

export function fromBackendListItem(item: BackendPatientListItem): Patient {
  const fullName = [item.first_name, item.middle_name, item.last_name].filter(Boolean).join(" ");
  const age = calculateAgeFromDob(item.dob);
  return {
    id: item.id,
    uid: item.uid,
    mrn: item.mrn,
    title: "",
    firstName: item.first_name,
    middleName: item.middle_name || undefined,
    lastName: item.last_name,
    fullName,
    gender: item.gender as Gender,
    dob: item.dob,
    ageYears: age.years,
    ageMonths: age.months,
    ageDays: age.days,
    isMinor: age.years < 18,
    bloodGroup: "UNKNOWN" as BloodGroup,
    mobile: "",
    address: { street: "", city: "", state: "", pincode: "", country: "India" },
    photoUrl: "",
    abha: { status: "UNVERIFIED" },
    tenantId: "",
    facilityId: "",
    facilityName: "",
    registeredAt: "",
    updatedAt: "",
    registeredBy: "",
    status: (item.status as Patient["status"]) || "ACTIVE",
  };
}

/**
 * Maps the registration form's camelCase data into the backend
 * `PatientCreateRequest` snake_case payload.
 */
export function toCreatePayload(data: PatientRegistrationFormData): PatientCreatePayload {
  const contacts: PatientCreatePayload["contacts"] = [];
  if (data.mobile) {
    contacts.push({ contact_type: "MOBILE", value: data.mobile.trim(), is_primary: true });
  }
  if (data.secondaryPhone) {
    contacts.push({ contact_type: "SECONDARY_PHONE", value: data.secondaryPhone.trim(), is_primary: false });
  }
  if (data.email) {
    contacts.push({ contact_type: "EMAIL", value: data.email.trim(), is_primary: false });
  }

  const identifiers: PatientCreatePayload["identifiers"] = [];
  if (data.identityType && data.identityNumber) {
    identifiers.push({ identity_type: data.identityType, id_number: data.identityNumber.trim() });
  }

  return {
    title: data.title || null,
    first_name: data.firstName.trim(),
    middle_name: data.middleName?.trim() || null,
    last_name: data.lastName.trim(),
    gender: data.gender,
    dob: data.dob,
    blood_group: data.bloodGroup,
    marital_status: data.maritalStatus || null,
    occupation: data.occupation?.trim() || null,
    preferred_language: data.preferredLanguage || null,
    guardian_name: data.guardianName?.trim() || null,
    guardian_relationship: data.guardianRelationship || null,
    guardian_phone: data.guardianPhone?.trim() || null,
    guardian_address: data.guardianAddressSameAsPatient
      ? `${data.street}, ${data.city}, ${data.state} - ${data.pincode}`
      : data.guardianAddress?.trim() || null,
    address: {
      address_type: "PERMANENT",
      street: data.street.trim(),
      city: data.city.trim(),
      state: data.state,
      pincode: data.pincode.trim(),
      country: data.country || "India",
    },
    contacts,
    identifiers,
  };
}

export function toDuplicateCheckPayload(data: {
  mobile?: string;
  identityNumber?: string;
  firstName?: string;
  lastName?: string;
  dob?: string;
}): DuplicateCheckPayload {
  return {
    mobile: data.mobile || undefined,
    id_number: data.identityNumber || undefined,
    first_name: data.firstName || undefined,
    last_name: data.lastName || undefined,
    dob: data.dob || undefined,
  };
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export async function listPatients(params: ListPatientsParams = {}): Promise<BackendPatientListItem[]> {
  const response = await apiClient.get<BackendPatientListItem[]>("/patients", { params });
  return response.data ?? [];
}

export async function checkDuplicates(payload: DuplicateCheckPayload): Promise<BackendPatientOut[]> {
  const response = await apiClient.post<BackendPatientOut[]>("/patients/check-duplicates", payload);
  return response.data ?? [];
}

export async function getPatient(id: string): Promise<BackendPatientOut> {
  const response = await apiClient.get<BackendPatientOut>(`/patients/${id}`);
  if (!response.data) {
    throw new Error("Patient not found");
  }
  return response.data;
}

export async function createPatient(payload: PatientCreatePayload): Promise<BackendPatientOut> {
  const response = await apiClient.post<BackendPatientOut>("/patients", payload);
  if (!response.data) {
    throw new Error("Failed to create patient");
  }
  return response.data;
}

export async function updatePatient(id: string, payload: PatientUpdatePayload): Promise<BackendPatientOut> {
  const response = await apiClient.patch<BackendPatientOut>(`/patients/${id}`, payload);
  if (!response.data) {
    throw new Error("Failed to update patient");
  }
  return response.data;
}

export interface UploadedPhoto {
  id: string;
  content_type: string;
  is_primary: boolean;
  captured_at: string;
}

export async function uploadPatientPhoto(id: string, file: Blob | File): Promise<UploadedPhoto> {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : "photo.jpg");
  const response = await apiClient.post<UploadedPhoto>(`/patients/${id}/photo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  if (!response.data) {
    throw new Error("Failed to upload photo");
  }
  return response.data;
}

/**
 * Fetches a patient photo as a blob and returns an object URL. The photo
 * endpoint returns raw image bytes (not the JSON envelope) and requires
 * cookie auth, so a plain `<img src>` cannot be used reliably cross-origin -
 * this goes through the authenticated axios instance instead.
 */
export async function getPatientPhotoBlobUrl(id: string, photoId: string): Promise<string> {
  const axiosInstance = apiClient.getAxiosInstance();
  const response = await axiosInstance.get(`/patients/${id}/photo/${photoId}`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data as Blob);
}
