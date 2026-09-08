import {
  Patient,
  PatientRegistrationFormData,
  PatientSearchParams,
  IdentityType,
  BloodGroup,
  Gender,
} from "@/types/patient";

const STORAGE_KEY = "foracare_patients_store";
const SEQUENCE_KEY = "foracare_patient_seq";

export const INITIAL_SEED_PATIENTS: Patient[] = [
  {
    id: "pat-seed-001",
    uid: "FC01-202609-000102",
    mrn: "MRN-2026-000102",
    title: "Mrs.",
    firstName: "Sunita",
    lastName: "Verma",
    fullName: "Sunita Verma",
    gender: "FEMALE",
    dob: "1982-04-15",
    ageYears: 44,
    ageMonths: 4,
    ageDays: 23,
    isMinor: false,
    bloodGroup: "B_POSITIVE",
    maritalStatus: "MARRIED",
    occupation: "School Teacher",
    preferredLanguage: "Hindi",
    mobile: "9876543210",
    email: "sunita.verma@example.com",
    address: {
      street: "Flat 402, Green Valley Apartments, MG Road",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560001",
      country: "India",
    },
    guardian: {
      name: "Ramesh Verma",
      relationship: "SPOUSE",
      phone: "9876543211",
      address: "Flat 402, Green Valley Apartments, MG Road, Bengaluru",
    },
    primaryIdentity: {
      type: "AADHAAR",
      idNumber: "567812349012",
      isVerified: true,
    },
    photoUrl: "",
    abha: {
      abhaNumber: "91-4521-8890-1204",
      abhaAddress: "sunita.verma@abdm",
      status: "VERIFIED",
      verifiedAt: "2026-09-01T09:30:00Z",
    },
    tenantId: "ten-001",
    facilityId: "fac-001",
    facilityName: "ForaCare City Hospital (Main Branch)",
    registeredAt: "2026-09-01T09:30:00Z",
    updatedAt: "2026-09-01T09:30:00Z",
    registeredBy: "Pooja Sharma (Receptionist)",
    status: "ACTIVE",
  },
  {
    id: "pat-seed-002",
    uid: "FC01-202609-000105",
    mrn: "MRN-2026-000105",
    title: "Mr.",
    firstName: "Rajesh",
    lastName: "Kumar",
    fullName: "Rajesh Kumar",
    gender: "MALE",
    dob: "1978-11-20",
    ageYears: 47,
    ageMonths: 9,
    ageDays: 18,
    isMinor: false,
    bloodGroup: "O_POSITIVE",
    maritalStatus: "MARRIED",
    occupation: "Business Executive",
    preferredLanguage: "English",
    mobile: "9812345678",
    email: "rajesh.kumar78@example.com",
    address: {
      street: "House No 84, Indiranagar 2nd Stage",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560038",
      country: "India",
    },
    guardian: {
      name: "Meena Kumar",
      relationship: "SPOUSE",
      phone: "9812345679",
    },
    primaryIdentity: {
      type: "PAN_CARD",
      idNumber: "ABCDE1234F",
      isVerified: true,
    },
    photoUrl: "",
    abha: {
      abhaNumber: "91-3344-5566-7788",
      abhaAddress: "rajesh.kumar@sbx",
      status: "LINKED",
      verifiedAt: "2026-09-02T11:15:00Z",
    },
    tenantId: "ten-001",
    facilityId: "fac-001",
    facilityName: "ForaCare City Hospital (Main Branch)",
    registeredAt: "2026-09-02T11:15:00Z",
    updatedAt: "2026-09-02T11:15:00Z",
    registeredBy: "Pooja Sharma (Receptionist)",
    status: "ACTIVE",
  },
  {
    id: "pat-seed-003",
    uid: "FC01-202609-000098",
    mrn: "MRN-2026-000098",
    title: "Ms.",
    firstName: "Ananya",
    lastName: "Sharma",
    fullName: "Ananya Sharma",
    gender: "FEMALE",
    dob: "1997-03-08",
    ageYears: 29,
    ageMonths: 5,
    ageDays: 30,
    isMinor: false,
    bloodGroup: "A_POSITIVE",
    maritalStatus: "SINGLE",
    occupation: "Software Engineer",
    preferredLanguage: "English",
    mobile: "9945678901",
    email: "ananya.sharma@techcorp.io",
    address: {
      street: "Flat 12B, Prestige Cyber Towers, Whitefield",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560066",
      country: "India",
    },
    primaryIdentity: {
      type: "PASSPORT",
      idNumber: "Z8942105",
      isVerified: true,
    },
    photoUrl: "",
    abha: {
      abhaNumber: "91-1122-3344-5566",
      abhaAddress: "ananya.sharma@abdm",
      status: "VERIFIED",
      verifiedAt: "2026-08-28T14:20:00Z",
    },
    tenantId: "ten-001",
    facilityId: "fac-001",
    facilityName: "ForaCare City Hospital (Main Branch)",
    registeredAt: "2026-08-28T14:20:00Z",
    updatedAt: "2026-08-28T14:20:00Z",
    registeredBy: "Amit Patel (Cashier)",
    status: "ACTIVE",
  },
  {
    id: "pat-seed-004",
    uid: "FC01-202609-000109",
    mrn: "MRN-2026-000109",
    title: "Master",
    firstName: "Aarav",
    lastName: "Patel",
    fullName: "Aarav Patel",
    gender: "MALE",
    dob: "2019-07-22",
    ageYears: 7,
    ageMonths: 1,
    ageDays: 16,
    isMinor: true,
    bloodGroup: "O_POSITIVE",
    maritalStatus: "SINGLE",
    preferredLanguage: "Gujarati",
    mobile: "9723456780",
    address: {
      street: "B-14, Shanti Niketan Society, Outer Ring Road",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560103",
      country: "India",
    },
    guardian: {
      name: "Vikram Patel",
      relationship: "FATHER",
      phone: "9723456780",
      address: "B-14, Shanti Niketan Society, Outer Ring Road, Bengaluru",
    },
    primaryIdentity: {
      type: "AADHAAR",
      idNumber: "458923019944",
      isVerified: false,
    },
    photoUrl: "",
    abha: {
      status: "UNVERIFIED",
    },
    tenantId: "ten-001",
    facilityId: "fac-001",
    facilityName: "ForaCare City Hospital (Main Branch)",
    registeredAt: "2026-09-03T16:05:00Z",
    updatedAt: "2026-09-03T16:05:00Z",
    registeredBy: "Pooja Sharma (Receptionist)",
    status: "ACTIVE",
  },
  {
    id: "pat-seed-005",
    uid: "FC01-202609-000114",
    mrn: "MRN-2026-000114",
    title: "Mr.",
    firstName: "Mohammed",
    middleName: "Irfan",
    lastName: "Khan",
    fullName: "Mohammed Irfan Khan",
    gender: "MALE",
    dob: "1965-10-10",
    ageYears: 60,
    ageMonths: 10,
    ageDays: 28,
    isMinor: false,
    bloodGroup: "AB_POSITIVE",
    maritalStatus: "MARRIED",
    occupation: "Retired Civil Officer",
    preferredLanguage: "Urdu",
    mobile: "9448123987",
    email: "irfan.khan@example.org",
    address: {
      street: "No. 29, Crescent Road, High Grounds",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560001",
      country: "India",
    },
    guardian: {
      name: "Farhan Khan",
      relationship: "SON",
      phone: "9448123999",
    },
    primaryIdentity: {
      type: "VOTER_ID",
      idNumber: "KAR0981245",
      isVerified: true,
    },
    photoUrl: "",
    abha: {
      abhaNumber: "91-7788-9900-1122",
      abhaAddress: "irfan.khan@abdm",
      status: "VERIFIED",
      verifiedAt: "2026-09-04T10:00:00Z",
    },
    tenantId: "ten-001",
    facilityId: "fac-001",
    facilityName: "ForaCare City Hospital (Main Branch)",
    registeredAt: "2026-09-04T10:00:00Z",
    updatedAt: "2026-09-04T10:00:00Z",
    registeredBy: "Pooja Sharma (Receptionist)",
    status: "ACTIVE",
  },
];

