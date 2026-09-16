import { describe, expect, it } from "vitest";
import { patientRegistrationFormSchema } from "@/types/patient";

const basePayload = {
  title: "Mr.",
  firstName: "Ramesh",
  middleName: "",
  lastName: "Sharma",
  gender: "MALE" as const,
  dob: "1990-01-01",
  ageYears: 36,
  ageMonths: 0,
  ageDays: 0,
  bloodGroup: "O_POSITIVE" as const,
  maritalStatus: "SINGLE",
  occupation: "",
  preferredLanguage: "English",
  mobile: "9876543210",
  secondaryPhone: "",
  email: "",
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
  identityType: "",
  identityNumber: "",
  photoUrl: "",
  abhaNumber: "",
  abhaAddress: "",
  abhaStatus: "UNVERIFIED" as const,
};

describe("patientRegistrationFormSchema", () => {
  it("accepts a fully valid adult payload", () => {
    const result = patientRegistrationFormSchema.safeParse(basePayload);
    expect(result.success).toBe(true);
  });

  it("requires guardianName and guardianRelationship for minors", () => {
    const minorPayload = { ...basePayload, ageYears: 10, dob: "2016-01-01" };
    const result = patientRegistrationFormSchema.safeParse(minorPayload);
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("guardianName");
      expect(paths).toContain("guardianRelationship");
    }
  });

  it("passes for a minor when guardian name and relationship are provided", () => {
    const minorPayload = {
      ...basePayload,
      ageYears: 10,
      dob: "2016-01-01",
      guardianName: "Vikram Sharma",
      guardianRelationship: "FATHER",
    };
    const result = patientRegistrationFormSchema.safeParse(minorPayload);
    expect(result.success).toBe(true);
  });

  it("rejects an invalid Aadhaar number (not 12 digits)", () => {
    const payload = { ...basePayload, identityType: "AADHAAR", identityNumber: "12345" };
    const result = patientRegistrationFormSchema.safeParse(payload);
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("identityNumber");
    }
  });

  it("accepts a valid 12-digit Aadhaar number", () => {
    const payload = { ...basePayload, identityType: "AADHAAR", identityNumber: "567812349012" };
    const result = patientRegistrationFormSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });

  it("rejects an invalid PAN format", () => {
    const payload = { ...basePayload, identityType: "PAN_CARD", identityNumber: "INVALIDPAN" };
    const result = patientRegistrationFormSchema.safeParse(payload);
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("identityNumber");
    }
  });

  it("accepts a valid PAN format", () => {
    const payload = { ...basePayload, identityType: "PAN_CARD", identityNumber: "ABCDE1234F" };
    const result = patientRegistrationFormSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });
});
