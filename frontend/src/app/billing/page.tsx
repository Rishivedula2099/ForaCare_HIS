"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Banknote, FileText, Package as PackageIcon, Plus, Printer, Receipt as ReceiptIcon, RotateCcw, Wallet } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { BillingAccessRestricted } from "@/components/billing/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { fromBackendListItem, getPatient, listPatients, toPatient } from "@/lib/patient-api";
import {
  createPackage,
  createRefund,
  createService,
  listDeposits,
  listInvoices,
  listPackages,
  listReceipts,
  listServices,
  newIdempotencyKey,
  recordDeposit,
  toPackageCreatePayload,
  toServiceCreatePayload,
  updatePackage,
  updateService,
} from "@/lib/billing-api";
import { Patient } from "@/types/patient";
import { ApiError } from "@/types/api";
import {
  BillingPackage,
  BillingPackageFormData,
  BillingService,
  BillingServiceFormData,
  Deposit,
  INVOICE_STATUS_BADGE_CLASS,
  InvoiceStatus,
  PAYMENT_MODES,
  PaymentMode,
  SERVICE_CATEGORIES,
} from "@/types/billing";

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

function PatientCell({ patientId }: { patientId: string }) {
  const query = useQuery({
    queryKey: ["patient", patientId],
    queryFn: async () => toPatient(await getPatient(patientId)),
    staleTime: 60_000,
  });
  return (
    <Link href={`/patients/${patientId}`} className="hover:underline">
      {query.data ? (
        <>
          <span className="block text-xs font-semibold text-slate-900">{query.data.fullName}</span>
          <span className="text-[11px] text-slate-500 font-mono">{query.data.uid}</span>
        </>
      ) : (
        <span className="text-xs font-mono text-slate-400">{patientId.slice(0, 8)}…</span>
      )}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Invoices tab
// ---------------------------------------------------------------------------

const INVOICE_STATUSES: { value: string; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "FINALIZED", label: "Finalized" },
  { value: "PARTIALLY_PAID", label: "Partially Paid" },
  { value: "PAID", label: "Paid" },
  { value: "CANCELLED", label: "Cancelled" },
];

function InvoicesTab() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission("billing.invoice.create");
  const [status, setStatus] = React.useState("");

  const invoicesQuery = useQuery({
    queryKey: ["billing-invoices", status],
    queryFn: () => listInvoices({ status: status || undefined }),
  });
  const invoices = invoicesQuery.data ?? [];

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <Select
            options={INVOICE_STATUSES}
            value={status}
            onChange={setStatus}
            placeholder="Filter by status"
            className="max-w-xs"
          />
          {canCreate ? (
            <Button size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/billing/new">
                <Plus className="w-3.5 h-3.5" />
                New Invoice
              </Link>
            </Button>
          ) : (
            <Button size="sm" disabled title="You don't have permission to create invoices" className="gap-1.5 text-xs">
              <Plus className="w-3.5 h-3.5" />
              New Invoice
            </Button>
          )}
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Paid</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-xs text-slate-400 py-8">
                    {invoicesQuery.isLoading ? "Loading invoices..." : "No invoices found."}
                  </TableCell>
                </TableRow>
              ) : (
                invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="text-xs font-mono font-semibold text-slate-900">{invoice.invoiceNumber}</TableCell>
                    <TableCell>
                      <PatientCell patientId={invoice.patientId} />
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">{new Date(invoice.invoiceDate).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={INVOICE_STATUS_BADGE_CLASS[invoice.status as InvoiceStatus]}>
                        {invoice.status.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-xs font-semibold text-slate-900">{currency(invoice.totalAmount)}</TableCell>
                    <TableCell className="text-right text-xs text-emerald-700">{currency(invoice.amountPaid)}</TableCell>
                    <TableCell className="text-right text-xs font-semibold text-rose-700">{currency(invoice.amountDue)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-xs h-7" asChild>
                        <Link href={`/billing/invoices/${invoice.id}`}>View</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Deposits tab
// ---------------------------------------------------------------------------

function RecordDepositDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] = React.useState<Patient | null>(null);
  const [amount, setAmount] = React.useState("");
  const [paymentMode, setPaymentMode] = React.useState<PaymentMode>("CASH");
  const [referenceNumber, setReferenceNumber] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const patientSearchQuery = useQuery({
    queryKey: ["billing-deposit-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  const mutation = useMutation({
    mutationFn: () =>
      recordDeposit(
        {
          patient_id: selectedPatient!.id,
          amount: Number(amount),
          payment_mode: paymentMode,
          reference_number: referenceNumber.trim() || null,
          notes: notes.trim() || null,
        },
        idempotencyKeyRef.current
      ),
    onSuccess: () => {
      toast({ title: "Deposit recorded", description: `${currency(Number(amount))} — ${selectedPatient?.fullName}`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-deposits"] });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to record this deposit.");
    },
  });

  const reset = () => {
    setPatientQuery("");
    setSelectedPatient(null);
    setAmount("");
    setPaymentMode("CASH");
    setReferenceNumber("");
    setNotes("");
    setFormError(null);
    idempotencyKeyRef.current = newIdempotencyKey();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!selectedPatient) {
      setFormError("Please select a patient.");
      return;
    }
    const numericAmount = Number(amount);
    if (!amount || Number.isNaN(numericAmount) || numericAmount <= 0) {
      setFormError("Enter a valid amount greater than zero.");
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Deposit</DialogTitle>
          <DialogDescription>Collect an advance payment from a patient, independent of any invoice.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Patient</label>
            {selectedPatient ? (
              <div className="flex items-center justify-between gap-3 rounded-md border border-teal-200 bg-teal-50/60 px-3 py-2">
                <div>
                  <div className="text-xs font-bold text-slate-900">{selectedPatient.fullName}</div>
                  <div className="text-[11px] text-slate-500 font-mono">{selectedPatient.uid} • {selectedPatient.mrn}</div>
                </div>
                <Button type="button" variant="ghost" size="sm" className="text-xs h-7" onClick={() => setSelectedPatient(null)}>
                  Change
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Input
                  value={patientQuery}
                  onChange={(e) => setPatientQuery(e.target.value)}
                  placeholder="Search by name, UID, or MRN..."
                  className="text-xs"
                />
                {patientQuery.trim().length >= 2 && (
                  <div className="border border-slate-200 rounded-md divide-y divide-slate-100 max-h-40 overflow-y-auto">
                    {(patientSearchQuery.data ?? []).length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-400">
                        {patientSearchQuery.isFetching ? "Searching..." : "No matching patients."}
                      </div>
                    ) : (
                      (patientSearchQuery.data ?? []).map((patient) => (
                        <button
                          key={patient.id}
                          type="button"
                          onClick={() => {
                            setSelectedPatient(patient);
                            setPatientQuery("");
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-slate-50"
                        >
                          <div className="text-xs font-semibold text-slate-900">{patient.fullName}</div>
                          <div className="text-[11px] text-slate-500 font-mono">{patient.uid} • {patient.mrn}</div>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Amount</label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
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
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={mutation.isPending}>
              {mutation.isPending ? "Recording..." : "Record Deposit"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DepositReceiptLink({ depositId }: { depositId: string }) {
  const query = useQuery({
    queryKey: ["billing-receipt-for-deposit", depositId],
    queryFn: () => listReceipts({ deposit_id: depositId }),
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

function RefundDepositDialog({
  open,
  onOpenChange,
  deposit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deposit: Deposit | null;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // The parent remounts this dialog (via a `key` on the target deposit's
  // id) each time a new deposit is selected for refund, so these
  // initializers run fresh instead of needing an effect to reset them.
  const [amount, setAmount] = React.useState(String((deposit?.amount ?? 0).toFixed(2)));
  const [reason, setReason] = React.useState("");
  const [refundMode, setRefundMode] = React.useState<PaymentMode>(deposit?.paymentMode ?? "CASH");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const mutation = useMutation({
    mutationFn: () =>
      createRefund(
        {
          deposit_id: deposit!.id,
          amount: Number(amount),
          reason: reason.trim(),
          refund_mode: refundMode,
          notes: notes.trim() || null,
        },
        idempotencyKeyRef.current
      ),
    onSuccess: (refund) => {
      toast({ title: "Refund processed", description: currency(refund.amount), variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-deposits"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "This refund could not be processed."),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!deposit) return;
    const numericAmount = Number(amount);
    if (!amount || Number.isNaN(numericAmount) || numericAmount <= 0) {
      setFormError("Enter a valid refund amount greater than zero.");
      return;
    }
    if (numericAmount > deposit.amount) {
      setFormError(`Refund amount exceeds the original deposit of ${currency(deposit.amount)}.`);
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
          <DialogTitle>Refund Deposit</DialogTitle>
          <DialogDescription>
            {deposit ? `Refund against the ${currency(deposit.amount)} deposit.` : ""}
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
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Patient discharged early" className="text-xs" />
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

function DepositsTab() {
  const { hasPermission } = useAuth();
  const canCollect = hasPermission("billing.payment.create");
  const canRefund = hasPermission("billing.refund.create");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [refundTarget, setRefundTarget] = React.useState<Deposit | null>(null);

  const depositsQuery = useQuery({ queryKey: ["billing-deposits"], queryFn: () => listDeposits() });
  const deposits = depositsQuery.data ?? [];

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-end">
          {canCollect ? (
            <Button size="sm" className="gap-1.5 text-xs" onClick={() => setDialogOpen(true)}>
              <Plus className="w-3.5 h-3.5" />
              Record Deposit
            </Button>
          ) : (
            <Button size="sm" disabled title="You don't have permission to collect deposits" className="gap-1.5 text-xs">
              <Plus className="w-3.5 h-3.5" />
              Record Deposit
            </Button>
          )}
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Patient</TableHead>
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
              {deposits.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-xs text-slate-400 py-8">
                    {depositsQuery.isLoading ? "Loading deposits..." : "No deposits recorded."}
                  </TableCell>
                </TableRow>
              ) : (
                deposits.map((deposit) => (
                  <TableRow key={deposit.id}>
                    <TableCell>
                      <PatientCell patientId={deposit.patientId} />
                    </TableCell>
                    <TableCell className="text-xs font-semibold text-slate-900">{currency(deposit.amount)}</TableCell>
                    <TableCell className="text-xs text-slate-600">
                      {PAYMENT_MODES.find((m) => m.value === deposit.paymentMode)?.label ?? deposit.paymentMode}
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-500">{deposit.referenceNumber || "—"}</TableCell>
                    <TableCell>
                      <Badge variant={deposit.status === "ACTIVE" ? "completed" : "alert"}>{deposit.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">{new Date(deposit.recordedAt).toLocaleString()}</TableCell>
                    <TableCell className="text-right">
                      <DepositReceiptLink depositId={deposit.id} />
                    </TableCell>
                    <TableCell className="text-right">
                      {canRefund && deposit.status === "ACTIVE" && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setRefundTarget(deposit)}>
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

      <RecordDepositDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      <RefundDepositDialog
        key={refundTarget?.id ?? "none"}
        open={!!refundTarget}
        onOpenChange={(open) => !open && setRefundTarget(null)}
        deposit={refundTarget}
      />
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Catalog tab (Service / Package master - P5-F01)
// ---------------------------------------------------------------------------

const EMPTY_SERVICE_FORM: BillingServiceFormData = {
  name: "",
  code: "",
  category: "CONSULTATION",
  price: "",
  departmentId: "",
  description: "",
};

function ServiceDialog({
  open,
  onOpenChange,
  editingService,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingService: BillingService | null;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  // The parent remounts this dialog (via a `key` on open-state + the
  // service being edited) each time it's opened, so this initializer runs
  // fresh instead of needing an effect to reset it.
  const [formData, setFormData] = React.useState<BillingServiceFormData>(
    editingService
      ? {
          name: editingService.name,
          code: editingService.code,
          category: editingService.category,
          price: String(editingService.price),
          departmentId: editingService.departmentId ?? "",
          description: editingService.description ?? "",
        }
      : EMPTY_SERVICE_FORM
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: BillingServiceFormData) => createService(toServiceCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Service created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-services"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to create service."),
  });

  const updateMutation = useMutation({
    mutationFn: (data: BillingServiceFormData) =>
      updateService(editingService!.id, {
        name: data.name.trim(),
        category: data.category,
        price: Number(data.price),
        department_id: data.departmentId || null,
        description: data.description.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Service updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-services"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update service."),
  });

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const price = Number(formData.price);
    if (!formData.name.trim() || !formData.code.trim()) {
      setFormError("Name and code are required.");
      return;
    }
    if (!formData.price || Number.isNaN(price) || price <= 0) {
      setFormError("Enter a valid price greater than zero.");
      return;
    }
    if (editingService) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingService ? "Edit Service" : "Add Service"}</DialogTitle>
          <DialogDescription>
            {editingService ? "Update this service's price and details." : "Add a billable service to the catalog."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Service Name</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. General Consultation"
              className="text-xs"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Code</label>
              <Input
                value={formData.code}
                onChange={(e) => setFormData((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. CONS-GEN"
                disabled={!!editingService}
                className="text-xs font-mono uppercase"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Category</label>
              <Select
                options={SERVICE_CATEGORIES.map((c) => ({ value: c.value, label: c.label }))}
                value={formData.category}
                onChange={(value) => setFormData((f) => ({ ...f, category: value as BillingServiceFormData["category"] }))}
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Price</label>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={formData.price}
              onChange={(e) => setFormData((f) => ({ ...f, price: e.target.value }))}
              placeholder="0.00"
              className="text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Description (optional)</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
              rows={2}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isSaving}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSaving}>
              {isSaving ? "Saving..." : editingService ? "Save Changes" : "Add Service"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ServicesSection() {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canManage = hasPermission("billing.manage_services");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingService, setEditingService] = React.useState<BillingService | null>(null);

  const servicesQuery = useQuery({ queryKey: ["billing-services"], queryFn: () => listServices() });
  const services = servicesQuery.data ?? [];

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updateService(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["billing-services"] }),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <Wallet className="w-4 h-4 text-slate-500" />
          Services
        </h3>
        {canManage && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs"
            onClick={() => {
              setEditingService(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="w-3.5 h-3.5" />
            Add Service
          </Button>
        )}
      </div>
      <div className="overflow-x-auto border border-slate-200 rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {services.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-xs text-slate-400 py-6">
                  {servicesQuery.isLoading ? "Loading services..." : "No services yet."}
                </TableCell>
              </TableRow>
            ) : (
              services.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="text-xs font-semibold text-slate-900">{service.name}</TableCell>
                  <TableCell className="text-xs font-mono text-slate-600">{service.code}</TableCell>
                  <TableCell className="text-xs text-slate-500">
                    {SERVICE_CATEGORIES.find((c) => c.value === service.category)?.label ?? service.category}
                  </TableCell>
                  <TableCell className="text-right text-xs font-semibold text-slate-900">{currency(service.price)}</TableCell>
                  <TableCell>
                    <button
                      type="button"
                      disabled={!canManage || toggleActiveMutation.isPending}
                      onClick={() => toggleActiveMutation.mutate({ id: service.id, isActive: !service.isActive })}
                    >
                      <Badge
                        variant="outline"
                        className={
                          service.isActive
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : "bg-slate-100 text-slate-500 border-slate-300"
                        }
                      >
                        {service.isActive ? "Active" : "Inactive"}
                      </Badge>
                    </button>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={!canManage}
                      className="h-7 text-xs"
                      onClick={() => {
                        setEditingService(service);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <ServiceDialog
        key={`${dialogOpen}-${editingService?.id ?? "new"}`}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingService={editingService}
      />
    </div>
  );
}

const EMPTY_PACKAGE_FORM: BillingPackageFormData = { name: "", code: "", price: "", description: "" };

function PackageDialog({
  open,
  onOpenChange,
  editingPackage,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingPackage: BillingPackage | null;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  // The parent remounts this dialog (via a `key` on open-state + the
  // package being edited) each time it's opened, so this initializer runs
  // fresh instead of needing an effect to reset it.
  const [formData, setFormData] = React.useState<BillingPackageFormData>(
    editingPackage
      ? {
          name: editingPackage.name,
          code: editingPackage.code,
          price: String(editingPackage.price),
          description: editingPackage.description ?? "",
        }
      : EMPTY_PACKAGE_FORM
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: BillingPackageFormData) => createPackage(toPackageCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Package created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-packages"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to create package."),
  });

  const updateMutation = useMutation({
    mutationFn: (data: BillingPackageFormData) =>
      updatePackage(editingPackage!.id, {
        name: data.name.trim(),
        price: Number(data.price),
        description: data.description.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Package updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["billing-packages"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update package."),
  });

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const price = Number(formData.price);
    if (!formData.name.trim() || !formData.code.trim()) {
      setFormError("Name and code are required.");
      return;
    }
    if (!formData.price || Number.isNaN(price) || price <= 0) {
      setFormError("Enter a valid price greater than zero.");
      return;
    }
    if (editingPackage) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingPackage ? "Edit Package" : "Add Package"}</DialogTitle>
          <DialogDescription>
            {editingPackage ? "Update this package's price and details." : "Add a fixed-price bundle to the catalog."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Package Name</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Full Body Health Checkup"
              className="text-xs"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Code</label>
              <Input
                value={formData.code}
                onChange={(e) => setFormData((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. PKG-CHECKUP"
                disabled={!!editingPackage}
                className="text-xs font-mono uppercase"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Price</label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={formData.price}
                onChange={(e) => setFormData((f) => ({ ...f, price: e.target.value }))}
                placeholder="0.00"
                className="text-xs"
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Description (optional)</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
              rows={2}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isSaving}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSaving}>
              {isSaving ? "Saving..." : editingPackage ? "Save Changes" : "Add Package"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PackagesSection() {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canManage = hasPermission("billing.manage_services");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingPackage, setEditingPackage] = React.useState<BillingPackage | null>(null);

  const packagesQuery = useQuery({ queryKey: ["billing-packages"], queryFn: () => listPackages() });
  const packages = packagesQuery.data ?? [];

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updatePackage(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["billing-packages"] }),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <PackageIcon className="w-4 h-4 text-slate-500" />
          Packages
        </h3>
        {canManage && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs"
            onClick={() => {
              setEditingPackage(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="w-3.5 h-3.5" />
            Add Package
          </Button>
        )}
      </div>
      <div className="overflow-x-auto border border-slate-200 rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Code</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {packages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-xs text-slate-400 py-6">
                  {packagesQuery.isLoading ? "Loading packages..." : "No packages yet."}
                </TableCell>
              </TableRow>
            ) : (
              packages.map((pkg) => (
                <TableRow key={pkg.id}>
                  <TableCell className="text-xs font-semibold text-slate-900">{pkg.name}</TableCell>
                  <TableCell className="text-xs font-mono text-slate-600">{pkg.code}</TableCell>
                  <TableCell className="text-right text-xs font-semibold text-slate-900">{currency(pkg.price)}</TableCell>
                  <TableCell>
                    <button
                      type="button"
                      disabled={!canManage || toggleActiveMutation.isPending}
                      onClick={() => toggleActiveMutation.mutate({ id: pkg.id, isActive: !pkg.isActive })}
                    >
                      <Badge
                        variant="outline"
                        className={
                          pkg.isActive
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : "bg-slate-100 text-slate-500 border-slate-300"
                        }
                      >
                        {pkg.isActive ? "Active" : "Inactive"}
                      </Badge>
                    </button>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={!canManage}
                      className="h-7 text-xs"
                      onClick={() => {
                        setEditingPackage(pkg);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <PackageDialog
        key={`${dialogOpen}-${editingPackage?.id ?? "new"}`}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingPackage={editingPackage}
      />
    </div>
  );
}

function CatalogTab() {
  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-6">
        <ServicesSection />
        <div className="border-t border-slate-100" />
        <PackagesSection />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function BillingPageContent() {
  const { hasPermission } = useAuth();
  const canView = hasPermission("billing.view");

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Billing & Cashier" description="Invoices, payments, deposits, and the service/package catalog." />
        <BillingAccessRestricted />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Billing & Cashier" description="Invoices, payments, deposits, and the service/package catalog." />

      <Tabs defaultValue="invoices">
        <TabsList>
          <TabsTrigger value="invoices" className="gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            Invoices
          </TabsTrigger>
          <TabsTrigger value="deposits" className="gap-1.5">
            <Banknote className="w-3.5 h-3.5" />
            Deposits
          </TabsTrigger>
          <TabsTrigger value="catalog" className="gap-1.5">
            <ReceiptIcon className="w-3.5 h-3.5" />
            Services & Packages
          </TabsTrigger>
        </TabsList>

        <TabsContent value="invoices">
          <InvoicesTab />
        </TabsContent>
        <TabsContent value="deposits">
          <DepositsTab />
        </TabsContent>
        <TabsContent value="catalog">
          <CatalogTab />
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}

export default function BillingPage() {
  return (
    <AppShell>
      <BillingPageContent />
    </AppShell>
  );
}
