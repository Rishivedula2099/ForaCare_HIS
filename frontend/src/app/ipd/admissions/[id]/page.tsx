"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BedDouble,
  FileText,
  IdCard,
  LogOut,
  ShieldCheck,
  Tags,
  Wallet,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { getPatient, toPatient } from "@/lib/patient-api";
import { listDoctors } from "@/lib/doctor-api";
import { listDepartments } from "@/lib/department-api";
import {
  dischargeAdmission,
  getAdmission,
  listConsents,
  recordConsent,
} from "@/lib/ipd-api";
import { ApiError } from "@/types/api";
import {
  ADMISSION_TYPES,
  CONSENT_TYPES,
  ConsentType,
  DISCHARGE_TYPES,
  DischargeType,
  PAYMENT_CATEGORIES,
  REFERRAL_SOURCES,
} from "@/types/ipd";

function labelFor(options: readonly { value: string; label: string }[], value: string) {
  return options.find((o) => o.value === value)?.label ?? value;
}

// ---------------------------------------------------------------------------
// Record Consent dialog (P4-F05)
// ---------------------------------------------------------------------------

function RecordConsentDialog({
  admissionId,
  patientName,
  open,
  onOpenChange,
}: {
  admissionId: string;
  patientName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [consentType, setConsentType] = React.useState<ConsentType>("GENERAL_ADMISSION");
  const [givenByName, setGivenByName] = React.useState(patientName);
  const [relationship, setRelationship] = React.useState("");
  const [consentGiven, setConsentGiven] = React.useState(true);
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      recordConsent(admissionId, {
        consent_type: consentType,
        consent_given: consentGiven,
        given_by_name: givenByName.trim(),
        relationship_to_patient: relationship.trim() || null,
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Consent recorded", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-consents", admissionId] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to record this consent."),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!givenByName.trim()) {
      setFormError("Please enter who is giving consent.");
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Consent</DialogTitle>
          <DialogDescription>Capture admission, surgical, or other consent for this patient.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Consent Type</label>
            <Select
              options={CONSENT_TYPES.map((c) => ({ value: c.value, label: c.label }))}
              value={consentType}
              onChange={(value) => setConsentType(value as ConsentType)}
              placeholder="Select consent type"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Given By</label>
            <Input value={givenByName} onChange={(e) => setGivenByName(e.target.value)} className="text-xs" />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">
              Relationship to Patient (optional)
            </label>
            <Input
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              placeholder="e.g. Self, Spouse, Parent"
              className="text-xs"
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={consentGiven}
              onChange={(e) => setConsentGiven(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            Consent given
          </label>
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
              {mutation.isPending ? "Saving..." : "Record Consent"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Discharge workflow (P4-F06): Summary -> Billing status -> Confirmation
// ---------------------------------------------------------------------------

function DischargeWorkflow({
  admissionId,
  patientName,
  admissionNumber,
  admittedAt,
  bedLabel,
  depositTotal,
}: {
  admissionId: string;
  patientName: string;
  admissionNumber: string;
  admittedAt: string;
  bedLabel: string;
  depositTotal: number;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const [dischargeType, setDischargeType] = React.useState<DischargeType>("NORMAL");
  const [dischargeCondition, setDischargeCondition] = React.useState("");
  const [dischargeSummary, setDischargeSummary] = React.useState("");
  const [followUpInstructions, setFollowUpInstructions] = React.useState("");
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      dischargeAdmission(admissionId, {
        discharge_type: dischargeType,
        discharge_condition: dischargeCondition.trim() || null,
        discharge_summary: dischargeSummary.trim() || null,
        follow_up_instructions: followUpInstructions.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Patient discharged", description: patientName, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-admission", admissionId] });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      setConfirmOpen(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to discharge this patient. Please try again.");
      queryClient.invalidateQueries({ queryKey: ["ipd-admission", admissionId] });
      setConfirmOpen(false);
    },
  });

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center gap-1.5">
          <LogOut className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-bold text-slate-900">Discharge Workflow</h3>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-semibold">
          {(["1. Summary", "2. Billing Status", "3. Confirm"] as const).map((label, i) => (
            <React.Fragment key={label}>
              {i > 0 && <div className="h-px w-4 bg-slate-200" />}
              <span className={step === i + 1 ? "text-primary" : "text-slate-400"}>{label}</span>
            </React.Fragment>
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 rounded-md p-3">
              <div>
                <span className="text-[10px] text-slate-500 block">Patient</span>
                <span className="font-semibold text-slate-900">{patientName}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Admission No.</span>
                <span className="font-mono font-semibold text-slate-900">{admissionNumber}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Current Bed</span>
                <span className="font-semibold text-slate-900">{bedLabel}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Admitted</span>
                <span className="font-semibold text-slate-900">{new Date(admittedAt).toLocaleString()}</span>
              </div>
            </div>
            <Button type="button" size="sm" className="text-xs" onClick={() => setStep(2)}>
              Continue
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
              <Wallet className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Billing is not yet automated for this facility.</p>
                <p className="text-amber-700 mt-0.5">
                  No invoicing module exists yet, so pending amount cannot be calculated. Confirm dues have been
                  settled with the billing/cashier desk before discharging.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 rounded-md p-3">
              <div>
                <span className="text-[10px] text-slate-500 block">Deposits Collected</span>
                <span className="font-semibold text-slate-900">₹{depositTotal.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Pending Amount</span>
                <span className="font-semibold text-slate-400">Not tracked</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" className="text-xs" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button type="button" size="sm" className="text-xs" onClick={() => setStep(3)}>
                Continue
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Discharge Type</label>
              <Select
                options={DISCHARGE_TYPES.map((t) => ({ value: t.value, label: t.label }))}
                value={dischargeType}
                onChange={(value) => setDischargeType(value as DischargeType)}
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Condition on Discharge (optional)</label>
              <Input
                value={dischargeCondition}
                onChange={(e) => setDischargeCondition(e.target.value)}
                placeholder="e.g. Stable, Improved"
                className="text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Discharge Summary (optional)</label>
              <textarea
                value={dischargeSummary}
                onChange={(e) => setDischargeSummary(e.target.value)}
                rows={3}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Follow-up Instructions (optional)</label>
              <textarea
                value={followUpInstructions}
                onChange={(e) => setFollowUpInstructions(e.target.value)}
                rows={2}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {formError && (
              <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
                {formError}
              </p>
            )}

            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" className="text-xs" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => setConfirmOpen(true)}
              >
                <LogOut className="w-3.5 h-3.5" />
                Discharge Patient
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Confirm discharge?"
        description={`This closes admission ${admissionNumber} for ${patientName} and frees bed ${bedLabel}. This cannot be undone.`}
        confirmLabel="Discharge"
        variant="destructive"
        isLoading={mutation.isPending}
        onConfirm={() => mutation.mutate()}
      />
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function AdmissionDetailContent({ admissionId }: { admissionId: string }) {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("ipd.manage_beds");
  const [consentDialogOpen, setConsentDialogOpen] = React.useState(false);

  const admissionQuery = useQuery({
    queryKey: ["ipd-admission", admissionId],
    queryFn: () => getAdmission(admissionId),
  });
  const admission = admissionQuery.data;

  const patientQuery = useQuery({
    queryKey: ["patient", admission?.patientId],
    queryFn: async () => toPatient(await getPatient(admission!.patientId)),
    enabled: !!admission,
  });

  const doctorsQuery = useQuery({ queryKey: ["ipd-admission-doctors"], queryFn: () => listDoctors() });
  const departmentsQuery = useQuery({ queryKey: ["ipd-admission-departments"], queryFn: () => listDepartments() });
  const consentsQuery = useQuery({
    queryKey: ["ipd-consents", admissionId],
    queryFn: () => listConsents(admissionId),
  });

  if (admissionQuery.isLoading) {
    return <p className="text-xs text-slate-400 py-8 text-center">Loading admission...</p>;
  }
  if (admissionQuery.isError || !admission) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
        Admission not found, or you don&apos;t have access to it.
      </div>
    );
  }

  const patient = patientQuery.data;
  const activeAssignment = admission.bedAssignments.find((a) => a.status === "ACTIVE");
  const bed = activeAssignment?.bed;
  const bedLabel = bed ? `${bed.bedNumber} (${bed.room.roomNumber}, ${bed.ward.name})` : "Not assigned";
  const consultant = doctorsQuery.data?.find((d) => d.id === admission.admittingDoctorId);
  const department = departmentsQuery.data?.find((d) => d.id === admission.departmentId);
  const depositTotal = admission.deposits.reduce((sum, d) => sum + d.amount, 0);

  const statusVariant =
    admission.status === "ADMITTED" ? "active" : admission.status === "DISCHARGED" ? "completed" : "alert";

  return (
    <PageContainer>
      <PageHeader
        title={patient?.fullName ?? "Admission"}
        description={`Admission ${admission.admissionNumber}`}
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/ipd">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Bed Board
            </Link>
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        <Badge variant={statusVariant}>{admission.status}</Badge>
        <Badge variant="outline">{labelFor(ADMISSION_TYPES, admission.admissionType)}</Badge>
      </div>

      {/* Overview */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Overview</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-[10px] text-slate-500 block">UID / MRN</span>
              <span className="font-mono font-semibold text-slate-900">
                {patient ? `${patient.uid} / ${patient.mrn}` : "—"}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Bed</span>
              <span className="font-semibold text-slate-900 flex items-center gap-1">
                <BedDouble className="w-3.5 h-3.5 text-slate-400" />
                {bedLabel}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Admitted</span>
              <span className="font-semibold text-slate-900">{new Date(admission.admittedAt).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Consultant</span>
              <span className="font-semibold text-slate-900">{consultant?.fullName ?? "Not assigned"}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Department</span>
              <span className="font-semibold text-slate-900">{department?.name ?? "Not assigned"}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Referral</span>
              <span className="font-semibold text-slate-900">
                {labelFor(REFERRAL_SOURCES, admission.referralSource)}
                {admission.referralDetail ? ` — ${admission.referralDetail}` : ""}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Payment Category</span>
              <span className="font-semibold text-slate-900">{labelFor(PAYMENT_CATEGORIES, admission.paymentCategory)}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Deposits Collected</span>
              <span className="font-semibold text-slate-900">₹{depositTotal.toFixed(2)}</span>
            </div>
            {admission.notes && (
              <div className="col-span-2 sm:col-span-3">
                <span className="text-[10px] text-slate-500 block">Notes</span>
                <span className="text-slate-700">{admission.notes}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Consents (P4-F05) */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-slate-500" />
              Consents
            </h3>
            {canManage && (
              <Button type="button" size="sm" variant="outline" className="text-xs" onClick={() => setConsentDialogOpen(true)}>
                Record Consent
              </Button>
            )}
          </div>

          {consentsQuery.isLoading ? (
            <p className="text-xs text-slate-400">Loading consents...</p>
          ) : (consentsQuery.data ?? []).length === 0 ? (
            <p className="text-xs text-slate-400">No consents recorded yet.</p>
          ) : (
            <div className="divide-y divide-slate-100 border border-slate-200 rounded-md">
              {(consentsQuery.data ?? []).map((consent) => (
                <div key={consent.id} className="flex items-center justify-between px-3 py-2 text-xs">
                  <div>
                    <div className="font-semibold text-slate-900">{labelFor(CONSENT_TYPES, consent.consentType)}</div>
                    <div className="text-[11px] text-slate-500">
                      {consent.givenByName}
                      {consent.relationshipToPatient ? ` (${consent.relationshipToPatient})` : ""} •{" "}
                      {new Date(consent.recordedAt).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={consent.consentGiven ? "completed" : "alert"}>
                      {consent.consentGiven ? "Given" : "Declined"}
                    </Badge>
                    <Button variant="ghost" size="sm" className="text-xs h-7" asChild>
                      <Link href={`/ipd/admissions/${admissionId}/print/consent/${consent.id}`} target="_blank">
                        Print
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents (P4-F05) */}
      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-slate-500" />
            Documents
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href={`/ipd/admissions/${admissionId}/print/identification-sheet`} target="_blank">
                <IdCard className="w-3.5 h-3.5" />
                Identification Sheet
              </Link>
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href={`/ipd/admissions/${admissionId}/print/labels`} target="_blank">
                <Tags className="w-3.5 h-3.5" />
                Admission Labels
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Discharge workflow (P4-F06) */}
      {admission.status === "ADMITTED" && canManage && (
        <DischargeWorkflow
          admissionId={admission.id}
          patientName={patient?.fullName ?? "this patient"}
          admissionNumber={admission.admissionNumber}
          admittedAt={admission.admittedAt}
          bedLabel={bedLabel}
          depositTotal={depositTotal}
        />
      )}

      {patient && (
        <RecordConsentDialog
          admissionId={admissionId}
          patientName={patient.fullName}
          open={consentDialogOpen}
          onOpenChange={setConsentDialogOpen}
        />
      )}
    </PageContainer>
  );
}

export default function AdmissionDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <AppShell>
      <AdmissionDetailContent admissionId={params.id} />
    </AppShell>
  );
}
