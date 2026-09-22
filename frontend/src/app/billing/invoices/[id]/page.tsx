"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Banknote,
  CheckCircle2,
  FileText,
  Plus,
  Printer,
  RotateCcw,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { BillingAccessRestricted } from "@/components/billing/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  EstimatedTotals,
  InvoiceItemBuilder,
  newDraftItem,
  validateDraftItems,
} from "@/components/billing/invoice-item-builder";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { getPatient, toPatient } from "@/lib/patient-api";
import {
  addInvoiceItems,
  createRefund,
  getInvoice,
  listPackages,
  listPayments,
  listReceipts,
  listServices,
  newIdempotencyKey,
  recordPayment,
  toInvoiceItemPayload,
} from "@/lib/billing-api";
import { ApiError } from "@/types/api";
import {
  INVOICE_STATUS_BADGE_CLASS,
  InvoiceItemDraft,
  InvoiceStatus,
  PAYMENT_MODES,
  PaymentMode,
  Payment as BillingPayment,
} from "@/types/billing";

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

function modeLabel(mode: string): string {
  return PAYMENT_MODES.find((m) => m.value === mode)?.label ?? mode;
}

// ---------------------------------------------------------------------------
// Receipt preview (shown right after a payment/deposit/refund succeeds, and
// as a "Receipt" link on each payment row once issued)
// ---------------------------------------------------------------------------