/**
 * Reads all patients from localStorage or loads initial seeds.
 */
export function getPatients(): Patient[] {
  if (typeof window === "undefined") {
    return INITIAL_SEED_PATIENTS;
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_PATIENTS));
      return INITIAL_SEED_PATIENTS;
    }
    return JSON.parse(raw) as Patient[];
  } catch (err) {
    console.error("Failed to read patients from storage", err);
    return INITIAL_SEED_PATIENTS;
  }
}

/**
 * Saves patients array to storage.
 */
function savePatients(patients: Patient[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(patients));
  } catch (err) {
    console.error("Failed to persist patients", err);
  }
}

/**
 * Generates the next sequential UID formatted as <FACILITY_CODE>-YYYYMM-<6_DIGIT_SEQ>
 */
export function generateNextUID(facilityCode = "FC01"): { uid: string; mrn: string } {
  let seq = 115;
  if (typeof window !== "undefined") {
    const rawSeq = localStorage.getItem(SEQUENCE_KEY);
    if (rawSeq) {
      seq = parseInt(rawSeq, 10) + 1;
    }
    localStorage.setItem(SEQUENCE_KEY, String(seq));
  }
  
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const seqStr = String(seq).padStart(6, "0");
  
  const uid = `${facilityCode}-${year}${month}-${seqStr}`;
  const mrn = `MRN-${year}-${seqStr}`;
  return { uid, mrn };
}

