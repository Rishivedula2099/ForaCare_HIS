/**
 * P10-F02: client-side checks for the setup wizard. They only give instant
 * feedback - the API repeats every rule and is the real gate - so keep them in
 * step with backend/app/modules/platform/schemas.py.
 */

export interface SetupForm {
  orgName: string;
  orgCode: string;
  facilityName: string;
  facilityCode: string;
  facilityType: string;
  phone: string;
  email: string;
  addressLine1: string;
  addressLine2: string;
  city: string;
  state: string;
  postalCode: string;
  timezone: string;
  currency: string;
  adminName: string;
  adminUsername: string;
  adminEmail: string;
  sendEmail: boolean;
}

export type SetupErrors = Partial<Record<keyof SetupForm, string>>;

export interface StepDef {
  id: string;
  title: string;
  fields: (keyof SetupForm)[];
}

export const STEPS: StepDef[] = [
  { id: "organization", title: "Organisation", fields: ["orgName", "orgCode"] },
  { id: "facility", title: "Facility", fields: ["facilityName", "facilityCode", "facilityType"] },
  {
    id: "contact",
    title: "Contact & address",
    fields: ["phone", "email", "addressLine1", "addressLine2", "city", "state", "postalCode"],
  },
  { id: "operations", title: "Operations", fields: ["timezone", "currency"] },
  { id: "administrator", title: "Administrator", fields: ["adminName", "adminUsername", "adminEmail"] },
  { id: "review", title: "Review & create", fields: [] },
];

const CODE = /^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$/;
const USERNAME = /^[A-Za-z0-9._-]{3,100}$/;
const PHONE = /^\+?[0-9][0-9 ()-]{6,19}$/;
const POSTAL = /^[A-Za-z0-9][A-Za-z0-9 -]{2,11}$/;
// Deliberately loose: the server applies the strict check (and rejects reserved domains).
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const clean = (v: string) => v.trim().replace(/\s+/g, " ");

export const EMPTY_FORM: SetupForm = {
  orgName: "",
  orgCode: "",
  facilityName: "",
  facilityCode: "",
  facilityType: "",
  phone: "",
  email: "",
  addressLine1: "",
  addressLine2: "",
  city: "",
  state: "",
  postalCode: "",
  timezone: "",
  currency: "",
  adminName: "",
  adminUsername: "",
  adminEmail: "",
  sendEmail: false,
};

export function validateField(field: keyof SetupForm, form: SetupForm): string | undefined {
  const raw = form[field];
  const v = typeof raw === "string" ? clean(raw) : "";
  const need = (label: string, min = 2, max = 255) =>
    !v ? `${label} is required.` : v.length < min ? `${label} is too short.` : v.length > max ? `${label} is too long.` : undefined;

  switch (field) {
    case "orgName":
      return need("Organisation name");
    case "orgCode":
      return !v ? "Organisation code is required." : CODE.test(v) ? undefined : "Use 2-50 letters, digits, '-' or '_'.";
    case "facilityName":
      return need("Facility name");
    case "facilityCode":
      return !v ? "Facility code is required." : CODE.test(v) ? undefined : "Use 2-50 letters, digits, '-' or '_'.";
    case "facilityType":
      return v ? undefined : "Choose a facility type.";
    case "phone":
      return !v ? "Phone number is required." : PHONE.test(v) ? undefined : "Enter a valid phone number (7-20 digits; may start with +).";
    case "email":
      return !v ? "Contact email is required." : EMAIL.test(v) ? undefined : "Enter a valid email address.";
    case "addressLine1":
      return need("Address", 3, 200);
    case "addressLine2":
      return v.length > 200 ? "Address line 2 is too long." : undefined;
    case "city":
      return need("City", 2, 100);
    case "state":
      return need("State / province", 2, 100);
    case "postalCode":
      return !v ? "Postal / PIN code is required." : POSTAL.test(v) ? undefined : "Enter a valid postal / PIN code.";
    case "timezone":
      return v ? undefined : "Choose a time zone.";
    case "currency":
      return v ? undefined : "Choose a currency.";
    case "adminName":
      return need("Administrator name");
    case "adminUsername":
      return !v ? "Username is required." : USERNAME.test(v) ? undefined : "Use 3-100 letters, digits, '.', '_' or '-'.";
    case "adminEmail":
      return !v ? "Administrator email is required." : EMAIL.test(v) ? undefined : "Enter a valid email address.";
    default:
      return undefined;
  }
}

export function validateStep(stepIndex: number, form: SetupForm): SetupErrors {
  const errors: SetupErrors = {};
  for (const field of STEPS[stepIndex].fields) {
    const message = validateField(field, form);
    if (message) errors[field] = message;
  }
  return errors;
}

export function validateAll(form: SetupForm): SetupErrors {
  return STEPS.reduce<SetupErrors>((all, _step, i) => ({ ...all, ...validateStep(i, form) }), {});
}

/** Which step owns a form field (for jumping to the first problem). */
export function stepOf(field: keyof SetupForm): number {
  return STEPS.findIndex((s) => s.fields.includes(field));
}

const SERVER_FIELD_MAP: Record<string, keyof SetupForm> = {
  "organization.name": "orgName",
  "organization.code": "orgCode",
  "facility.name": "facilityName",
  "facility.facility_code": "facilityCode",
  "facility.facility_type": "facilityType",
  "facility.phone": "phone",
  "facility.email": "email",
  "facility.address_line1": "addressLine1",
  "facility.address_line2": "addressLine2",
  "facility.city": "city",
  "facility.state": "state",
  "facility.postal_code": "postalCode",
  "facility.timezone": "timezone",
  "facility.currency": "currency",
  "administrator.full_name": "adminName",
  "administrator.username": "adminUsername",
  "administrator.email": "adminEmail",
};

/** Maps backend field paths (e.g. "body.facility.postal_code") onto form fields. */
export function mapServerErrors(details: { field?: string | null; message: string }[]): SetupErrors {
  const errors: SetupErrors = {};
  for (const detail of details) {
    const path = (detail.field ?? "").replace(/^body\./, "");
    const field = SERVER_FIELD_MAP[path];
    if (field && !errors[field]) errors[field] = detail.message;
  }
  return errors;
}

/** Suggests a code from a name, e.g. "Green Valley Hospital" -> "GVH". */
export function suggestCode(name: string): string {
  const words = name.replace(/[^A-Za-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  if (words.length === 0) return "";
  const initials = words.length > 1 ? words.map((w) => w[0]).join("") : words[0].slice(0, 6);
  return initials.toUpperCase().slice(0, 12);
}

export function toPayload(form: SetupForm) {
  return {
    organization: { name: clean(form.orgName), code: form.orgCode.trim().toUpperCase() },
    facility: {
      name: clean(form.facilityName),
      facility_code: form.facilityCode.trim().toUpperCase(),
      facility_type: form.facilityType,
      phone: form.phone.trim(),
      email: form.email.trim(),
      address_line1: clean(form.addressLine1),
      address_line2: clean(form.addressLine2) || null,
      city: clean(form.city),
      state: clean(form.state),
      postal_code: form.postalCode.trim().toUpperCase(),
      timezone: form.timezone,
      currency: form.currency,
    },
    administrator: {
      full_name: clean(form.adminName),
      username: form.adminUsername.trim(),
      email: form.adminEmail.trim(),
    },
    send_activation_email: form.sendEmail,
  };
}
