import { describe, expect, it } from "vitest";
import {
  BackendPatientOut,
  fromBackendPatient,
  toCreatePayload,
  toDuplicateCheckPayload,
  toPatient,
} from "@/lib/patient-api";
import { PatientRegistrationFormData } from "@/types/patient";

const backendPatientFixture: BackendPatientOut = {
  id: "11111111-1111-1111-1111-111111111111",
  uid: "FC01-202609-000123",
  mrn: "MRN-2026-000123",
  title: "Mrs.",
  first_name: "Sunita",
  middle_name: null,
  last_name: "Verma",
  gender: "FEMALE",
  dob: "1982-04-15",
  blood_group: "B_POSITIVE",
  marital_status: "MARRIED",
  occupation: "Teacher",
  preferred_language: "Hindi",
  is_minor: false,
  guardian_name: "Ramesh Verma",
  guardian_relationship: "SPOUSE",
  guardian_phone: "9876543211",
  guardian_address: "Flat 402, MG Road",
  status: "ACTIVE",
  created_at: "2026-09-01T09:30:00Z",
  address: {
    address_type: "PERMANENT",
    street: "Flat 402, Green Valley Apartments",
    city: "Bengaluru",
    state: "Karnataka",
    pincode: "560001",
    country: "India",
  },
  contacts: [
    { contact_type: "MOBILE", value: "9876543210", is_primary: true },
    { contact_type: "EMAIL", value: "sunita.verma@example.com", is_primary: false },
  ],
  photos: [{ id: "photo-1", storage_path: "/storage/photo-1.jpg", is_primary: true, captured_at: "2026-09-01T09:30:00Z" }],
  identifiers: [{ identity_type: "AADHAAR", id_number: "567812349012", is_verified: true }],
  identity_links: [
    {
      system: "ABHA",
      external_id: "91-4521-8890-1204",
      external_address: "sunita.verma@abdm",
      status: "VERIFIED",
      linked_at: "2026-09-01T09:30:00Z",
    },
  ],
};

describe("fromBackendPatient", () => {
  it("extracts mobile and email from contacts", () => {
    const vm = fromBackendPatient(backendPatientFixture);
    expect(vm.mobile).toBe("9876543210");
    expect(vm.email).toBe("sunita.verma@example.com");
    expect(vm.secondaryPhone).toBeUndefined();
  });

  it("extracts ABHA number/address/status from identity_links", () => {
    const vm = fromBackendPatient(backendPatientFixture);
    expect(vm.abha.abhaNumber).toBe("91-4521-8890-1204");
    expect(vm.abha.abhaAddress).toBe("sunita.verma@abdm");
    expect(vm.abha.status).toBe("VERIFIED");
  });

  it("builds the display name from title/first/middle/last", () => {
    const vm = fromBackendPatient(backendPatientFixture);
    expect(vm.displayName).toBe("Mrs. Sunita Verma");
  });

  it("maps the primary photo id", () => {
    const vm = fromBackendPatient(backendPatientFixture);
    expect(vm.primaryPhotoId).toBe("photo-1");
  });

  it("maps guardian details when guardian_name is present", () => {
    const vm = fromBackendPatient(backendPatientFixture);
    expect(vm.guardian).toEqual({
      name: "Ramesh Verma",
      relationship: "SPOUSE",
      phone: "9876543211",
      address: "Flat 402, MG Road",
    });
  });

  it("omits guardian when guardian_name is null", () => {
    const vm = fromBackendPatient({ ...backendPatientFixture, guardian_name: null });
    expect(vm.guardian).toBeUndefined();
  });
});

describe("toPatient", () => {
  it("maps a full backend patient into the camelCase Patient shape", () => {
    const patient = toPatient(backendPatientFixture);
    expect(patient.uid).toBe("FC01-202609-000123");
    expect(patient.mrn).toBe("MRN-2026-000123");
    expect(patient.fullName).toBe("Mrs. Sunita Verma");
    expect(patient.mobile).toBe("9876543210");
    expect(patient.email).toBe("sunita.verma@example.com");
    expect(patient.address.city).toBe("Bengaluru");
    expect(patient.primaryIdentity).toEqual({
      type: "AADHAAR",
      idNumber: "567812349012",
      isVerified: true,
    });
    expect(patient.abha.abhaNumber).toBe("91-4521-8890-1204");
    expect(patient.status).toBe("ACTIVE");
  });
});

describe("toCreatePayload", () => {
  it("maps camelCase registration form data into the backend snake_case shape", () => {
    const formData: PatientRegistrationFormData = {
      title: "Mr.",
      firstName: "Ramesh",
      middleName: "",
      lastName: "Sharma",
      gender: "MALE",
      dob: "1990-01-01",
      ageYears: 36,
      ageMonths: 0,
      ageDays: 0,
      bloodGroup: "O_POSITIVE",
      maritalStatus: "SINGLE",
      occupation: "",
      preferredLanguage: "English",
      mobile: "9876543210",
      secondaryPhone: "",
      email: "ramesh@example.com",
      street: "123 MG Road",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560001",
      country: "India",
      guardianName: "",
      guardianRelationship: "",
      guardianPhone: "",
      guardianAddressSameAsPatient: true,
      guardianAddress: "",
      identityType: "AADHAAR",
      identityNumber: "567812349012",
      photoUrl: "",
      abhaNumber: "",
      abhaAddress: "",
      abhaStatus: "UNVERIFIED",
    };

    const payload = toCreatePayload(formData);
    expect(payload.first_name).toBe("Ramesh");
    expect(payload.last_name).toBe("Sharma");
    expect(payload.address.city).toBe("Bengaluru");
    expect(payload.contacts).toEqual([
      { contact_type: "MOBILE", value: "9876543210", is_primary: true },
      { contact_type: "EMAIL", value: "ramesh@example.com", is_primary: false },
    ]);
    expect(payload.identifiers).toEqual([{ identity_type: "AADHAAR", id_number: "567812349012" }]);
  });
});

describe("toDuplicateCheckPayload", () => {
  it("maps camelCase fields to the DuplicateCheckRequest snake_case shape", () => {
    const payload = toDuplicateCheckPayload({
      mobile: "9876543210",
      identityNumber: "567812349012",
      firstName: "Ramesh",
      lastName: "Sharma",
      dob: "1990-01-01",
    });
    expect(payload).toEqual({
      mobile: "9876543210",
      id_number: "567812349012",
      first_name: "Ramesh",
      last_name: "Sharma",
      dob: "1990-01-01",
    });
  });
});