/**
 * Checks for potential duplicate patients by phone, Aadhaar/Govt ID, or Name + Year of Birth.
 */
export function checkDuplicates(params: {
  mobile?: string;
  identityType?: string;
  identityNumber?: string;
  name?: string;
  dob?: string;
  excludeId?: string;
}): Patient[] {
  const patients = getPatients();
  const matches: Patient[] = [];

  const cleanMobile = params.mobile?.trim();
  const cleanId = params.identityNumber?.trim().toLowerCase();
  const cleanName = params.name?.trim().toLowerCase();
  const birthYear = params.dob ? new Date(params.dob).getFullYear() : null;

  for (const pat of patients) {
    if (params.excludeId && pat.id === params.excludeId) continue;

    // Mobile exact match
    if (cleanMobile && (pat.mobile === cleanMobile || pat.secondaryPhone === cleanMobile)) {
      matches.push(pat);
      continue;
    }

    // Identity number exact match
    if (
      cleanId &&
      pat.primaryIdentity?.idNumber &&
      pat.primaryIdentity.idNumber.toLowerCase() === cleanId
    ) {
      matches.push(pat);
      continue;
    }

    // Name + Year of birth match
    if (cleanName && birthYear && pat.fullName.toLowerCase() === cleanName) {
      const patYear = new Date(pat.dob).getFullYear();
      if (patYear === birthYear) {
        matches.push(pat);
        continue;
      }
    }
  }

  return matches;
}

/**
 * Registers a new patient, saves to persistent store, and returns the created Patient object.
 */
