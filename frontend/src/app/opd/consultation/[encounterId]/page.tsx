"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Stethoscope,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  ClipboardList,
  History as HistoryIcon,
  Activity,
  Thermometer,
  FlaskConical,
  Pill,
  StickyNote,
  ChevronDown,
  Plus,
  Trash2,
  Eye,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { PageLoadingState } from "@/components/states/loading-state";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  getEncounter,
  getConsultation,
  createConsultation,
  updateConsultation,
  listPatientConsultationHistory,
  toConsultationPayload,
  formStateFromConsultation,
  getPrescription,
  createPrescription,
  updatePrescription,
  toPrescriptionPayload,
  rowsFromPrescription,
} from "@/lib/opd-api";
import {
  ConsultationFormState,
  DRUG_ROUTES,
  DrugRoute,
  EMPTY_CONSULTATION_FORM,
  OPDEncounter,
  PrescriptionItemFormRow,
  emptyPrescriptionItemRow,
} from "@/types/opd";
import { ApiError } from "@/types/api";

const TEXTAREA_CLASS =
  "flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

interface SectionProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
}

function Section({ icon: Icon, title, children }: SectionProps) {
  return (
    <Card className="shadow-xs border-slate-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs uppercase tracking-wide text-slate-500 flex items-center gap-1.5">
          <Icon className="w-3.5 h-3.5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">{children}</CardContent>
    </Card>
  );
}

function VitalField({
  label,
  unit,
  value,
  onChange,
  disabled,
}: {
  label: string;
  unit: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div>
      <label className="text-[10px] font-semibold text-slate-500 block mb-1">
        {label} <span className="text-slate-400">({unit})</span>
      </label>
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="text-xs"
      />
    </div>
  );
}

const ROUTE_LABEL: Record<DrugRoute, string> = Object.fromEntries(
  DRUG_ROUTES.map((r) => [r.value, r.label])
) as Record<DrugRoute, string>;

