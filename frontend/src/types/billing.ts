// Mirrors backend/app/modules/billing/schemas.py (Phase 5).

export const PAYMENT_MODES = [
  { value: "CASH", label: "Cash" },
  { value: "CARD", label: "Card" },
  { value: "UPI", label: "UPI" },
  { value: "INSURANCE", label: "Insurance" },
  { value: "CORPORATE", label: "Corporate" },
  { value: "FREE", label: "Free / Waived" },
  { value: "OTHER", label: "Other" },
] as const;
export type PaymentMode = (typeof PAYMENT_MODES)[number]["value"];

export const SERVICE_CATEGORIES = [
  { value: "CONSULTATION", label: "Consultation" },
  { value: "PROCEDURE", label: "Procedure" },
  { value: "DIAGNOSTIC", label: "Diagnostic" },
  { value: "ROOM_CHARGE", label: "Room Charge" },
  { value: "PHARMACY", label: "Pharmacy" },
  { value: "OTHER", label: "Other" },
] as const;
export type ServiceCategory = (typeof SERVICE_CATEGORIES)[number]["value"];

export type InvoiceStatus = "FINALIZED" | "PARTIALLY_PAID" | "PAID" | "CANCELLED";

export const INVOICE_STATUS_BADGE_CLASS: Record<InvoiceStatus, string> = {
  FINALIZED: "bg-amber-50 text-amber-700 border-amber-300",
  PARTIALLY_PAID: "bg-sky-50 text-sky-700 border-sky-300",
  PAID: "bg-emerald-50 text-emerald-700 border-emerald-300",
  CANCELLED: "bg-slate-100 text-slate-500 border-slate-300",
};

export type InvoiceItemType = "SERVICE" | "PACKAGE" | "CUSTOM";

export type PaymentStatus = "COMPLETED" | "REFUNDED";
export type DepositStatus = "ACTIVE" | "REFUNDED";
export type ReceiptType = "PAYMENT" | "DEPOSIT" | "REFUND";

export interface BillingService {
  id: string;
  departmentId?: string;
  name: string;
  code: string;
  category: ServiceCategory;
  price: number;
  description?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface BillingServiceFormData {
  name: string;
  code: string;
  category: ServiceCategory;
  price: string;
  departmentId: string;
  description: string;
}

export interface BillingPackage {
  id: string;
  name: string;
  code: string;
  price: number;
  description?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface BillingPackageFormData {
  name: string;
  code: string;
  price: string;
  description: string;
}

export interface InvoiceItem {
  id: string;
  serviceId?: string;
  packageId?: string;
  itemType: InvoiceItemType;
  description: string;
  quantity: number;
  unitPrice: number;
  discountAmount: number;
  taxAmount: number;
  totalAmount: number;
}

// A line item as it's being built in the invoice-creation form, before
// submission - not yet server-priced/validated.
export interface InvoiceItemDraft {
  key: string;
  itemType: InvoiceItemType;
  serviceId?: string;
  packageId?: string;
  description: string;
  quantity: string;
  unitPrice: string;
  discountAmount: string;
  taxAmount: string;
}

export interface Invoice {
  id: string;
  patientId: string;
  admissionId?: string;
  invoiceNumber: string;
  status: InvoiceStatus;
  subtotal: number;
  discountAmount: number;
  taxAmount: number;
  totalAmount: number;
  amountPaid: number;
  amountDue: number;
  notes?: string;
  invoiceDate: string;
  createdAt: string;
  updatedAt: string;
  items: InvoiceItem[];
}

export interface InvoiceBalance {
  invoiceId: string;
  invoiceNumber: string;
  status: InvoiceStatus;
  totalAmount: number;
  amountPaid: number;
  amountDue: number;
}

export interface Payment {
  id: string;
  invoiceId: string;
  amount: number;
  paymentMode: PaymentMode;
  referenceNumber?: string;
  notes?: string;
  status: PaymentStatus;
  recordedAt: string;
}

export interface Deposit {
  id: string;
  patientId: string;
  admissionId?: string;
  amount: number;
  paymentMode: PaymentMode;
  referenceNumber?: string;
  notes?: string;
  status: DepositStatus;
  recordedAt: string;
}

export interface Refund {
  id: string;
  paymentId?: string;
  depositId?: string;
  amount: number;
  reason: string;
  refundMode: PaymentMode;
  gatewayReference?: string;
  notes?: string;
  status: string;
  recordedAt: string;
}

export interface Receipt {
  id: string;
  patientId: string;
  paymentId?: string;
  depositId?: string;
  refundId?: string;
  receiptNumber: string;
  receiptType: ReceiptType;
  amount: number;
  issuedAt: string;
}