export function registerPatient(
  formData: PatientRegistrationFormData,
  options?: {
    facilityCode?: string;
    facilityId?: string;
    facilityName?: string;
    tenantId?: string;
    registeredBy?: string;
  }
): Patient {
  const patients = getPatients();
  const facilityCode = options?.facilityCode || "FC01";
  const { uid, mrn } = generateNextUID(facilityCode);

  const fullName = [formData.title, formData.firstName, formData.middleName, formData.lastName]
    .filter(Boolean)
    .join(" ");

  const nowIso = new Date().toISOString();

  const newPatient: Patient = {
    id: `pat-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    uid,
    mrn,
    title: formData.title,
    firstName: formData.firstName.trim(),
    middleName: formData.middleName?.trim() || undefined,
    lastName: formData.lastName.trim(),
    fullName,
    gender: formData.gender as Gender,
    dob: formData.dob,
    ageYears: formData.ageYears,
    ageMonths: formData.ageMonths,
    ageDays: formData.ageDays,
    isMinor: formData.ageYears < 18,
    bloodGroup: formData.bloodGroup as BloodGroup,
    maritalStatus: formData.maritalStatus,
    occupation: formData.occupation?.trim(),
    preferredLanguage: formData.preferredLanguage,
    mobile: formData.mobile.trim(),
    secondaryPhone: formData.secondaryPhone?.trim() || undefined,
    email: formData.email?.trim() || undefined,
    address: {
      street: formData.street.trim(),
      city: formData.city.trim(),
      state: formData.state,
      pincode: formData.pincode.trim(),
      country: formData.country || "India",
    },
    guardian:
      formData.guardianName || formData.guardianPhone
        ? {
            name: formData.guardianName?.trim(),
            relationship: formData.guardianRelationship,
            phone: formData.guardianPhone?.trim(),
            address: formData.guardianAddressSameAsPatient
              ? `${formData.street}, ${formData.city}, ${formData.state} - ${formData.pincode}`
              : formData.guardianAddress?.trim(),
          }
        : undefined,
    primaryIdentity: formData.identityType
      ? {
          type: formData.identityType as IdentityType,
          idNumber: formData.identityNumber?.trim() || "",
          isVerified: false,
        }
      : undefined,
    photoUrl: formData.photoUrl,
    abha: {
      abhaNumber: formData.abhaNumber?.trim() || undefined,
      abhaAddress: formData.abhaAddress?.trim() || undefined,
      status: formData.abhaStatus,
      verifiedAt:
        formData.abhaStatus === "VERIFIED" || formData.abhaStatus === "LINKED"
          ? nowIso
          : undefined,
    },
    tenantId: options?.tenantId || "ten-001",
    facilityId: options?.facilityId || "fac-001",
    facilityName:
      options?.facilityName || "ForaCare City Hospital (Main Branch)",
    registeredAt: nowIso,
    updatedAt: nowIso,
    registeredBy: options?.registeredBy || "Front Desk Receptionist",
    status: "ACTIVE",
  };

  const updatedList = [newPatient, ...patients];
  savePatients(updatedList);
  return newPatient;
}

/**
 * Searches patients across multi-criteria:
 * - Patient UID
 * - MRN
 * - Full Name / partial name
 * - Mobile Phone
 * - Approved identity references (Aadhaar, Voter ID, Passport, PAN, DL, Ration Card)
 * - ABHA Number / Address
 * - Filters: Gender, Blood group, Minor, Date
 */
export function searchPatients(params: PatientSearchParams): Patient[] {
  const patients = getPatients();
  const q = params.query?.trim().toLowerCase();

  return patients.filter((pat) => {
    // Universal query search
    if (q) {
      const matchUid = pat.uid.toLowerCase().includes(q);
      const matchMrn = pat.mrn.toLowerCase().includes(q);
      const matchName = pat.fullName.toLowerCase().includes(q);
      const matchMobile =
        pat.mobile.includes(q) || (pat.secondaryPhone && pat.secondaryPhone.includes(q));
      const matchIdentity =
        pat.primaryIdentity?.idNumber &&
        pat.primaryIdentity.idNumber.toLowerCase().includes(q);
      const matchAbha =
        (pat.abha.abhaNumber && pat.abha.abhaNumber.includes(q)) ||
        (pat.abha.abhaAddress && pat.abha.abhaAddress.toLowerCase().includes(q));
      const matchGuardian =
        pat.guardian?.name && pat.guardian.name.toLowerCase().includes(q);
      const matchCity = pat.address.city.toLowerCase().includes(q);

      if (
        !matchUid &&
        !matchMrn &&
        !matchName &&
        !matchMobile &&
        !matchIdentity &&
        !matchAbha &&
        !matchGuardian &&
        !matchCity
      ) {
        return false;
      }
    }

    // Specific field filters
    if (params.uid && !pat.uid.toLowerCase().includes(params.uid.toLowerCase())) {
      return false;
    }
    if (params.mrn && !pat.mrn.toLowerCase().includes(params.mrn.toLowerCase())) {
      return false;
    }
    if (params.name && !pat.fullName.toLowerCase().includes(params.name.toLowerCase())) {
      return false;
    }
    if (params.mobile && !pat.mobile.includes(params.mobile)) {
      return false;
    }
    if (
      params.identityNumber &&
      (!pat.primaryIdentity?.idNumber ||
        !pat.primaryIdentity.idNumber.toLowerCase().includes(params.identityNumber.toLowerCase()))
    ) {
      return false;
    }
    if (
      params.abhaNumber &&
      (!pat.abha.abhaNumber || !pat.abha.abhaNumber.includes(params.abhaNumber))
    ) {
      return false;
    }
    if (params.gender && params.gender !== "ALL" && pat.gender !== params.gender) {
      return false;
    }
    if (
      params.bloodGroup &&
      params.bloodGroup !== "ALL" &&
      pat.bloodGroup !== params.bloodGroup
    ) {
      return false;
    }
    if (params.isMinor !== undefined && pat.isMinor !== params.isMinor) {
      return false;
    }

    return true;
  });
}

/**
 * Retrieves a single patient by either UID or internal ID.
 */
export function getPatientById(uidOrId: string): Patient | undefined {
  const patients = getPatients();
  return patients.find(
    (p) =>
      p.id.toLowerCase() === uidOrId.toLowerCase() ||
      p.uid.toLowerCase() === uidOrId.toLowerCase() ||
      p.mrn.toLowerCase() === uidOrId.toLowerCase()
  );
}

/**
 * Calculates exact age in years, months, and days from Date of Birth.
 */
export function calculateAgeFromDob(dobString: string): {
  years: number;
  months: number;
  days: number;
} {
  const dob = new Date(dobString);
  const today = new Date();

  if (isNaN(dob.getTime()) || dob > today) {
    return { years: 0, months: 0, days: 0 };
  }

  let years = today.getFullYear() - dob.getFullYear();
  let months = today.getMonth() - dob.getMonth();
  let days = today.getDate() - dob.getDate();

  if (days < 0) {
    months -= 1;
    // Get days in previous month
    const prevMonth = new Date(today.getFullYear(), today.getMonth(), 0);
    days += prevMonth.getDate();
  }

  if (months < 0) {
    years -= 1;
    months += 12;
  }

  return {
    years: Math.max(0, years),
    months: Math.max(0, months),
    days: Math.max(0, days),
  };
}

/**
 * Calculates approximate DOB from age in years.
 */
export function calculateDobFromAge(years: number): string {
  const today = new Date();
  const birthYear = today.getFullYear() - years;
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${birthYear}-${month}-${day}`;
}

/**
 * Simulates ABDM M1 / Aadhaar OTP verification and demographic autofill.
 */
export function simulateAbdmOtpVerification(mobileOrAadhaar: string): {
  success: boolean;
  demoData?: Partial<PatientRegistrationFormData>;
  abhaNumber: string;
  abhaAddress: string;
} {
  const randomSuffix = Math.floor(1000 + Math.random() * 9000);
  const abhaNumber = `91-${Math.floor(1000 + Math.random() * 9000)}-${Math.floor(
    1000 + Math.random() * 9000
  )}-${randomSuffix}`;
  const abhaAddress = `patient_${randomSuffix}@abdm`;

  return {
    success: true,
    abhaNumber,
    abhaAddress,
    demoData: {
      abhaNumber,
      abhaAddress,
      abhaStatus: "VERIFIED",
      identityType: "AADHAAR",
      identityNumber: mobileOrAadhaar.length === 12 ? mobileOrAadhaar : "982341908712",
    },
  };
}
