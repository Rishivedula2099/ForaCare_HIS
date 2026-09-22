"use client";

import React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, ShieldAlert } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { BillingAccessRestricted } from "@/components/billing/access-restricted";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  EstimatedTotals,
  InvoiceItemBuilder,
  newDraftItem,
  validateDraftItems,
} from "@/components/billing/invoice-item-builder";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { fromBackendListItem, getPatient, listPatients, toPatient } from "@/lib/patient-api";
import {
  createInvoice,
  listPackages,
  listServices,
  newIdempotencyKey,
  toInvoiceItemPayload,
} from "@/lib/billing-api";
import { Patient } from "@/types/patient";
import { ApiError } from "@/types/api";
import { InvoiceItemDraft } from "@/types/billing";

function NewInvoicePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillPatientId = searchParams.get("patientId");
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const canView = hasPermission("billing.view");
  const canCreate = hasPermission("billing.invoice.create");

  const [patientQuery, setPatientQuery] = React.useState("");
  const [manualPatient, setManualPatient] = React.useState<Patient | null>(null);
  // True once the cashier has explicitly moved past the `?patientId=`
  // prefill (via "Change"), so it's never resurrected after that.
  const [prefillDismissed, setPrefillDismissed] = React.useState(false);

  const prefillPatientQuery = useQuery({
    queryKey: ["patient", prefillPatientId],
    queryFn: async () => toPatient(await getPatient(prefillPatientId!)),
    enabled: !!prefillPatientId && !prefillDismissed && !manualPatient,
  });

  // Derived, not copied into its own state via an effect: the prefilled
  // patient (from a "New Invoice" link on a patient's profile) applies
  // until the cashier picks a different one or dismisses it.
  const selectedPatient = manualPatient ?? (prefillDismissed ? null : prefillPatientQuery.data ?? null);
  const [admissionId, setAdmissionId] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [items, setItems] = React.useState<InvoiceItemDraft[]>([newDraftItem()]);
  const [formError, setFormError] = React.useState<string | null>(null);
  const idempotencyKeyRef = React.useRef(newIdempotencyKey());

  const patientSearchQuery = useQuery({
    queryKey: ["billing-new-invoice-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  // `enabled: canView` matters beyond avoiding a wasted request: without
  // it, these would still fire on mount for a role lacking `billing.view`
  // (hooks run before the `!canView` early return below), hit a real 403,
  // and trip the API client's generic redirect to /forbidden before this
  // page's own inline guard ever renders.
  const servicesQuery = useQuery({
    queryKey: ["billing-services"],
    queryFn: () => listServices({ is_active: true }),
    enabled: canView,
  });
  const packagesQuery = useQuery({
    queryKey: ["billing-packages"],
    queryFn: () => listPackages({ is_active: true }),
    enabled: canView,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createInvoice(
        {
          patient_id: selectedPatient!.id,
          admission_id: admissionId.trim() || null,
          notes: notes.trim() || null,
          items: items.map(toInvoiceItemPayload),
        },
        idempotencyKeyRef.current
      ),
    onSuccess: (invoice) => {
      toast({ title: "Invoice created", description: invoice.invoiceNumber, variant: "success" });
      router.push(`/billing/invoices/${invoice.id}`);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to create this invoice. Please check the details and try again.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!selectedPatient) {
      setFormError("Please select a patient.");
      return;
    }
    const itemsError = validateDraftItems(items);
    if (itemsError) {
      setFormError(itemsError);
      return;
    }
    createMutation.mutate();
  };

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="New Invoice" description="Create an invoice for services or packages rendered to a patient." />
        <BillingAccessRestricted />
      </PageContainer>
    );
  }

  if (!canCreate) {
    return (
      <PageContainer>
        <PageHeader title="New Invoice" description="Create an invoice for services or packages rendered to a patient." />
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">You don&apos;t have permission to create invoices.</p>
            <p className="text-amber-700 mt-0.5">Contact a Hospital Admin if you believe you should have access.</p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
          <Link href="/billing">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Billing
          </Link>
        </Button>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="New Invoice"
        description="Create an invoice for services or packages rendered to a patient."
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/billing">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Billing
            </Link>
          </Button>
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-5">
          {/* Patient */}
          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-slate-700 block">1. Select Patient</label>
            {selectedPatient ? (
              <div className="flex items-center justify-between gap-3 rounded-md border border-teal-200 bg-teal-50/60 px-3 py-2.5">
                <div>
                  <div className="text-xs font-bold text-slate-900">{selectedPatient.fullName}</div>
                  <div className="text-[11px] text-slate-500 font-mono">{selectedPatient.uid} • {selectedPatient.mrn}</div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => {
                    setManualPatient(null);
                    setPrefillDismissed(true);
                  }}
                >
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
                  <div className="border border-slate-200 rounded-md divide-y divide-slate-100 max-h-56 overflow-y-auto">
                    {(patientSearchQuery.data ?? []).length === 0 ? (
                      <div className="px-3 py-3 text-xs text-slate-400">
                        {patientSearchQuery.isFetching ? "Searching..." : "No matching patients found."}
                      </div>
                    ) : (
                      (patientSearchQuery.data ?? []).map((patient) => (
                        <button
                          key={patient.id}
                          type="button"
                          onClick={() => {
                            setManualPatient(patient);
                            setPatientQuery("");
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-slate-50"
                        >
                          <div className="text-xs font-semibold text-slate-900">{patient.fullName}</div>
                          <div className="text-[11px] text-slate-500 font-mono">
                            {patient.uid} • {patient.mrn} • {patient.gender}, {patient.ageYears}y
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Admission ID (optional)</label>
            <Input
              value={admissionId}
              onChange={(e) => setAdmissionId(e.target.value)}
              placeholder="Link this invoice to an IPD admission"
              className="text-xs font-mono"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">2. Line Items</label>
            <InvoiceItemBuilder
              items={items}
              onChange={setItems}
              services={servicesQuery.data ?? []}
              packages={packagesQuery.data ?? []}
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

          <div className="border-t border-slate-100 pt-4">
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">3. Review</label>
            <EstimatedTotals items={items} />
          </div>

          {formError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" size="sm" className="text-xs" disabled={createMutation.isPending} onClick={handleSubmit}>
              {createMutation.isPending ? "Creating..." : "Create Invoice"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  );
}

export default function NewInvoicePage() {
  return (
    <AppShell>
      <NewInvoicePageContent />
    </AppShell>
  );
}
