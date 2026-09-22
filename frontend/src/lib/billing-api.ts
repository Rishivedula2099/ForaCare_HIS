/**
 * Thin typed wrapper over `apiClient` for the Phase 5 Billing backend
 * (backend/app/api/v1/billing.py), plus the camelCase (frontend
 * `types/billing.ts`) <-> snake_case (backend `*Out`/`*Request`) mapping.
 */

import { apiClient } from "@/lib/api-client";
import {
  BillingPackage,
  BillingPackageFormData,
  BillingService,
  BillingServiceFormData,
  Deposit,
  Invoice,
  InvoiceBalance,
  InvoiceItem,
  InvoiceItemDraft,
  Payment,
  Receipt,
  Refund,
} from "@/types/billing";

// ---------------------------------------------------------------------------
// Backend shapes (snake_case)
// ---------------------------------------------------------------------------

export interface BackendServiceOut {
  id: string;
  department_id: string | null;
  name: string;
  code: string;
  category: string;
  price: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackendPackageOut {
  id: string;
  name: string;
  code: string;
  price: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackendInvoiceItemOut {
  id: string;
  service_id: string | null;
  package_id: string | null;
  item_type: string;
  description: string;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
}

export interface BackendInvoiceOut {
  id: string;
  patient_id: string;
  admission_id: string | null;
  invoice_number: string;
  status: string;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  amount_due: number;
  notes: string | null;
  invoice_date: string;
  created_at: string;
  updated_at: string;
  items: BackendInvoiceItemOut[];
}

export interface BackendInvoiceBalanceOut {
  invoice_id: string;
  invoice_number: string;
  status: string;
  total_amount: number;
  amount_paid: number;
  amount_due: number;
}

export interface BackendPaymentOut {
  id: string;
  invoice_id: string;
  amount: number;
  payment_mode: string;
  reference_number: string | null;
  notes: string | null;
  status: string;
  recorded_at: string;
}

export interface BackendDepositOut {
  id: string;
  patient_id: string;
  admission_id: string | null;
  amount: number;
  payment_mode: string;
  reference_number: string | null;
  notes: string | null;
  status: string;
  recorded_at: string;
}

export interface BackendRefundOut {
  id: string;
  payment_id: string | null;
  deposit_id: string | null;
  amount: number;
  reason: string;
  refund_mode: string;
  gateway_reference: string | null;
  notes: string | null;
  status: string;
  recorded_at: string;
}

export interface BackendReceiptOut {
  id: string;
  patient_id: string;
  payment_id: string | null;
  deposit_id: string | null;
  refund_id: string | null;
  receipt_number: string;
  receipt_type: string;
  amount: number;
  issued_at: string;
}

// ---------------------------------------------------------------------------
// snake_case <-> camelCase mapping
// ---------------------------------------------------------------------------

export function fromBackendService(service: BackendServiceOut): BillingService {
  return {
    id: service.id,
    departmentId: service.department_id ?? undefined,
    name: service.name,
    code: service.code,
    category: service.category as BillingService["category"],
    price: Number(service.price),
    description: service.description ?? undefined,
    isActive: service.is_active,
    createdAt: service.created_at,
    updatedAt: service.updated_at,
  };
}

export function fromBackendPackage(pkg: BackendPackageOut): BillingPackage {
  return {
    id: pkg.id,
    name: pkg.name,
    code: pkg.code,
    price: Number(pkg.price),
    description: pkg.description ?? undefined,
    isActive: pkg.is_active,
    createdAt: pkg.created_at,
    updatedAt: pkg.updated_at,
  };
}

function fromBackendInvoiceItem(item: BackendInvoiceItemOut): InvoiceItem {
  return {
    id: item.id,
    serviceId: item.service_id ?? undefined,
    packageId: item.package_id ?? undefined,
    itemType: item.item_type as InvoiceItem["itemType"],
    description: item.description,
    quantity: Number(item.quantity),
    unitPrice: Number(item.unit_price),
    discountAmount: Number(item.discount_amount),
    taxAmount: Number(item.tax_amount),
    totalAmount: Number(item.total_amount),
  };
}

export function fromBackendInvoice(invoice: BackendInvoiceOut): Invoice {
  return {
    id: invoice.id,
    patientId: invoice.patient_id,
    admissionId: invoice.admission_id ?? undefined,
    invoiceNumber: invoice.invoice_number,
    status: invoice.status as Invoice["status"],
    subtotal: Number(invoice.subtotal),
    discountAmount: Number(invoice.discount_amount),
    taxAmount: Number(invoice.tax_amount),
    totalAmount: Number(invoice.total_amount),
    amountPaid: Number(invoice.amount_paid),
    amountDue: Number(invoice.amount_due),
    notes: invoice.notes ?? undefined,
    invoiceDate: invoice.invoice_date,
    createdAt: invoice.created_at,
    updatedAt: invoice.updated_at,
    items: invoice.items.map(fromBackendInvoiceItem),
  };
}

export function fromBackendBalance(balance: BackendInvoiceBalanceOut): InvoiceBalance {
  return {
    invoiceId: balance.invoice_id,
    invoiceNumber: balance.invoice_number,
    status: balance.status as InvoiceBalance["status"],
    totalAmount: Number(balance.total_amount),
    amountPaid: Number(balance.amount_paid),
    amountDue: Number(balance.amount_due),
  };
}

export function fromBackendPayment(payment: BackendPaymentOut): Payment {
  return {
    id: payment.id,
    invoiceId: payment.invoice_id,
    amount: Number(payment.amount),
    paymentMode: payment.payment_mode as Payment["paymentMode"],
    referenceNumber: payment.reference_number ?? undefined,
    notes: payment.notes ?? undefined,
    status: payment.status as Payment["status"],
    recordedAt: payment.recorded_at,
  };
}

export function fromBackendDeposit(deposit: BackendDepositOut): Deposit {
  return {
    id: deposit.id,
    patientId: deposit.patient_id,
    admissionId: deposit.admission_id ?? undefined,
    amount: Number(deposit.amount),
    paymentMode: deposit.payment_mode as Deposit["paymentMode"],
    referenceNumber: deposit.reference_number ?? undefined,
    notes: deposit.notes ?? undefined,
    status: deposit.status as Deposit["status"],
    recordedAt: deposit.recorded_at,
  };
}

export function fromBackendRefund(refund: BackendRefundOut): Refund {
  return {
    id: refund.id,
    paymentId: refund.payment_id ?? undefined,
    depositId: refund.deposit_id ?? undefined,
    amount: Number(refund.amount),
    reason: refund.reason,
    refundMode: refund.refund_mode as Refund["refundMode"],
    gatewayReference: refund.gateway_reference ?? undefined,
    notes: refund.notes ?? undefined,
    status: refund.status,
    recordedAt: refund.recorded_at,
  };
}

export function fromBackendReceipt(receipt: BackendReceiptOut): Receipt {
  return {
    id: receipt.id,
    patientId: receipt.patient_id,
    paymentId: receipt.payment_id ?? undefined,
    depositId: receipt.deposit_id ?? undefined,
    refundId: receipt.refund_id ?? undefined,
    receiptNumber: receipt.receipt_number,
    receiptType: receipt.receipt_type as Receipt["receiptType"],
    amount: Number(receipt.amount),
    issuedAt: receipt.issued_at,
  };
}

export function toServiceCreatePayload(data: BillingServiceFormData) {
  return {
    name: data.name.trim(),
    code: data.code.trim().toUpperCase(),
    category: data.category,
    price: Number(data.price),
    department_id: data.departmentId || null,
    description: data.description.trim() || null,
  };
}

export function toPackageCreatePayload(data: BillingPackageFormData) {
  return {
    name: data.name.trim(),
    code: data.code.trim().toUpperCase(),
    price: Number(data.price),
    description: data.description.trim() || null,
  };
}

export function toInvoiceItemPayload(draft: InvoiceItemDraft) {
  return {
    item_type: draft.itemType,
    service_id: draft.itemType === "SERVICE" ? draft.serviceId : null,
    package_id: draft.itemType === "PACKAGE" ? draft.packageId : null,
    description: draft.itemType === "CUSTOM" ? draft.description.trim() : draft.description.trim() || null,
    quantity: Number(draft.quantity || "1"),
    unit_price: draft.unitPrice.trim() === "" ? null : Number(draft.unitPrice),
    discount_amount: Number(draft.discountAmount || "0"),
    tax_amount: Number(draft.taxAmount || "0"),
  };
}

// A random key per mutation *attempt* (a fresh key is generated only when
// the user (re)starts an action, not on every render/retry within that
// attempt) - see `Idempotency-Key` handling in
// backend/app/api/v1/billing.py. Retrying the exact same submission (e.g.
// this hook's own mutation retry, or the user clicking "Pay" again after a
// timeout without changing anything) reuses the same key so the backend
// recognizes it as the same attempt rather than a new payment.
export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `idem-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function idemHeaders(idempotencyKey?: string) {
  return idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined;
}

// ---------------------------------------------------------------------------
// Service master
// ---------------------------------------------------------------------------

export interface ListServicesParams {
  name?: string;
  is_active?: boolean;
}

export async function listServices(params: ListServicesParams = {}): Promise<BillingService[]> {
  const response = await apiClient.get<BackendServiceOut[]>("/billing/services", { params });
  return (response.data ?? []).map(fromBackendService);
}

export async function createService(payload: ReturnType<typeof toServiceCreatePayload>): Promise<BillingService> {
  const response = await apiClient.post<BackendServiceOut>("/billing/services", payload);
  if (!response.data) throw new Error("Failed to create service");
  return fromBackendService(response.data);
}

export async function updateService(
  id: string,
  payload: Partial<ReturnType<typeof toServiceCreatePayload>> & { is_active?: boolean }
): Promise<BillingService> {
  const response = await apiClient.patch<BackendServiceOut>(`/billing/services/${id}`, payload);
  if (!response.data) throw new Error("Failed to update service");
  return fromBackendService(response.data);
}

// ---------------------------------------------------------------------------
// Package master
// ---------------------------------------------------------------------------

export interface ListPackagesParams {
  name?: string;
  is_active?: boolean;
}

export async function listPackages(params: ListPackagesParams = {}): Promise<BillingPackage[]> {
  const response = await apiClient.get<BackendPackageOut[]>("/billing/packages", { params });
  return (response.data ?? []).map(fromBackendPackage);
}

export async function createPackage(payload: ReturnType<typeof toPackageCreatePayload>): Promise<BillingPackage> {
  const response = await apiClient.post<BackendPackageOut>("/billing/packages", payload);
  if (!response.data) throw new Error("Failed to create package");
  return fromBackendPackage(response.data);
}

export async function updatePackage(
  id: string,
  payload: Partial<ReturnType<typeof toPackageCreatePayload>> & { is_active?: boolean }
): Promise<BillingPackage> {
  const response = await apiClient.patch<BackendPackageOut>(`/billing/packages/${id}`, payload);
  if (!response.data) throw new Error("Failed to update package");
  return fromBackendPackage(response.data);
}

// ---------------------------------------------------------------------------
// Invoice
// ---------------------------------------------------------------------------

export interface ListInvoicesParams {
  patient_id?: string;
  status?: string;
}

export async function listInvoices(params: ListInvoicesParams = {}): Promise<Invoice[]> {
  const response = await apiClient.get<BackendInvoiceOut[]>("/billing/invoices", { params });
  return (response.data ?? []).map(fromBackendInvoice);
}

export async function getInvoice(id: string): Promise<Invoice> {
  const response = await apiClient.get<BackendInvoiceOut>(`/billing/invoices/${id}`);
  if (!response.data) throw new Error("Invoice not found");
  return fromBackendInvoice(response.data);
}

export async function getInvoiceBalance(id: string): Promise<InvoiceBalance> {
  const response = await apiClient.get<BackendInvoiceBalanceOut>(`/billing/invoices/${id}/balance`);
  if (!response.data) throw new Error("Invoice not found");
  return fromBackendBalance(response.data);
}

export interface CreateInvoicePayload {
  patient_id: string;
  admission_id?: string | null;
  notes?: string | null;
  items: ReturnType<typeof toInvoiceItemPayload>[];
}

export async function createInvoice(payload: CreateInvoicePayload, idempotencyKey?: string): Promise<Invoice> {
  const response = await apiClient.post<BackendInvoiceOut>("/billing/invoices", payload, idemHeaders(idempotencyKey));
  if (!response.data) throw new Error("Failed to create invoice");
  return fromBackendInvoice(response.data);
}

export async function addInvoiceItems(
  invoiceId: string,
  items: ReturnType<typeof toInvoiceItemPayload>[],
  idempotencyKey?: string
): Promise<Invoice> {
  const response = await apiClient.post<BackendInvoiceOut>(
    `/billing/invoices/${invoiceId}/items`,
    { items },
    idemHeaders(idempotencyKey)
  );
  if (!response.data) throw new Error("Failed to add items to invoice");
  return fromBackendInvoice(response.data);
}

// ---------------------------------------------------------------------------
// Payment
// ---------------------------------------------------------------------------

export async function listPayments(invoiceId: string): Promise<Payment[]> {
  const response = await apiClient.get<BackendPaymentOut[]>(`/billing/invoices/${invoiceId}/payments`);
  return (response.data ?? []).map(fromBackendPayment);
}

export interface RecordPaymentPayload {
  amount: number;
  payment_mode: string;
  reference_number?: string | null;
  notes?: string | null;
}

export async function recordPayment(
  invoiceId: string,
  payload: RecordPaymentPayload,
  idempotencyKey?: string
): Promise<Payment> {
  const response = await apiClient.post<BackendPaymentOut>(
    `/billing/invoices/${invoiceId}/payments`,
    payload,
    idemHeaders(idempotencyKey)
  );
  if (!response.data) throw new Error("Failed to record payment");
  return fromBackendPayment(response.data);
}

// ---------------------------------------------------------------------------
// Deposit
// ---------------------------------------------------------------------------

export interface ListDepositsParams {
  patient_id?: string;
}

export async function listDeposits(params: ListDepositsParams = {}): Promise<Deposit[]> {
  const response = await apiClient.get<BackendDepositOut[]>("/billing/deposits", { params });
  return (response.data ?? []).map(fromBackendDeposit);
}

export interface RecordDepositPayload {
  patient_id: string;
  admission_id?: string | null;
  amount: number;
  payment_mode: string;
  reference_number?: string | null;
  notes?: string | null;
}

export async function recordDeposit(payload: RecordDepositPayload, idempotencyKey?: string): Promise<Deposit> {
  const response = await apiClient.post<BackendDepositOut>("/billing/deposits", payload, idemHeaders(idempotencyKey));
  if (!response.data) throw new Error("Failed to record deposit");
  return fromBackendDeposit(response.data);
}

// ---------------------------------------------------------------------------
// Refund
// ---------------------------------------------------------------------------

export interface CreateRefundPayload {
  payment_id?: string | null;
  deposit_id?: string | null;
  amount: number;
  reason: string;
  refund_mode: string;
  notes?: string | null;
}

export async function createRefund(payload: CreateRefundPayload, idempotencyKey?: string): Promise<Refund> {
  const response = await apiClient.post<BackendRefundOut>("/billing/refunds", payload, idemHeaders(idempotencyKey));
  if (!response.data) throw new Error("Failed to process refund");
  return fromBackendRefund(response.data);
}

// ---------------------------------------------------------------------------
// Receipt
// ---------------------------------------------------------------------------

export async function getReceipt(id: string): Promise<Receipt> {
  const response = await apiClient.get<BackendReceiptOut>(`/billing/receipts/${id}`);
  if (!response.data) throw new Error("Receipt not found");
  return fromBackendReceipt(response.data);
}

export interface ListReceiptsParams {
  patient_id?: string;
  payment_id?: string;
  deposit_id?: string;
  refund_id?: string;
}

export async function listReceipts(params: ListReceiptsParams): Promise<Receipt[]> {
  const response = await apiClient.get<BackendReceiptOut[]>("/billing/receipts", { params });
  return (response.data ?? []).map(fromBackendReceipt);
}
