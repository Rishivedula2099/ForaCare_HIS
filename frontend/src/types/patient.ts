import { z } from "zod";

export const GENDERS = [
  { value: "MALE", label: "Male" },
  { value: "FEMALE", label: "Female" },
  { value: "OTHER", label: "Other" },
  { value: "TRANSGENDER", label: "Transgender" },
] as const;

export type Gender = (typeof GENDERS)[number]["value"];

export const BLOOD_GROUPS = [
  { value: "A_POSITIVE", label: "A+" },
  { value: "A_NEGATIVE", label: "A-" },
  { value: "B_POSITIVE", label: "B+" },
  { value: "B_NEGATIVE", label: "B-" },
  { value: "AB_POSITIVE", label: "AB+" },
  { value: "AB_NEGATIVE", label: "AB-" },
  { value: "O_POSITIVE", label: "O+" },
  { value: "O_NEGATIVE", label: "O-" },
  { value: "UNKNOWN", label: "Unknown / Not Tested" },
] as const;

export type BloodGroup = (typeof BLOOD_GROUPS)[number]["value"];

export const TITLES = [
  { value: "Mr.", label: "Mr." },
  { value: "Mrs.", label: "Mrs." },
  { value: "Ms.", label: "Ms." },
  { value: "Master", label: "Master (Child)" },
  { value: "Baby", label: "Baby of" },
  { value: "Dr.", label: "Dr." },
  { value: "Prof.", label: "Prof." },
  { value: "Shri", label: "Shri" },
  { value: "Smt.", label: "Smt." },
] as const;

export const MARITAL_STATUSES = [
  { value: "SINGLE", label: "Single" },
  { value: "MARRIED", label: "Married" },
  { value: "DIVORCED", label: "Divorced" },
  { value: "WIDOWED", label: "Widowed" },
  { value: "OTHER", label: "Other / Unspecified" },
] as const;

export const GUARDIAN_RELATIONSHIPS = [
  { value: "FATHER", label: "Father" },
  { value: "MOTHER", label: "Mother" },
  { value: "SPOUSE", label: "Spouse" },
  { value: "SON", label: "Son" },
  { value: "DAUGHTER", label: "Daughter" },
  { value: "BROTHER", label: "Brother" },
  { value: "SISTER", label: "Sister" },
  { value: "LEGAL_GUARDIAN", label: "Legal Guardian" },
  { value: "FRIEND", label: "Friend / Relative" },
  { value: "OTHER", label: "Other" },
] as const;

export const IDENTITY_TYPES = [
  { value: "AADHAAR", label: "Aadhaar Card (UIDAI)" },
  { value: "VOTER_ID", label: "Voter Identity Card (EPIC)" },
  { value: "PASSPORT", label: "Passport" },
  { value: "DRIVING_LICENSE", label: "Driving License" },
  { value: "PAN_CARD", label: "PAN Card" },
  { value: "RATION_CARD", label: "Ration Card / Food Security" },
  { value: "AYUSHMAN_CARD", label: "Ayushman Bharat / PMJAY Card" },
  { value: "OTHER", label: "Other Government ID" },
] as const;

export type IdentityType = (typeof IDENTITY_TYPES)[number]["value"];

export const INDIAN_STATES_AND_UTS = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Andaman and Nicobar Islands",
  "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi (NCT)",
  "Jammu and Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
] as const;

export const ABHA_STATUSES = {
  UNVERIFIED: "UNVERIFIED",
  VERIFIED: "VERIFIED",
  PENDING: "PENDING",
  LINKED: "LINKED",
} as const;

export type ABHAVerificationStatus =
  (typeof ABHA_STATUSES)[keyof typeof ABHA_STATUSES];

export interface IdentityReference {
  type: IdentityType;
  idNumber: string;
  isVerified?: boolean;
}

export interface GuardianDetails {
  name?: string;
  relationship?: string;
  phone?: string;
  address?: string;
}

export interface AddressDetails {
  street: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
}

export interface ABHADetails {
  abhaNumber?: string;
  abhaAddress?: string;
  status: ABHAVerificationStatus;
  verifiedAt?: string;
}

export interface Patient {
  id: string;
  uid: string; // e.g. FC01-202609-000102
  mrn: string; // e.g. MRN-2026-000102
  title: string;
  firstName: string;
  middleName?: string;
  lastName: string;
  fullName: string;
  gender: Gender;
  dob: string; // YYYY-MM-DD
  ageYears: number;
  ageMonths?: number;
  ageDays?: number;
  isMinor: boolean;
  bloodGroup: BloodGroup;
  maritalStatus?: string;
  occupation?: string;
  preferredLanguage?: string;
  
  mobile: string;
  secondaryPhone?: string;
  email?: string;
  
  address: AddressDetails;
  guardian?: GuardianDetails;
  primaryIdentity?: IdentityReference;
  photoUrl?: string;
  abha: ABHADetails;
  
  tenantId: string;
  facilityId: string;
  facilityName: string;
  registeredAt: string;
  updatedAt: string;
  registeredBy: string;
  status: "ACTIVE" | "INACTIVE" | "DECEASED";
}