function PrescriptionSection({ encounterId, encounter }: { encounterId: string; encounter: OPDEncounter }) {
  const { hasPermission, user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const hasManagePermission = hasPermission("prescriptions.manage");
  // P3-F07 "doctor-specific access" - see the identical check in
  // ConsultationPageContent for the rationale.
  const isAssignedDoctor = user?.role !== "DOCTOR" || user.doctorId === encounter.doctor.id;
  const canManage = hasManagePermission && isAssignedDoctor;

  const [rows, setRows] = React.useState<PrescriptionItemFormRow[]>([]);
  const [loadedPrescriptionId, setLoadedPrescriptionId] = React.useState<string | null>(null);
  const [hasStarted, setHasStarted] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [showPreview, setShowPreview] = React.useState(false);

  const prescriptionQuery = useQuery({
    queryKey: ["opd-prescription", encounterId],
    queryFn: () => getPrescription(encounterId),
    enabled: !!encounterId,
  });

  const prescription = prescriptionQuery.data;

  if (prescription && prescription.id !== loadedPrescriptionId) {
    setLoadedPrescriptionId(prescription.id);
    setRows(rowsFromPrescription(prescription));
    setHasStarted(true);
  }

  const startRows = !prescriptionQuery.isLoading && !prescription && !hasStarted && rows.length === 0;
  if (startRows) {
    // First time opening this section with no prescription yet: seed one
    // blank row so the doctor isn't stuck looking at an empty table.
    setHasStarted(true);
    setRows([emptyPrescriptionItemRow()]);
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = toPrescriptionPayload(rows);
      return prescription ? updatePrescription(encounterId, payload) : createPrescription(encounterId, payload);
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(["opd-prescription", encounterId], saved);
      setFormError(null);
      toast({ title: "Prescription saved", variant: "success" });
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to save this prescription.");
    },
  });

  const updateRow = (key: string, patch: Partial<PrescriptionItemFormRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  };

  const removeRow = (key: string) => {
    setRows((current) => current.filter((row) => row.key !== key));
  };

  const handleSave = () => {
    setFormError(null);
    if (rows.length === 0) {
      setFormError("Add at least one medicine before saving.");
      return;
    }
    for (const row of rows) {
      if (!row.drugName.trim() || !row.dosage.trim() || !row.frequency.trim() || !row.duration.trim()) {
        setFormError("Every medicine needs a name, dosage, frequency, and duration.");
        return;
      }
    }
    saveMutation.mutate();
  };

  const isReadOnly = !canManage;

  return (
    <Card className="shadow-xs border-slate-200">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-xs uppercase tracking-wide text-slate-500 flex items-center gap-1.5">
          <Pill className="w-3.5 h-3.5" />
          Prescription
        </CardTitle>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={rows.length === 0}
          onClick={() => setShowPreview(true)}
          className="h-7 gap-1.5 text-xs"
        >
          <Eye className="w-3.5 h-3.5" />
          Preview
        </Button>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        {hasManagePermission && !isAssignedDoctor && (
          <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2.5 py-1.5">
            Read-only — this encounter is assigned to {encounter.doctor.fullName}, not you.
          </p>
        )}
        {prescriptionQuery.isLoading ? (
          <p className="text-xs text-slate-400">Loading prescription...</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-separate border-spacing-y-1.5">
                <thead>
                  <tr className="text-[10px] uppercase text-slate-400 text-left">
                    <th className="font-semibold pb-1">Medicine</th>
                    <th className="font-semibold pb-1">Dosage</th>
                    <th className="font-semibold pb-1">Route</th>
                    <th className="font-semibold pb-1">Frequency</th>
                    <th className="font-semibold pb-1">Duration</th>
                    <th className="font-semibold pb-1">Instructions</th>
                    <th className="pb-1" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.key}>
                      <td className="pr-1.5 min-w-32">
                        <Input
                          value={row.drugName}
                          onChange={(e) => updateRow(row.key, { drugName: e.target.value })}
                          disabled={isReadOnly}
                          placeholder="e.g. Amoxicillin"
                          className="text-xs h-8"
                        />
                      </td>
                      <td className="pr-1.5 min-w-24">
                        <Input
                          value={row.dosage}
                          onChange={(e) => updateRow(row.key, { dosage: e.target.value })}
                          disabled={isReadOnly}
                          placeholder="e.g. 500mg"
                          className="text-xs h-8"
                        />
                      </td>
                      <td className="pr-1.5 min-w-28">
                        <Select
                          options={DRUG_ROUTES.map((r) => ({ value: r.value, label: r.label }))}
                          value={row.route}
                          onChange={(value) => updateRow(row.key, { route: value as DrugRoute })}
                          disabled={isReadOnly}
                        />
                      </td>
                      <td className="pr-1.5 min-w-24">
                        <Input
                          value={row.frequency}
                          onChange={(e) => updateRow(row.key, { frequency: e.target.value })}
                          disabled={isReadOnly}
                          placeholder="e.g. TID"
                          className="text-xs h-8"
                        />
                      </td>
                      <td className="pr-1.5 min-w-24">
                        <Input
                          value={row.duration}
                          onChange={(e) => updateRow(row.key, { duration: e.target.value })}
                          disabled={isReadOnly}
                          placeholder="e.g. 5 days"
                          className="text-xs h-8"
                        />
                      </td>
                      <td className="pr-1.5 min-w-32">
                        <Input
                          value={row.instructions}
                          onChange={(e) => updateRow(row.key, { instructions: e.target.value })}
                          disabled={isReadOnly}
                          placeholder="e.g. After food"
                          className="text-xs h-8"
                        />
                      </td>
                      <td>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={isReadOnly}
                          onClick={() => removeRow(row.key)}
                          className="h-8 w-8 p-0 text-slate-400 hover:text-destructive"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!isReadOnly && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setRows((current) => [...current, emptyPrescriptionItemRow()])}
                className="gap-1.5 text-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Medicine
              </Button>
            )}

            {formError && <p className="text-xs text-destructive">{formError}</p>}

            {!isReadOnly && (
              <div className="flex justify-end pt-1">
                <Button
                  type="button"
                  size="sm"
                  disabled={saveMutation.isPending}
                  onClick={handleSave}
                  className="text-xs"
                >
                  {saveMutation.isPending ? "Saving..." : "Save Prescription"}
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>

      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent size="lg">
          <DialogHeader>
            <DialogTitle>Prescription Preview</DialogTitle>
            <DialogDescription>
              {encounter.patient.fullName} • {encounter.encounterNumber}
            </DialogDescription>
          </DialogHeader>
          <div className="border border-slate-200 rounded-md p-5 space-y-4 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <div className="text-sm font-bold text-slate-900">{encounter.doctor.fullName}</div>
                <div className="text-[11px] text-slate-500">{encounter.doctor.specialization}</div>
              </div>
              <div className="text-right text-[11px] text-slate-500">
                <div>{new Date().toLocaleDateString()}</div>
                <div>{encounter.department.name}</div>
              </div>
            </div>
            <div className="text-xs text-slate-700">
              <span className="text-slate-400">Patient: </span>
              <span className="font-semibold">{encounter.patient.fullName}</span>
              <span className="text-slate-400"> • UID: </span>
              <span className="font-mono">{encounter.patient.uid}</span>
            </div>
            <div className="space-y-2">
              {rows.map((row, index) => (
                <div key={row.key} className="text-xs border-b border-dashed border-slate-100 pb-2">
                  <div className="font-semibold text-slate-900">
                    {index + 1}. {row.drugName || "—"}{" "}
                    <span className="font-normal text-slate-500">
                      ({row.dosage || "—"}, {ROUTE_LABEL[row.route]})
                    </span>
                  </div>
                  <div className="text-slate-500 ml-4">
                    {row.frequency || "—"} • {row.duration || "—"}
                    {row.instructions && <> • {row.instructions}</>}
                  </div>
                </div>
              ))}
              {rows.length === 0 && <p className="text-xs text-slate-400">No medicines added yet.</p>}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function ConsultationPageContent() {
  const params = useParams<{ encounterId: string }>();
  const encounterId = params.encounterId;
  const { hasPermission, user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const hasManagePermission = hasPermission("consultations.manage");

  const [form, setForm] = React.useState<ConsultationFormState>(EMPTY_CONSULTATION_FORM);
  const [loadedConsultationId, setLoadedConsultationId] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [showHistory, setShowHistory] = React.useState(false);

  const encounterQuery = useQuery({
    queryKey: ["opd-encounter", encounterId],
    queryFn: () => getEncounter(encounterId),
    enabled: !!encounterId,
  });

  const consultationQuery = useQuery({
    queryKey: ["opd-consultation", encounterId],
    queryFn: () => getConsultation(encounterId),
    enabled: !!encounterId,
  });

  const patientId = encounterQuery.data?.patient.id;
  const historyQuery = useQuery({
    queryKey: ["opd-consultation-history", patientId],
    queryFn: () => listPatientConsultationHistory(patientId as string),
    enabled: !!patientId && showHistory,
  });

  // Sync the editable form from the fetched consultation exactly once per
  // consultation (by id) - a "set state during render" sync rather than an
  // effect, so a background refetch of the same consultation never clobbers
  // in-progress edits between saves. See React's "adjusting state when a
  // prop changes" pattern.
  if (consultationQuery.data && consultationQuery.data.id !== loadedConsultationId) {
    setLoadedConsultationId(consultationQuery.data.id);
    setForm(formStateFromConsultation(consultationQuery.data));
  }

  const createMutation = useMutation({
    mutationFn: () => createConsultation(encounterId, toConsultationPayload(EMPTY_CONSULTATION_FORM)),
    onSuccess: (consultation) => {
      queryClient.setQueryData(["opd-consultation", encounterId], consultation);
      toast({ title: "Consultation started", variant: "success" });
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to start this consultation.");
    },
  });

  const saveMutation = useMutation({
    mutationFn: (statusOverride?: "COMPLETED") =>
      updateConsultation(encounterId, { ...toConsultationPayload(form), status: statusOverride }),
    onSuccess: (consultation, statusOverride) => {
      queryClient.setQueryData(["opd-consultation", encounterId], consultation);
      queryClient.invalidateQueries({ queryKey: ["opd-encounter", encounterId] });
      setFormError(null);
      toast({
        title: statusOverride === "COMPLETED" ? "Consultation completed" : "Draft saved",
        variant: "success",
      });
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to save this consultation.");
    },
  });

  if (encounterQuery.isLoading || consultationQuery.isLoading) {
    return <PageLoadingState label="Loading consultation..." />;
  }

  if (encounterQuery.isError || !encounterQuery.data) {
    return (
      <PageContainer>
        <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>This OPD encounter could not be found.</span>
        </div>
      </PageContainer>
    );
  }

  const encounter = encounterQuery.data;
  const consultation = consultationQuery.data;

  // P3-F07 "doctor-specific access": a DOCTOR-role user only gets write
  // access to encounters actually assigned to them - mirrors the backend's
  // `_ensure_is_assigned_doctor` so the UI doesn't offer an editable form
  // that's destined to 403 on save. Non-DOCTOR roles (admin override) are
  // governed by the RBAC permission alone, same as the backend.
  const isAssignedDoctor = user?.role !== "DOCTOR" || user.doctorId === encounter.doctor.id;
  const canManage = hasManagePermission && isAssignedDoctor;
  const isReadOnly = !canManage || consultation?.status === "COMPLETED";

  const pastConsultations = (historyQuery.data ?? []).filter((c) => c.id !== consultation?.id);

  return (
    <PageContainer>
      <div className="flex items-center gap-2 mb-1">
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1" asChild>
          <Link href="/opd">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to OPD
          </Link>
        </Button>
      </div>

      <PageHeader
        title={`Consultation — ${encounter.patient.fullName}`}
        description={`${encounter.encounterNumber} • Token #${encounter.token?.tokenNumber ?? "—"} • ${encounter.doctor.fullName} • ${encounter.department.name}`}
        actions={
          consultation && (
            <Badge
              variant="outline"
              className={
                consultation.status === "COMPLETED"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : "bg-amber-50 text-amber-700 border-amber-300"
              }
            >
              {consultation.status === "COMPLETED" ? "Completed" : "In Progress"}
            </Badge>
          )
        }
      />

      {!canManage && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {hasManagePermission && !isAssignedDoctor
              ? `You have read-only access — this encounter is assigned to ${encounter.doctor.fullName}, not you.`
              : "You have read-only access to this consultation."}
          </span>
        </div>
      )}

      <div className="border border-slate-200 rounded-md">
        <button
          type="button"
          onClick={() => setShowHistory((v) => !v)}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-700"
        >
          <span className="flex items-center gap-1.5">
            <HistoryIcon className="w-3.5 h-3.5" />
            Previous Consultations
          </span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showHistory ? "rotate-180" : ""}`} />
        </button>
        {showHistory && (
          <div className="border-t border-slate-100 px-3 py-2">
            {historyQuery.isLoading ? (
              <p className="text-xs text-slate-400">Loading history...</p>
            ) : pastConsultations.length === 0 ? (
              <p className="text-xs text-slate-400">No previous consultations for this patient.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {pastConsultations.map((c) => (
                  <div key={c.id} className="py-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800">
                        {new Date(c.createdAt).toLocaleDateString()} — {c.doctor.fullName}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {c.status}
                      </Badge>
                    </div>
                    {c.diagnosis && <p className="text-slate-500 mt-0.5">Diagnosis: {c.diagnosis}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {!consultation ? (
        <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
          <CardContent className="p-8 text-center space-y-3">
            <Stethoscope className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-sm text-slate-600">No consultation has been started for this encounter yet.</p>
            <Button
              type="button"
              size="sm"
              disabled={!canManage || createMutation.isPending}
              onClick={() => createMutation.mutate()}
              title={canManage ? undefined : "Only the assigned doctor can start this consultation"}
            >
              {createMutation.isPending ? "Starting..." : "Start Consultation"}
            </Button>
            {formError && <p className="text-xs text-destructive">{formError}</p>}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Section icon={ClipboardList} title="Complaints">
            <textarea
              value={form.chiefComplaint}
              onChange={(e) => setForm((f) => ({ ...f, chiefComplaint: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="Presenting complaints"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={HistoryIcon} title="History">
            <textarea
              value={form.history}
              onChange={(e) => setForm((f) => ({ ...f, history: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="History of present illness / relevant past history"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={Stethoscope} title="Examination">
            <textarea
              value={form.examination}
              onChange={(e) => setForm((f) => ({ ...f, examination: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="Clinical examination findings"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={CheckCircle2} title="Diagnosis">
            <textarea
              value={form.diagnosis}
              onChange={(e) => setForm((f) => ({ ...f, diagnosis: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="Provisional / final diagnosis"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={AlertTriangle} title="Allergies">
            <textarea
              value={form.allergies}
              onChange={(e) => setForm((f) => ({ ...f, allergies: e.target.value }))}
              disabled={isReadOnly}
              rows={2}
              placeholder="Known drug / food allergies"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={FlaskConical} title="Investigation">
            <textarea
              value={form.investigation}
              onChange={(e) => setForm((f) => ({ ...f, investigation: e.target.value }))}
              disabled={isReadOnly}
              rows={2}
              placeholder="Tests / investigations ordered"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={Pill} title="Treatment">
            <textarea
              value={form.treatment}
              onChange={(e) => setForm((f) => ({ ...f, treatment: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="Medications / treatment plan"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <Section icon={StickyNote} title="Notes">
            <textarea
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              disabled={isReadOnly}
              rows={3}
              placeholder="Additional notes"
              className={TEXTAREA_CLASS}
            />
          </Section>

          <div className="lg:col-span-2">
            <Section icon={Activity} title="Vitals">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <VitalField
                  label="Temperature"
                  unit="°C"
                  value={form.temperatureCelsius}
                  onChange={(v) => setForm((f) => ({ ...f, temperatureCelsius: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="Pulse"
                  unit="bpm"
                  value={form.pulseBpm}
                  onChange={(v) => setForm((f) => ({ ...f, pulseBpm: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="BP Systolic"
                  unit="mmHg"
                  value={form.bpSystolic}
                  onChange={(v) => setForm((f) => ({ ...f, bpSystolic: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="BP Diastolic"
                  unit="mmHg"
                  value={form.bpDiastolic}
                  onChange={(v) => setForm((f) => ({ ...f, bpDiastolic: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="SpO2"
                  unit="%"
                  value={form.spo2Percent}
                  onChange={(v) => setForm((f) => ({ ...f, spo2Percent: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="Resp. Rate"
                  unit="/min"
                  value={form.respiratoryRate}
                  onChange={(v) => setForm((f) => ({ ...f, respiratoryRate: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="Weight"
                  unit="kg"
                  value={form.weightKg}
                  onChange={(v) => setForm((f) => ({ ...f, weightKg: v }))}
                  disabled={isReadOnly}
                />
                <VitalField
                  label="Height"
                  unit="cm"
                  value={form.heightCm}
                  onChange={(v) => setForm((f) => ({ ...f, heightCm: v }))}
                  disabled={isReadOnly}
                />
              </div>
              <div className="mt-2 flex items-center gap-1 text-[10px] text-slate-400">
                <Thermometer className="w-3 h-3" />
                Leave a field blank to skip it — saved values are never cleared by an empty field.
              </div>
            </Section>
          </div>
        </div>
      )}

      {formError && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{formError}</span>
        </div>
      )}

      {consultation && !isReadOnly && (
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={saveMutation.isPending}
            onClick={() => saveMutation.mutate(undefined)}
            className="text-xs"
          >
            {saveMutation.isPending ? "Saving..." : "Save Draft"}
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={saveMutation.isPending}
            onClick={() => saveMutation.mutate("COMPLETED")}
            className="gap-1.5 text-xs"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Complete Consultation
          </Button>
        </div>
      )}

      {consultation && <PrescriptionSection encounterId={encounterId} encounter={encounter} />}
    </PageContainer>
  );
}

export default function ConsultationPage() {
  return (
    <AppShell>
      <ConsultationPageContent />
    </AppShell>
  );
}
