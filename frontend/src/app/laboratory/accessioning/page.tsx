"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Barcode, ScanLine } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { LabAccessRestricted } from "@/components/lab/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { fromBackendListItem, listPatients } from "@/lib/patient-api";
import {
  collectSample,
  createAccession,
  listLabOrders,
  listSampleStatusHistory,
  markSampleCollected,
  processSample,
  rejectSample,
  resolveBarcode,
} from "@/lib/lab-api";
import { ApiError } from "@/types/api";
import { Patient } from "@/types/patient";
import { CONTAINER_TYPES, LabOrder, SPECIMEN_TYPES } from "@/types/lab";

function specimenLabel(value: string): string {
  return SPECIMEN_TYPES.find((s) => s.value === value)?.label ?? value;
}

function containerLabel(value: string): string {
  return CONTAINER_TYPES.find((c) => c.value === value)?.label ?? value;
}

function formatDateTime(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function sampleStatusTone(status: string): string {
  if (status === "REJECTED") return "bg-rose-50 text-rose-700 border-rose-300";
  if (status === "RECEIVED") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (status === "COLLECTED" || status === "IN_TRANSIT") return "bg-blue-50 text-blue-700 border-blue-300";
  return "bg-amber-50 text-amber-700 border-amber-300";
}

/** A printed/on-screen barcode label - no Code128 rendering library is wired
 * in yet (P6-F03 scope note), so this renders the code as a large monospace
 * "ticket" rather than a scannable symbol; a scan-gun fed the printed code
 * still round-trips through the Scan panel below. */
function BarcodeLabel({ code, caption }: { code: string; caption: string }) {
  return (
    <div className="inline-flex flex-col items-center gap-1 rounded-md border border-slate-300 bg-white px-4 py-3">
      <div className="flex items-center gap-1.5 text-slate-400">
        <Barcode className="w-3.5 h-3.5" />
        <span className="text-[10px] uppercase tracking-wide">{caption}</span>
      </div>
      <div className="font-mono text-sm font-bold tracking-widest text-slate-900">{code}</div>
    </div>
  );
}

function OrderStatusBadge({ status }: { status: string }) {
  const tone =
    status === "CANCELLED"
      ? "bg-rose-50 text-rose-700 border-rose-300"
      : status === "FINALIZED" || status === "APPROVED"
      ? "bg-emerald-50 text-emerald-700 border-emerald-300"
      : "bg-slate-100 text-slate-600 border-slate-300";
  return (
    <Badge variant="outline" className={tone}>
      {status}
    </Badge>
  );
}

function NewAccessionPanel({ canAccession }: { canAccession: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] = React.useState<Patient | null>(null);
  const [selectedOrderIds, setSelectedOrderIds] = React.useState<Set<string>>(new Set());
  const [accessionError, setAccessionError] = React.useState<string | null>(null);

  const patientSearchQuery = useQuery({
    queryKey: ["accessioning-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  const billedOrdersQuery = useQuery({
    queryKey: ["lab-orders", "BILLED", selectedPatient?.id],
    queryFn: () => listLabOrders({ patient_id: selectedPatient!.id, status: "BILLED" }),
    enabled: !!selectedPatient,
  });

  const accessionMutation = useMutation({
    mutationFn: () =>
      createAccession({ patient_id: selectedPatient!.id, lab_order_ids: Array.from(selectedOrderIds) }),
    onSuccess: () => {
      toast({ title: "Accession created", variant: "success" });
      setSelectedOrderIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      billedOrdersQuery.refetch();
    },
    onError: (error: ApiError) => setAccessionError(error?.message || "Unable to create accession."),
  });

  const toggleOrder = (id: string) => {
    setSelectedOrderIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">New Accession</h2>

        {selectedPatient ? (
          <div className="flex items-center justify-between gap-3 rounded-md border border-teal-200 bg-teal-50/60 px-3 py-2.5">
            <div>
              <div className="text-xs font-bold text-slate-900">{selectedPatient.fullName}</div>
              <div className="text-[11px] text-slate-500 font-mono">
                {selectedPatient.uid} • {selectedPatient.mrn}
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-xs h-7"
              onClick={() => {
                setSelectedPatient(null);
                setSelectedOrderIds(new Set());
                setAccessionError(null);
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
              placeholder="Search patient by name, UID, or MRN..."
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
                        setSelectedPatient(patient);
                        setPatientQuery("");
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-slate-50"
                    >
                      <div className="text-xs font-semibold text-slate-900">{patient.fullName}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {patient.uid} • {patient.mrn}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {selectedPatient && (
          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-slate-700 block">
              Billed orders awaiting accession
            </label>
            {billedOrdersQuery.isLoading ? (
              <p className="text-xs text-slate-400">Loading orders...</p>
            ) : (billedOrdersQuery.data ?? []).length === 0 ? (
              <p className="text-xs text-slate-400">No billed orders are awaiting accession for this patient.</p>
            ) : (
              <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
                {(billedOrdersQuery.data ?? []).map((order) => (
                  <label key={order.id} className="flex items-center gap-2.5 px-3 py-2 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedOrderIds.has(order.id)}
                      onChange={() => toggleOrder(order.id)}
                      className="h-3.5 w-3.5"
                    />
                    <span className="font-mono text-slate-700">{order.orderNumber}</span>
                    <OrderStatusBadge status={order.status} />
                  </label>
                ))}
              </div>
            )}

            {accessionError && (
              <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
                {accessionError}
              </p>
            )}

            <Button
              size="sm"
              className="text-xs"
              disabled={!canAccession || selectedOrderIds.size === 0 || accessionMutation.isPending}
              onClick={() => {
                setAccessionError(null);
                accessionMutation.mutate();
              }}
            >
              {accessionMutation.isPending ? "Creating..." : "Create Accession"}
            </Button>

            {accessionMutation.data && (
              <div className="pt-2">
                <BarcodeLabel code={accessionMutation.data.accessionNumber} caption="Accession ID" />
                <CollectTubesPanel
                  accessionId={accessionMutation.data.id}
                  patientId={selectedPatient.id}
                  canAccession={canAccession}
                />
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CollectTubesPanel({
  accessionId,
  patientId,
  canAccession,
}: {
  accessionId: string;
  patientId: string;
  canAccession: boolean;
}) {
  const { toast } = useToast();
  const [specimenType, setSpecimenType] = React.useState(SPECIMEN_TYPES[0].value);
  const [containerType, setContainerType] = React.useState(CONTAINER_TYPES[0].value);
  const [tubeOrderIds, setTubeOrderIds] = React.useState<Set<string>>(new Set());
  const [tubeError, setTubeError] = React.useState<string | null>(null);

  const accessionOrdersQuery = useQuery({
    queryKey: ["lab-orders", "accession", accessionId],
    queryFn: () => listLabOrders({ patient_id: patientId, accession_id: accessionId }),
  });

  const unassigned = (accessionOrdersQuery.data ?? []).filter((o) => !o.sampleId);

  const collectMutation = useMutation({
    mutationFn: () =>
      collectSample(accessionId, {
        specimen_type: specimenType,
        container_type: containerType,
        lab_order_ids: Array.from(tubeOrderIds),
      }),
    onSuccess: () => {
      toast({ title: "Tube barcode generated", variant: "success" });
      setTubeOrderIds(new Set());
      accessionOrdersQuery.refetch();
    },
    onError: (error: ApiError) => setTubeError(error?.message || "Unable to generate tube barcode."),
  });

  const toggleOrder = (id: string) => {
    setTubeOrderIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
      <label className="text-[11px] font-semibold text-slate-700 block">Generate a tube barcode</label>
      {unassigned.length === 0 ? (
        <p className="text-xs text-slate-400">Every order on this accession already has a tube assigned.</p>
      ) : (
        <>
          <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
            {unassigned.map((order) => (
              <label key={order.id} className="flex items-center gap-2.5 px-3 py-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={tubeOrderIds.has(order.id)}
                  onChange={() => toggleOrder(order.id)}
                  className="h-3.5 w-3.5"
                />
                <span className="font-mono text-slate-700">{order.orderNumber}</span>
              </label>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select
              options={SPECIMEN_TYPES.map((s) => ({ value: s.value, label: s.label }))}
              value={specimenType}
              onChange={(value) => setSpecimenType(value as typeof specimenType)}
            />
            <Select
              options={CONTAINER_TYPES.map((c) => ({ value: c.value, label: c.label }))}
              value={containerType}
              onChange={(value) => setContainerType(value as typeof containerType)}
            />
          </div>
          {tubeError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {tubeError}
            </p>
          )}
          <Button
            size="sm"
            className="text-xs"
            disabled={!canAccession || tubeOrderIds.size === 0 || collectMutation.isPending}
            onClick={() => {
              setTubeError(null);
              collectMutation.mutate();
            }}
          >
            {collectMutation.isPending ? "Generating..." : "Generate Tube Barcode"}
          </Button>
        </>
      )}
      {collectMutation.data && (
        <div className="pt-1">
          <BarcodeLabel code={collectMutation.data.barcodeId} caption="Sample Tube" />
        </div>
      )}
    </div>
  );
}

function ScanPanel({ canAccession }: { canAccession: boolean }) {
  const { toast } = useToast();
  const [code, setCode] = React.useState("");
  const [lookupCode, setLookupCode] = React.useState<string | null>(null);
  const [rejectReason, setRejectReason] = React.useState("");
  const [showHistory, setShowHistory] = React.useState(false);

  const resolveQuery = useQuery({
    queryKey: ["barcode-resolve", lookupCode],
    queryFn: () => resolveBarcode(lookupCode!),
    enabled: !!lookupCode,
    retry: false,
  });

  const resolution = resolveQuery.data;
  const sample = resolution?.sample;

  const historyQuery = useQuery({
    queryKey: ["sample-status-history", sample?.id],
    queryFn: () => listSampleStatusHistory(sample!.id),
    enabled: !!sample && showHistory,
  });

  const collectMutation = useMutation({
    mutationFn: (sampleId: string) => markSampleCollected(sampleId),
    onSuccess: () => {
      toast({ title: "Sample marked collected", variant: "success" });
      resolveQuery.refetch();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to mark collected.", variant: "destructive" }),
  });

  const processMutation = useMutation({
    mutationFn: (sampleId: string) => processSample(sampleId),
    onSuccess: () => {
      toast({ title: "Sample received at the lab", variant: "success" });
      resolveQuery.refetch();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to process sample.", variant: "destructive" }),
  });

  const rejectMutation = useMutation({
    mutationFn: (sampleId: string) => rejectSample(sampleId, rejectReason),
    onSuccess: () => {
      toast({ title: "Sample rejected", variant: "success" });
      setRejectReason("");
      resolveQuery.refetch();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to reject sample.", variant: "destructive" }),
  });

  const canReject = sample && (sample.status === "PENDING_COLLECTION" || sample.status === "COLLECTED");

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
          <ScanLine className="w-3.5 h-3.5 text-slate-400" />
          Scan / Identify
        </h2>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) setLookupCode(code.trim());
          }}
          className="flex gap-2"
        >
          <Input
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Scan or type an accession/sample barcode, then press Enter"
            className="text-xs font-mono"
          />
          <Button type="submit" size="sm" className="text-xs" disabled={!code.trim()}>
            Look Up
          </Button>
        </form>

        {resolveQuery.isFetching && <p className="text-xs text-slate-400">Looking up...</p>}
        {resolveQuery.isError && (
          <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
            {(resolveQuery.error as Error | null)?.message || "Barcode not recognized."}
          </p>
        )}

        {resolution && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge variant="outline" className="bg-slate-100 text-slate-700 border-slate-300">
                {resolution.codeType}
              </Badge>
              <span className="text-xs font-mono font-semibold text-slate-900">
                {resolution.accession.accessionNumber}
              </span>
              {sample && <span className="text-xs font-mono text-slate-500">{sample.barcodeId}</span>}
              {sample && (
                <Badge variant="outline" className={sampleStatusTone(sample.status)}>
                  {sample.status}
                </Badge>
              )}
            </div>

            {/* P6-F04: sample identification detail - collector, collection
                time, sample type, container, rejection reason. */}
            {sample && (
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-md border border-slate-200 bg-slate-50/60 px-3 py-2.5">
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">Sample Type</div>
                  <div className="text-xs text-slate-800">{specimenLabel(sample.specimenType)}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">Container</div>
                  <div className="text-xs text-slate-800">{containerLabel(sample.containerType)}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">Collector</div>
                  <div className="text-xs font-mono text-slate-800">
                    {sample.collectedBy ? sample.collectedBy.slice(0, 8) : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">Collection Time</div>
                  <div className="text-xs text-slate-800">{formatDateTime(sample.collectedAt)}</div>
                </div>
                {sample.status === "REJECTED" && (
                  <div className="col-span-2">
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Rejection Reason</div>
                    <div className="text-xs text-rose-700">{sample.rejectionReason ?? "—"}</div>
                  </div>
                )}
              </div>
            )}

            <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
              {resolution.labOrders.length === 0 ? (
                <div className="px-3 py-3 text-xs text-slate-400">No lab orders linked to this code.</div>
              ) : (
                resolution.labOrders.map((order: LabOrder) => (
                  <div key={order.id} className="flex items-center justify-between px-3 py-2">
                    <span className="text-xs font-mono text-slate-700">{order.orderNumber}</span>
                    <div className="flex items-center gap-2">
                      {(order.status === "PROCESSING" || order.status === "RESULT_ENTERED") && (
                        <Link
                          href={`/laboratory/orders/${order.id}/results`}
                          className="text-[11px] font-semibold text-teal-700 hover:underline"
                        >
                          {order.status === "PROCESSING" ? "Enter Results" : "View Results"}
                        </Link>
                      )}
                      {(order.status === "RESULT_ENTERED" ||
                        order.status === "TECHNICALLY_VERIFIED" ||
                        order.status === "PENDING_APPROVAL" ||
                        order.status === "APPROVED" ||
                        order.status === "FINALIZED") && (
                        <Link
                          href={`/laboratory/orders/${order.id}/review`}
                          className="text-[11px] font-semibold text-teal-700 hover:underline"
                        >
                          Review
                        </Link>
                      )}
                      {(order.status === "APPROVED" || order.status === "FINALIZED") && (
                        <Link
                          href={`/laboratory/orders/${order.id}/report`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] font-semibold text-teal-700 hover:underline"
                        >
                          Report
                        </Link>
                      )}
                      <OrderStatusBadge status={order.status} />
                    </div>
                  </div>
                ))
              )}
            </div>

            {sample && sample.status === "PENDING_COLLECTION" && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  className="text-xs"
                  disabled={!canAccession || collectMutation.isPending}
                  onClick={() => collectMutation.mutate(sample.id)}
                >
                  Mark Collected
                </Button>
              </div>
            )}

            {sample && sample.status === "COLLECTED" && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  className="text-xs"
                  disabled={!canAccession || processMutation.isPending}
                  onClick={() => processMutation.mutate(sample.id)}
                >
                  {processMutation.isPending ? "Processing..." : "Process (Receive at Lab)"}
                </Button>
              </div>
            )}

            {canReject && (
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Rejection reason..."
                  className="text-xs max-w-55"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs"
                  disabled={!canAccession || !rejectReason.trim() || rejectMutation.isPending}
                  onClick={() => rejectMutation.mutate(sample!.id)}
                >
                  Reject
                </Button>
              </div>
            )}

            {sample && (
              <div className="space-y-1.5">
                <button
                  type="button"
                  className="text-[11px] font-semibold text-teal-700 hover:underline"
                  onClick={() => setShowHistory((v) => !v)}
                >
                  {showHistory ? "Hide" : "Show"} sample status history
                </button>
                {showHistory && (
                  <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
                    {historyQuery.isLoading ? (
                      <div className="px-3 py-2 text-xs text-slate-400">Loading...</div>
                    ) : (historyQuery.data ?? []).length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-400">No history yet.</div>
                    ) : (
                      (historyQuery.data ?? []).map((entry) => (
                        <div key={entry.id} className="flex items-center justify-between px-3 py-1.5">
                          <Badge variant="outline" className={sampleStatusTone(entry.status)}>
                            {entry.status}
                          </Badge>
                          <span className="text-[11px] text-slate-500">{formatDateTime(entry.changedAt)}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AccessioningPageContent() {
  const { hasPermission } = useAuth();
  const canView = hasPermission("lab.view");
  const canAccession = hasPermission("lab.accession_sample");

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Accessioning" description="Accession billed orders and generate sample barcodes." />
        <LabAccessRestricted />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Accessioning"
        description="Accession billed orders, generate tube barcodes, and identify samples by scan."
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/laboratory">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Laboratory
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <NewAccessionPanel canAccession={canAccession} />
        <ScanPanel canAccession={canAccession} />
      </div>
    </PageContainer>
  );
}

export default function AccessioningPage() {
  return (
    <AppShell>
      <AccessioningPageContent />
    </AppShell>
  );
}