// Base Zod schema for patient registration form validation
export const patientRegistrationBaseSchema = z.object({
  title: z.string().min(1, "Title is required"),
  firstName: z
    .string()
    .trim()
    .min(2, "First name must be at least 2 characters")
    .max(50, "First name cannot exceed 50 characters"),
  middleName: z.string().trim().max(50).optional(),
  lastName: z
    .string()
    .trim()
    .min(1, "Last name is required")
    .max(50, "Last name cannot exceed 50 characters"),
  gender: z.enum(["MALE", "FEMALE", "OTHER", "TRANSGENDER"], {
    message: "Please select a gender",
  }),
  dob: z
    .string()
    .min(1, "Date of birth is required")
    .refine(
      (val) => {
        const date = new Date(val);
        return !isNaN(date.getTime()) && date <= new Date();
      },
      { message: "Date of birth cannot be in the future" }
    ),
  ageYears: z
    .number()
    .min(0, "Age cannot be negative")
    .max(130, "Age must be realistic (max 130)"),
  ageMonths: z.number().min(0).max(11).optional(),
  ageDays: z.number().min(0).max(30).optional(),
  bloodGroup: z.enum(
    [
      "A_POSITIVE",
      "A_NEGATIVE",
      "B_POSITIVE",
      "B_NEGATIVE",
      "AB_POSITIVE",
      "AB_NEGATIVE",
      "O_POSITIVE",
      "O_NEGATIVE",
      "UNKNOWN",
    ],
    { message: "Please select a blood group" }
  ),
  maritalStatus: z.string().optional(),
  occupation: z.string().trim().max(100).optional(),
  preferredLanguage: z.string().optional(),

  mobile: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, "Please enter a valid 10-digit Indian mobile number"),
  secondaryPhone: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, "Must be a valid 10-digit mobile number")
    .optional()
    .or(z.literal("")),
  email: z
    .string()
    .trim()
    .email("Please enter a valid email address")
    .optional()
    .or(z.literal("")),

  street: z
    .string()
    .trim()
    .min(3, "Street address / locality is required"),
  city: z.string().trim().min(2, "City / District is required"),
  state: z.string().min(1, "State is required"),
  pincode: z
    .string()
    .trim()
    .regex(/^\d{6}$/, "Must be a valid 6-digit PIN code"),
  country: z.string().default("India"),

  // Guardian details
  guardianName: z.string().trim().optional(),
  guardianRelationship: z.string().optional(),
  guardianPhone: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, "Guardian phone must be a 10-digit mobile number")
    .optional()
    .or(z.literal("")),
  guardianAddressSameAsPatient: z.boolean().default(true),
  guardianAddress: z.string().trim().optional(),

  // Identity Reference
  identityType: z.string().optional(),
  identityNumber: z.string().trim().optional(),

  // Photo
  photoUrl: z.string().optional(),

  // ABHA
  abhaNumber: z
    .string()
    .trim()
    .optional()
    .refine(
      (val) => {
        if (!val) return true;
        const digits = val.replace(/\D/g, "");
        return digits.length === 14;
      },
      { message: "ABHA Number must be 14 digits (XX-XXXX-XXXX-XXXX)" }
    ),
  abhaAddress: z
    .string()
    .trim()
    .optional()
    .refine(
      (val) => {
        if (!val) return true;
        return /^[a-zA-Z0-9._-]+@(abdm|sbx|ndhm|hisp)$/i.test(val) || val.length >= 3;
      },
      { message: "ABHA Address format example: name@abdm or name@sbx" }
    ),
  abhaStatus: z
    .enum(["UNVERIFIED", "VERIFIED", "PENDING", "LINKED"])
    .default("UNVERIFIED"),
});

export const patientRegistrationFormSchema = patientRegistrationBaseSchema.superRefine((data, ctx) => {
  // If minor, require guardian name and relationship
  if (data.ageYears < 18) {
    if (!data.guardianName || data.guardianName.trim().length < 2) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["guardianName"],
        message: "Guardian name is required for minor patients (< 18 years)",
      });
    }
    if (!data.guardianRelationship) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["guardianRelationship"],
        message: "Guardian relationship is required for minor patients",
      });
    }
  }

  // If identity type is selected, number should not be blank
  if (data.identityType && (!data.identityNumber || data.identityNumber.trim().length === 0)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["identityNumber"],
      message: "Identity document number is required when ID type is selected",
    });
  }

  // Aadhaar specific validation if selected
  if (data.identityType === "AADHAAR" && data.identityNumber) {
    const cleanAadhaar = data.identityNumber.replace(/\s|-/g, "");
    if (!/^\d{12}$/.test(cleanAadhaar)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["identityNumber"],
        message: "Aadhaar number must be exactly 12 digits",
      });
    }
  }

  // PAN specific validation if selected
  if (data.identityType === "PAN_CARD" && data.identityNumber) {
    const cleanPan = data.identityNumber.trim().toUpperCase();
    if (!/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(cleanPan)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["identityNumber"],
        message: "PAN must follow standard format (e.g., ABCDE1234F)",
      });
    }
  }
});

export type PatientRegistrationFormData = z.infer<
  typeof patientRegistrationBaseSchema
>;

export interface PatientSearchParams {
  query?: string;
  uid?: string;
  mrn?: string;
  name?: string;
  mobile?: string;
  identityNumber?: string;
  abhaNumber?: string;
  gender?: Gender | "ALL";
  bloodGroup?: BloodGroup | "ALL";
  isMinor?: boolean;
  registeredDateFrom?: string;
  registeredDateTo?: string;
}