function ReceiptLink({ paymentId, refundId }: { paymentId?: string; refundId?: string }) {
  const query = useQuery({
    queryKey: ["billing-receipt-for", paymentId, refundId],
    queryFn: () => listReceipts(paymentId ? { payment_id: paymentId } : { refund_id: refundId }),
    enabled: !!(paymentId || refundId),
  });
  const receipt = (query.data ?? [])[0];
  if (!receipt) return <span className="text-[11px] text-slate-300">—</span>;
  return (
    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" asChild>
      <Link href={`/billing/invoices/receipts/${receipt.id}`} target="_blank">
        <Printer className="w-3 h-3" />
        Receipt
      </Link>
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Collect Payment
// ---------------------------------------------------------------------------

function CollectPaymentCard({
  invoiceId,
  amountDue,
  onSettled,
}: {
  invoiceId: string;
  amountDue: number;
  onSettled: (paymentId: string) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // `amount` defaults to the current balance but is user-editable; the
  // parent remounts this card (via a `key` on `amountDue`) whenever the
  // balance changes so this default picks up the new value, rather than
  // syncing it with an effect that would also clobber anything the cashier
  // is mid-typing.
  const [amount, setAmount] = React.useState(String(amountDue.toFixed(2)));
  const [paymentMode, setPaymentMode] = React.useState<PaymentMode>("CASH");
  const [referenceNumber, setReferenceNumber] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const mutation = useMutation({
    mutationFn: () =>
      recordPayment(
        invoiceId,
        {
          amount: Number(amount),
          payment_mode: paymentMode,
          reference_number: referenceNumber.trim() || null,
          notes: notes.trim() || null,
        },
        idempotencyKeyRef.current
      ),
    onSuccess: (payment) => {
      toast({ title: "Payment collected", description: currency(payment.amount), variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-invoice", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["billing-invoice-payments", invoiceId] });
      setReferenceNumber("");
      setNotes("");
      idempotencyKeyRef.current = newIdempotencyKey();
      onSettled(payment.id);
    },
    onError: (error: ApiError) => {
      // Server error messages are already specific ("Payment amount exceeds
      // the outstanding balance on this invoice.", "Payment could not be
      // processed.") - surfaced as-is (P5-F05: invalid amount / insufficient
      // balance / payment failure).
      setFormError(error?.message || "Payment could not be processed. Please try again.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const numericAmount = Number(amount);
    if (!amount || Number.isNaN(numericAmount) || numericAmount <= 0) {
      setFormError("Enter a valid amount greater than zero.");
      return;
    }
    if (numericAmount > amountDue) {
      setFormError(`Amount exceeds the outstanding balance of ${currency(amountDue)}.`);
      return;
    }
    mutation.mutate();
  };

  if (amountDue <= 0) {
    return (
      <Card className="shadow-xs border-emerald-200 bg-emerald-50/40">
        <CardContent className="p-4 flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4" />
          This invoice is fully paid. No balance is outstanding.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <Banknote className="w-4 h-4 text-slate-500" />
          Collect Payment
        </h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Amount (balance: {currency(amountDue)})
              </label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Payment Mode</label>
              <Select
                options={PAYMENT_MODES.map((m) => ({ value: m.value, label: m.label }))}
                value={paymentMode}
                onChange={(value) => setPaymentMode(value as PaymentMode)}
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Reference Number (optional)</label>
            <Input
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder="UPI transaction ID, cheque number..."
              className="text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Notes (optional)</label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} className="text-xs" />
          </div>

          {formError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" size="sm" className="text-xs" disabled={mutation.isPending}>
              {mutation.isPending ? "Processing..." : "Collect Payment"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Refund dialog
// ---------------------------------------------------------------------------

function RefundDialog({
  open,
  onOpenChange,
  payment,
  invoiceId,
  onSettled,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  payment: BillingPayment | null;
  invoiceId: string;
  onSettled: (refundId: string) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // The parent remounts this dialog (via a `key` on the target payment's
  // id) each time a new payment is selected for refund, so these
  // initializers run fresh instead of needing an effect to reset them.
  const [amount, setAmount] = React.useState(String((payment?.amount ?? 0).toFixed(2)));
  const [reason, setReason] = React.useState("");
  const [refundMode, setRefundMode] = React.useState<PaymentMode>(payment?.paymentMode ?? "CASH");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const mutation = useMutation({
    mutationFn: () =>
      createRefund(
        {
          payment_id: payment!.id,
          amount: Number(amount),
          reason: reason.trim(),
          refund_mode: refundMode,
          notes: notes.trim() || null,
        },
        idempotencyKeyRef.current
      ),
    onSuccess: (refund) => {
      toast({ title: "Refund processed", description: currency(refund.amount), variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-invoice", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["billing-invoice-payments", invoiceId] });
      onOpenChange(false);
      onSettled(refund.id);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "This refund could not be processed.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!payment) return;
    const numericAmount = Number(amount);
    if (!amount || Number.isNaN(numericAmount) || numericAmount <= 0) {
      setFormError("Enter a valid refund amount greater than zero.");
      return;
    }
    if (numericAmount > payment.amount) {
      setFormError(`Refund amount exceeds the original payment of ${currency(payment.amount)}.`);
      return;
    }
    if (!reason.trim()) {
      setFormError("A reason is required for every refund.");
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Refund Payment</DialogTitle>
          <DialogDescription>
            {payment ? `Refund against the ${currency(payment.amount)} ${modeLabel(payment.paymentMode)} payment.` : ""}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Refund Amount</label>
              <Input type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className="text-xs" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Refund Mode</label>
              <Select
                options={PAYMENT_MODES.map((m) => ({ value: m.value, label: m.label }))}
                value={refundMode}
                onChange={(value) => setRefundMode(value as PaymentMode)}
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Reason</label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Overcharge correction" className="text-xs" />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Notes (optional)</label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} className="text-xs" />
          </div>

          {formError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" size="sm" disabled={mutation.isPending} className="gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              {mutation.isPending ? "Processing..." : "Process Refund"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Add Items dialog
// ---------------------------------------------------------------------------

function AddItemsDialog({
  open,
  onOpenChange,
  invoiceId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoiceId: string;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  // The parent remounts this dialog (via a `key` toggling on `open`) each
  // time it's opened, so these initializers give a fresh form without an
  // effect to reset them.
  const [items, setItems] = React.useState<InvoiceItemDraft[]>([newDraftItem()]);
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const servicesQuery = useQuery({ queryKey: ["billing-services"], queryFn: () => listServices({ is_active: true }), enabled: open });
  const packagesQuery = useQuery({ queryKey: ["billing-packages"], queryFn: () => listPackages({ is_active: true }), enabled: open });

  const mutation = useMutation({
    mutationFn: () => addInvoiceItems(invoiceId, items.map(toInvoiceItemPayload), idempotencyKeyRef.current),
    onSuccess: () => {
      toast({ title: "Items added to invoice", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-invoice", invoiceId] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to add these items."),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const itemsError = validateDraftItems(items);
    if (itemsError) {
      setFormError(itemsError);
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Add Items to Invoice</DialogTitle>
          <DialogDescription>These items are added to the existing invoice and its balance updated.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <InvoiceItemBuilder
            items={items}
            onChange={setItems}
            services={servicesQuery.data ?? []}
            packages={packagesQuery.data ?? []}
          />
          <EstimatedTotals items={items} />

          {formError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={mutation.isPending} className="gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              {mutation.isPending ? "Adding..." : "Add Items"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function InvoiceDetailContent({ invoiceId }: { invoiceId: string }) {
  const { hasPermission } = useAuth();
  const canView = hasPermission("billing.view");
  const canCollectPayment = hasPermission("billing.payment.create");
  const canRefund = hasPermission("billing.refund.create");
  const canAddItems = hasPermission("billing.invoice.create");

  const [addItemsOpen, setAddItemsOpen] = React.useState(false);
  const [refundTarget, setRefundTarget] = React.useState<BillingPayment | null>(null);
  const [previewReceiptId, setPreviewReceiptId] = React.useState<string | null>(null);

  // `enabled: canView` on every billing.view-gated query below matters, not
  // just for avoiding wasted requests: without it, a role lacking
  // `billing.view` would still fire this query on mount (React hooks run
  // before the early `!canView` return further down), hit a real 403, and
  // trip the API client's generic redirect to /forbidden before this
  // page's own inline guard ever gets a chance to render.
  const invoiceQuery = useQuery({
    queryKey: ["billing-invoice", invoiceId],
    queryFn: () => getInvoice(invoiceId),
    enabled: canView,
  });
  const invoice = invoiceQuery.data;

  const patientQuery = useQuery({
    queryKey: ["patient", invoice?.patientId],
    queryFn: async () => toPatient(await getPatient(invoice!.patientId)),
    enabled: !!invoice,
  });
  const patient = patientQuery.data;

  const paymentsQuery = useQuery({
    queryKey: ["billing-invoice-payments", invoiceId],
    queryFn: () => listPayments(invoiceId),
    enabled: canView,
  });
  const payments = paymentsQuery.data ?? [];

  if (!canView) {
    return <BillingAccessRestricted />;
  }
  if (invoiceQuery.isLoading) {
    return <p className="text-xs text-slate-400 py-8 text-center">Loading invoice...</p>;
  }
  if (invoiceQuery.isError || !invoice) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
        Invoice not found, or you don&apos;t have access to it.
      </div>
    );
  }

  const canMutateInvoice = invoice.status !== "CANCELLED";

  return (
    <PageContainer>
      <PageHeader
        title={invoice.invoiceNumber}
        description={patient ? `${patient.fullName} • ${patient.uid}` : "Loading patient..."}
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/billing">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Billing
            </Link>
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        <Badge variant="outline" className={INVOICE_STATUS_BADGE_CLASS[invoice.status as InvoiceStatus]}>
          {invoice.status.replace("_", " ")}
        </Badge>
        <span className="text-xs text-slate-400">{new Date(invoice.invoiceDate).toLocaleString()}</span>
      </div>

      {/* Totals - server-calculated, read-only (P5-F05) */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Totals</h3>
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-4 text-xs">
            <div>
              <span className="text-[10px] text-slate-500 block">Subtotal</span>
              <span className="font-semibold text-slate-900">{currency(invoice.subtotal)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Discount</span>
              <span className="font-semibold text-slate-900">-{currency(invoice.discountAmount)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Tax</span>
              <span className="font-semibold text-slate-900">+{currency(invoice.taxAmount)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Total</span>
              <span className="font-bold text-slate-900">{currency(invoice.totalAmount)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Paid</span>
              <span className="font-bold text-emerald-700">{currency(invoice.amountPaid)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Balance</span>
              <span className="font-bold text-rose-700">{currency(invoice.amountDue)}</span>
            </div>
          </div>
          {invoice.notes && (
            <div className="pt-2 border-t border-slate-100">
              <span className="text-[10px] text-slate-500 block">Notes</span>
              <span className="text-xs text-slate-700">{invoice.notes}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Line items */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-slate-500" />
              Line Items
            </h3>
            {canAddItems && canMutateInvoice && invoice.status !== "PAID" && (
              <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => setAddItemsOpen(true)}>
                <Plus className="w-3.5 h-3.5" />
                Add Items
              </Button>
            )}
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Description</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Unit Price</TableHead>
                  <TableHead className="text-right">Discount</TableHead>
                  <TableHead className="text-right">Tax</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoice.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-xs font-semibold text-slate-900">{item.description}</TableCell>
                    <TableCell className="text-xs text-slate-500">{item.itemType}</TableCell>
                    <TableCell className="text-right text-xs text-slate-600">{item.quantity}</TableCell>
                    <TableCell className="text-right text-xs text-slate-600">{currency(item.unitPrice)}</TableCell>
                    <TableCell className="text-right text-xs text-slate-600">{currency(item.discountAmount)}</TableCell>
                    <TableCell className="text-right text-xs text-slate-600">{currency(item.taxAmount)}</TableCell>
                    <TableCell className="text-right text-xs font-semibold text-slate-900">{currency(item.totalAmount)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Payment history */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <Banknote className="w-4 h-4 text-slate-500" />
            Payments
          </h3>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Amount</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Recorded</TableHead>
                  <TableHead className="text-right">Receipt</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-xs text-slate-400 py-6">
                      {paymentsQuery.isLoading ? "Loading payments..." : "No payments recorded yet."}
                    </TableCell>
                  </TableRow>
                ) : (
                  payments.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell className="text-xs font-semibold text-slate-900">{currency(payment.amount)}</TableCell>
                      <TableCell className="text-xs text-slate-600">{modeLabel(payment.paymentMode)}</TableCell>
                      <TableCell className="text-xs font-mono text-slate-500">{payment.referenceNumber || "—"}</TableCell>
                      <TableCell>
                        <Badge variant={payment.status === "COMPLETED" ? "completed" : "alert"}>{payment.status}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">{new Date(payment.recordedAt).toLocaleString()}</TableCell>
                      <TableCell className="text-right">
                        <ReceiptLink paymentId={payment.id} />
                      </TableCell>
                      <TableCell className="text-right">
                        {canRefund && payment.status === "COMPLETED" && (
                          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setRefundTarget(payment)}>
                            Refund
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Cashier: collect payment */}
      {canCollectPayment && canMutateInvoice && (
        <CollectPaymentCard
          key={invoice.amountDue}
          invoiceId={invoiceId}
          amountDue={invoice.amountDue}
          onSettled={setPreviewReceiptId}
        />
      )}

      <AddItemsDialog key={String(addItemsOpen)} open={addItemsOpen} onOpenChange={setAddItemsOpen} invoiceId={invoiceId} />
      <RefundDialog
        key={refundTarget?.id ?? "none"}
        open={!!refundTarget}
        onOpenChange={(open) => !open && setRefundTarget(null)}
        payment={refundTarget}
        invoiceId={invoiceId}
        onSettled={setPreviewReceiptId}
      />
      {previewReceiptId && (
        <ReceiptSettledBanner receiptId={previewReceiptId} onDismiss={() => setPreviewReceiptId(null)} />
      )}
    </PageContainer>
  );
}

function ReceiptSettledBanner({ receiptId, onDismiss }: { receiptId: string; onDismiss: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3">
      <div className="flex items-center gap-2 text-xs text-emerald-800">
        <CheckCircle2 className="w-4 h-4 shrink-0" />
        A receipt has been issued for this transaction.
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
          <Link href={`/billing/invoices/receipts/${receiptId}`} target="_blank">
            <Printer className="w-3.5 h-3.5" />
            Print Receipt
          </Link>
        </Button>
        <Button size="sm" variant="ghost" className="text-xs" onClick={onDismiss}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <AppShell>
      <InvoiceDetailContent invoiceId={params.id} />
    </AppShell>
  );
}
