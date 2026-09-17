"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Stethoscope,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Ticket,
  RotateCcw,
  User as UserIcon,
  Star,
  PhoneCall,
  Play,
  CheckCheck,
  SkipForward,
  XCircle,
  Undo2,
  Clock,
  QrCode,
  Camera,
  CameraOff,
  ShieldQuestion,
  ShieldX,
  ShieldOff,
  ShieldCheck,
} from "lucide-react";
import jsQR from "jsqr";
import { QRCodeSVG } from "qrcode.react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { SearchInput } from "@/components/ui/search-input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { cn } from "@/lib/utils";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { listDepartments } from "@/lib/department-api";
import { listDoctors } from "@/lib/doctor-api";
import { listPatients, fromBackendListItem } from "@/lib/patient-api";
import {
  registerVisit,
  toCreatePayload,
  getDoctorQueue,
  getDoctorQueueWebSocketUrl,
  callNextToken,
  updateTokenStatus,
  listEncounters,
  verifyQrCode,
  revokeQr,
} from "@/lib/opd-api";
import { Patient } from "@/types/patient";
import {
  OPDEncounter,
  OPDRegistrationFormState,
  QRVerifyResult,
  TOKEN_PRIORITIES,
  TOKEN_STATUS_BADGE_VARIANT,
  TOKEN_STATUS_LABEL,
  TokenPriority,
  TokenStatus,
  VISIT_TYPES,
  VisitType,
} from "@/types/opd";
import { ApiError } from "@/types/api";

const EMPTY_FORM: OPDRegistrationFormState = {
  patientId: "",
  departmentId: "",
  doctorId: "",
  visitType: "WALK_IN",
  priority: "NORMAL",
  notes: "",
};

// P3-B03/P3-F03 "real-time refresh": the WebSocket (see the effect in
// QueueTab) is the primary channel - this is just the safety-net poll
// interval in case a socket drops without the client noticing right away.
const QUEUE_POLL_FALLBACK_MS = 20000;

function RegistrationTab() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canRegister = hasPermission("opd.manage_queue");

  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] = React.useState<Patient | null>(null);
  const [form, setForm] = React.useState<OPDRegistrationFormState>(EMPTY_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [confirmation, setConfirmation] = React.useState<OPDEncounter | null>(null);

  const patientSearchQuery = useQuery({
    queryKey: ["opd-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  const departmentsQuery = useQuery({
    queryKey: ["departments", ""],
    queryFn: () => listDepartments(),
  });

  const activeDepartments = (departmentsQuery.data ?? []).filter((d) => d.isActive);

  const doctorsQuery = useQuery({
    queryKey: ["doctors-by-department", form.departmentId],
    queryFn: () => listDoctors({ department_id: form.departmentId }),
    enabled: !!form.departmentId,
  });

  const activeDoctors = (doctorsQuery.data ?? []).filter((d) => d.isActive);

  const registerMutation = useMutation({
    mutationFn: (data: OPDRegistrationFormState) => registerVisit(toCreatePayload(data)),
    onSuccess: (encounter) => {
      toast({ title: "OPD visit registered", description: encounter.encounterNumber, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["opd-encounters"] });
      queryClient.invalidateQueries({ queryKey: ["opd-doctor-queue"] });
      setConfirmation(encounter);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to register this visit. Please try again.");
    },
  });

  const handleSelectPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setForm((f) => ({ ...f, patientId: patient.id }));
    setPatientQuery("");
  };

  const handleChangePatient = () => {
    setSelectedPatient(null);
    setForm((f) => ({ ...f, patientId: "" }));
  };

  const handleDepartmentChange = (departmentId: string) => {
    setForm((f) => ({ ...f, departmentId, doctorId: "" }));
  };

  const resetForRegisterAnother = () => {
    setConfirmation(null);
    setSelectedPatient(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!form.patientId) {
      setFormError("Please search for and select a patient.");
      return;
    }
    if (!form.departmentId) {
      setFormError("Please select a department.");
      return;
    }
    if (!form.doctorId) {
      setFormError("Please select a doctor.");
      return;
    }

    registerMutation.mutate(form);
  };

  const departmentOptions = activeDepartments.map((d) => ({ value: d.id, label: `${d.name} (${d.code})` }));
  const doctorOptions = activeDoctors.map((d) => ({
    value: d.id,
    label: `${d.fullName} — ${d.specialization}`,
  }));

  return (
    <div className="space-y-4">
      {!canRegister && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">You don&apos;t have permission to register OPD visits.</p>
            <p className="text-amber-700 mt-0.5">
              Contact a Hospital Admin if you believe you should have access to OPD registration.
            </p>
          </div>
        </div>
      )}

      {confirmation ? (
        <Card className="border-emerald-200 bg-emerald-50/40 shadow-xs">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Visit registered successfully</h3>
                <p className="text-xs text-slate-500">{confirmation.patient.fullName}</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <div className="grid grid-cols-2 gap-3 p-3 bg-white rounded-lg border border-emerald-200 text-xs flex-1">
                <div>
                  <span className="text-[10px] text-slate-500 block">Encounter No.</span>
                  <span className="font-mono font-semibold text-slate-900">{confirmation.encounterNumber}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Token No.</span>
                  <span className="font-mono font-bold text-lg text-teal-700">
                    {confirmation.token?.tokenNumber ?? "—"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Doctor</span>
                  <span className="font-semibold text-slate-900">{confirmation.doctor.fullName}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Department</span>
                  <span className="font-semibold text-slate-900">{confirmation.department.name}</span>
                </div>
              </div>

              {/* Display QR (P3-F04): the patient's check-in code for this visit */}
              <div className="flex flex-col items-center justify-center gap-1.5 p-3 bg-white rounded-lg border border-emerald-200">
                <QRCodeSVG value={confirmation.qrCode} size={96} />
                <span className="text-[10px] text-slate-400">Scan at doctor&apos;s desk to check in</span>
              </div>
            </div>

            <Button type="button" size="sm" onClick={resetForRegisterAnother} className="gap-1.5 text-xs">
              <RotateCcw className="w-3.5 h-3.5" />
              Register Another Visit
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-xs border-slate-200">
          <CardContent className="p-5">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Step 1: Patient search */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-slate-700 block">1. Search Patient</label>
                {selectedPatient ? (
                  <div className="flex items-center justify-between gap-3 rounded-md border border-teal-200 bg-teal-50/60 px-3 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <UserIcon className="w-4 h-4 text-teal-700 shrink-0" />
                      <div>
                        <div className="text-xs font-bold text-slate-900">{selectedPatient.fullName}</div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {selectedPatient.uid} • {selectedPatient.mrn}
                        </div>
                      </div>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={handleChangePatient} className="text-xs h-7">
                      Change
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <SearchInput
                      placeholder="Search by patient UID, MRN, or name..."
                      onSearchChange={setPatientQuery}
                      isLoading={patientSearchQuery.isFetching}
                      disabled={!canRegister}
                    />
                    {patientQuery.trim().length >= 2 && (
                      <div className="border border-slate-200 rounded-md divide-y divide-slate-100 max-h-56 overflow-y-auto">
                        {(patientSearchQuery.data ?? []).length === 0 ? (
                          <div className="px-3 py-3 text-xs text-slate-400 flex items-center gap-1.5">
                            <Search className="w-3.5 h-3.5" />
                            {patientSearchQuery.isFetching ? "Searching..." : "No matching patients found."}
                          </div>
                        ) : (
                          (patientSearchQuery.data ?? []).map((patient) => (
                            <button
                              key={patient.id}
                              type="button"
                              onClick={() => handleSelectPatient(patient)}
                              className="w-full text-left px-3 py-2 hover:bg-slate-50 transition-colors"
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

              {/* Step 2: Department */}
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">2. Select Department</label>
                <Select
                  options={departmentOptions}
                  value={form.departmentId}
                  onChange={handleDepartmentChange}
                  placeholder="Select a department"
                  disabled={!canRegister}
                />
              </div>

              {/* Step 3: Doctor */}
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">3. Select Doctor</label>
                <Select
                  options={doctorOptions}
                  value={form.doctorId}
                  onChange={(doctorId) => setForm((f) => ({ ...f, doctorId }))}
                  placeholder={form.departmentId ? "Select a doctor" : "Select a department first"}
                  disabled={!canRegister || !form.departmentId}
                />
                {form.departmentId && !doctorsQuery.isLoading && doctorOptions.length === 0 && (
                  <p className="text-[11px] text-amber-600 mt-1">No active doctors in this department.</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Visit type */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">Visit Type</label>
                  <div className="flex items-center gap-2">
                    {VISIT_TYPES.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        disabled={!canRegister}
                        onClick={() => setForm((f) => ({ ...f, visitType: option.value as VisitType }))}
                        className={cn(
                          "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors",
                          form.visitType === option.value
                            ? "bg-primary text-white border-primary"
                            : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                        )}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Priority */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">Priority</label>
                  <div className="flex items-center gap-2">
                    {TOKEN_PRIORITIES.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        disabled={!canRegister}
                        onClick={() => setForm((f) => ({ ...f, priority: option.value as TokenPriority }))}
                        className={cn(
                          "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors inline-flex items-center gap-1",
                          form.priority === option.value
                            ? "bg-amber-500 text-white border-amber-500"
                            : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                        )}
                      >
                        {option.value === "PRIORITY" && <Star className="w-3 h-3" />}
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">Notes (optional)</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Any relevant notes for this visit"
                  rows={2}
                  disabled={!canRegister}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>

              {formError && (
                <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="submit"
                  size="sm"
                  disabled={!canRegister || registerMutation.isPending}
                  className="gap-1.5 text-xs"
                  title={canRegister ? undefined : "You don't have permission to register OPD visits"}
                >
                  <Ticket className="w-3.5 h-3.5" />
                  {registerMutation.isPending ? "Registering..." : "Register Visit"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function TokenStatusBadge({ status }: { status: TokenStatus }) {
  return <Badge variant={TOKEN_STATUS_BADGE_VARIANT[status]}>{TOKEN_STATUS_LABEL[status]}</Badge>;
}

function PriorityBadge({ priority }: { priority: TokenPriority }) {
  if (priority !== "PRIORITY") return null;
  return (
    <Badge variant="outline" className="gap-1 text-[10px] bg-amber-50 text-amber-800 border-amber-300">
      <Star className="w-2.5 h-2.5" />
      Priority
    </Badge>
  );
}

function QueueTab() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManageQueue = hasPermission("opd.manage_queue");

  const [departmentFilter, setDepartmentFilter] = React.useState("ALL");
  const [doctorId, setDoctorId] = React.useState("");
  const [actionError, setActionError] = React.useState<string | null>(null);

  const departmentsQuery = useQuery({
    queryKey: ["departments", ""],
    queryFn: () => listDepartments(),
  });

  const doctorsQuery = useQuery({
    queryKey: ["doctors-by-department", departmentFilter === "ALL" ? "" : departmentFilter],
    queryFn: () =>
      listDoctors({ department_id: departmentFilter !== "ALL" ? departmentFilter : undefined }),
  });
  const activeDoctors = (doctorsQuery.data ?? []).filter((d) => d.isActive);

  // Derived (not effect-synced) so a doctor is always selected once the
  // list loads, without the cascading-render pattern of setState-in-effect.
  const effectiveDoctorId =
    doctorId && activeDoctors.some((d) => d.id === doctorId) ? doctorId : activeDoctors[0]?.id ?? "";

  const queueQuery = useQuery({
    queryKey: ["opd-doctor-queue", effectiveDoctorId],
    queryFn: () => getDoctorQueue(effectiveDoctorId),
    enabled: !!effectiveDoctorId,
    refetchInterval: QUEUE_POLL_FALLBACK_MS,
  });

  const invalidateQueue = () => {
    queryClient.invalidateQueries({ queryKey: ["opd-doctor-queue", effectiveDoctorId] });
  };

  const [isLive, setIsLive] = React.useState(false);

  // P3-B03 queue-updates channel: push notifications from the backend
  // trigger an immediate refetch instead of waiting for the next poll.
  // Reconnects on drop (server restart, network blip) with a fixed delay -
  // simple and sufficient at this app's scale, no backoff/jitter needed.
  React.useEffect(() => {
    if (!effectiveDoctorId) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      socket = new WebSocket(getDoctorQueueWebSocketUrl(effectiveDoctorId));
      socket.onopen = () => setIsLive(true);
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string);
          if (data?.type === "queue_updated") {
            queryClient.invalidateQueries({ queryKey: ["opd-doctor-queue", effectiveDoctorId] });
          }
        } catch {
          // Ignore malformed frames rather than crashing the socket handler.
        }
      };
      socket.onclose = () => {
        setIsLive(false);
        if (!cancelled) reconnectTimer = setTimeout(connect, 4000);
      };
      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [effectiveDoctorId, queryClient]);

  const callNextMutation = useMutation({
    mutationFn: () => callNextToken(effectiveDoctorId),
    onSuccess: (encounter) => {
      toast({
        title: "Token called",
        description: `#${encounter.token?.tokenNumber} — ${encounter.patient.fullName}`,
        variant: "success",
      });
      setActionError(null);
      invalidateQueue();
    },
    onError: (error: ApiError) => setActionError(error?.message || "Unable to call the next token."),
  });

  const statusMutation = useMutation({
    mutationFn: ({ tokenId, status }: { tokenId: string; status: TokenStatus }) =>
      updateTokenStatus(tokenId, status),
    onSuccess: () => {
      setActionError(null);
      invalidateQueue();
    },
    onError: (error: ApiError) => setActionError(error?.message || "Unable to update this token."),
  });

  const encounters = queueQuery.data ?? [];
  const current = encounters.find((e) => e.token && ["CALLED", "IN_CONSULTATION"].includes(e.token.status));
  const waiting = encounters.filter((e) => e.token?.status === "WAITING");
  const skipped = encounters.filter((e) => e.token?.status === "SKIPPED");
  const done = encounters.filter((e) => e.token && ["COMPLETED", "CANCELLED"].includes(e.token.status));

  const departmentOptions = [
    { value: "ALL", label: "All Departments" },
    ...(departmentsQuery.data ?? []).filter((d) => d.isActive).map((d) => ({ value: d.id, label: d.name })),
  ];
  const doctorOptions = activeDoctors.map((d) => ({ value: d.id, label: d.fullName }));

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="w-full sm:w-56">
          <Select
            options={departmentOptions}
            value={departmentFilter}
            onChange={(value) => {
              setDepartmentFilter(value);
              setDoctorId("");
            }}
            placeholder="Filter by department"
          />
        </div>
        <div className="w-full sm:w-72">
          <Select
            options={doctorOptions}
            value={effectiveDoctorId}
            onChange={setDoctorId}
            placeholder="Select a doctor's queue"
          />
        </div>
        {effectiveDoctorId && (
          <span
            className={cn(
              "text-[11px] flex items-center gap-1 self-center",
              isLive ? "text-emerald-600" : "text-slate-400"
            )}
          >
            <span className={cn("w-1.5 h-1.5 rounded-full", isLive ? "bg-emerald-500 animate-pulse" : "bg-slate-300")} />
            {isLive ? "Live" : "Reconnecting..."}
          </span>
        )}
        {queueQuery.isFetching && (
          <span className="text-[11px] text-slate-400 flex items-center gap-1 self-center">
            <Clock className="w-3 h-3 animate-pulse" />
            Refreshing...
          </span>
        )}
      </div>

      {!effectiveDoctorId ? (
        <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
          <CardContent className="p-8 text-center text-xs text-slate-400">
            Select a doctor to view their live OPD queue.
          </CardContent>
        </Card>
      ) : (
        <>
          {actionError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{actionError}</span>
            </div>
          )}

          {/* Current token */}
          <Card className={cn("shadow-xs", current ? "border-teal-300 bg-teal-50/40" : "border-slate-200")}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Current Token</span>
                {!current && (
                  <Button
                    type="button"
                    size="sm"
                    className="gap-1.5 text-xs"
                    disabled={!canManageQueue || waiting.length === 0 || callNextMutation.isPending}
                    onClick={() => callNextMutation.mutate()}
                    title={canManageQueue ? undefined : "You don't have permission to manage the OPD queue"}
                  >
                    <PhoneCall className="w-3.5 h-3.5" />
                    {callNextMutation.isPending ? "Calling..." : "Call Next"}
                  </Button>
                )}
              </div>

              {current?.token ? (
                <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="text-4xl font-extrabold font-mono text-teal-700">
                      #{current.token.tokenNumber}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{current.patient.fullName}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {current.patient.uid} • {current.encounterNumber}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <TokenStatusBadge status={current.token.status} />
                        <PriorityBadge priority={current.token.priority} />
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button type="button" size="sm" variant="outline" className="gap-1.5 text-xs" asChild>
                      <Link href={`/opd/consultation/${current.id}`}>
                        <Stethoscope className="w-3.5 h-3.5" />
                        Open Consultation
                      </Link>
                    </Button>
                    {current.token.status === "CALLED" && (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={!canManageQueue || statusMutation.isPending}
                          onClick={() => statusMutation.mutate({ tokenId: current.token!.id, status: "IN_CONSULTATION" })}
                          className="gap-1.5 text-xs"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Start Consultation
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={!canManageQueue || statusMutation.isPending}
                          onClick={() => statusMutation.mutate({ tokenId: current.token!.id, status: "SKIPPED" })}
                          className="gap-1.5 text-xs text-amber-700 border-amber-200 hover:bg-amber-50"
                        >
                          <SkipForward className="w-3.5 h-3.5" />
                          Skip
                        </Button>
                      </>
                    )}
                    {current.token.status === "IN_CONSULTATION" && (
                      <Button
                        type="button"
                        size="sm"
                        disabled={!canManageQueue || statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ tokenId: current.token!.id, status: "COMPLETED" })}
                        className="gap-1.5 text-xs"
                      >
                        <CheckCheck className="w-3.5 h-3.5" />
                        Complete
                      </Button>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={!canManageQueue || statusMutation.isPending}
                      onClick={() => statusMutation.mutate({ tokenId: current.token!.id, status: "CANCELLED" })}
                      className="gap-1.5 text-xs text-destructive hover:bg-destructive/5"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-xs text-slate-400">
                  {waiting.length === 0
                    ? "No tokens waiting."
                    : "No token currently called. Click \"Call Next\" to bring up the next patient."}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Waiting list */}
          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                Waiting List ({waiting.length})
              </span>
              {waiting.length === 0 ? (
                <p className="mt-2 text-xs text-slate-400">No patients waiting.</p>
              ) : (
                <div className="mt-2 divide-y divide-slate-100">
                  {waiting.map((e) => (
                    <div key={e.id} className="flex items-center justify-between py-2 text-xs">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-slate-700 w-8">#{e.token?.tokenNumber}</span>
                        <div>
                          <div className="font-semibold text-slate-900">{e.patient.fullName}</div>
                          <div className="text-[11px] text-slate-500 font-mono">{e.patient.uid}</div>
                        </div>
                        {e.token && <PriorityBadge priority={e.token.priority} />}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        disabled={!canManageQueue || statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ tokenId: e.token!.id, status: "CANCELLED" })}
                        className="h-7 w-7 p-0 text-slate-400 hover:text-destructive"
                        title="Cancel this token"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Skipped list */}
          {skipped.length > 0 && (
            <Card className="shadow-xs border-slate-200">
              <CardContent className="p-5">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                  Skipped ({skipped.length})
                </span>
                <div className="mt-2 divide-y divide-slate-100">
                  {skipped.map((e) => (
                    <div key={e.id} className="flex items-center justify-between py-2 text-xs">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-slate-700 w-8">#{e.token?.tokenNumber}</span>
                        <div className="font-semibold text-slate-900">{e.patient.fullName}</div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={!canManageQueue || statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ tokenId: e.token!.id, status: "WAITING" })}
                        className="h-7 text-xs gap-1"
                      >
                        <Undo2 className="w-3 h-3" />
                        Re-queue
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Completed / cancelled */}
          {done.length > 0 && (
            <Card className="shadow-xs border-slate-200">
              <CardContent className="p-5">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
                  Completed Today ({done.length})
                </span>
                <div className="mt-2 divide-y divide-slate-100">
                  {done.map((e) => (
                    <div key={e.id} className="flex items-center justify-between py-2 text-xs">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-slate-500 w-8">#{e.token?.tokenNumber}</span>
                        <div className="text-slate-600">{e.patient.fullName}</div>
                      </div>
                      {e.token && <TokenStatusBadge status={e.token.status} />}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

const QR_RESULT_STYLES: Record<
  QRVerifyResult["reason"],
  { icon: typeof ShieldCheck; badge: string; card: string; title: string }
> = {
  OK: {
    icon: ShieldCheck,
    badge: "bg-emerald-100 text-emerald-700",
    card: "border-emerald-300 bg-emerald-50/60",
    title: "Valid check-in",
  },
  INVALID: {
    icon: ShieldQuestion,
    badge: "bg-slate-200 text-slate-600",
    card: "border-slate-300 bg-slate-50",
    title: "Invalid QR code",
  },
  EXPIRED: {
    icon: ShieldOff,
    badge: "bg-amber-100 text-amber-700",
    card: "border-amber-300 bg-amber-50/60",
    title: "QR code expired",
  },
  REVOKED: {
    icon: ShieldX,
    badge: "bg-rose-100 text-rose-700",
    card: "border-rose-300 bg-rose-50/60",
    title: "QR code revoked",
  },
};

function QRResultCard({ result }: { result: QRVerifyResult }) {
  const style = QR_RESULT_STYLES[result.reason];
  const Icon = style.icon;
  return (
    <div className={cn("rounded-lg border p-4 space-y-2", style.card)}>
      <div className="flex items-center gap-2">
        <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0", style.badge)}>
          <Icon className="w-4 h-4" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-900">{style.title}</div>
          {!result.valid && result.reason === "INVALID" && (
            <div className="text-[11px] text-slate-500">
              This code doesn&apos;t match any registered OPD visit.
            </div>
          )}
          {!result.valid && result.reason === "EXPIRED" && (
            <div className="text-[11px] text-slate-500">
              This visit&apos;s check-in window has passed. Ask the patient to re-register.
            </div>
          )}
          {!result.valid && result.reason === "REVOKED" && (
            <div className="text-[11px] text-slate-500">
              This QR was revoked (or the visit was cancelled) and can no longer be used.
            </div>
          )}
        </div>
      </div>

      {result.encounter && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-2 border-t border-black/5">
          <div>
            <span className="text-[10px] text-slate-500 block">Patient</span>
            <span className="font-semibold text-slate-900">{result.encounter.patient.fullName}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Token No.</span>
            <span className="font-mono font-semibold text-slate-900">
              {result.encounter.token?.tokenNumber ?? "—"}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Doctor</span>
            <span className="font-semibold text-slate-900">{result.encounter.doctor.fullName}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block">Encounter No.</span>
            <span className="font-mono font-semibold text-slate-900">{result.encounter.encounterNumber}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function QRScanCard() {
  const { toast } = useToast();
  const [manualCode, setManualCode] = React.useState("");
  const [isScanning, setIsScanning] = React.useState(false);
  const [cameraError, setCameraError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<QRVerifyResult | null>(null);

  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const rafRef = React.useRef<number | null>(null);
  const scanFrameRef = React.useRef<(() => void) | null>(null);

  const verifyMutation = useMutation({
    mutationFn: (code: string) => verifyQrCode(code),
    onSuccess: (data) => {
      setResult(data);
      if (data.valid) {
        toast({ title: "QR verified", description: data.encounter?.patient.fullName, variant: "success" });
      }
    },
    onError: (error: ApiError) => {
      toast({ title: "Unable to verify QR code", description: error?.message, variant: "destructive" });
    },
  });

  const stopScanning = React.useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setIsScanning(false);
  }, []);

  // Held in a ref (rather than called by name) so the recursive
  // requestAnimationFrame loop always invokes the latest closure without
  // React's exhaustive-deps flagging self-reference before declaration.
  const scanFrame = React.useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) {
      rafRef.current = requestAnimationFrame(() => scanFrameRef.current?.());
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height);

    if (code?.data) {
      stopScanning();
      verifyMutation.mutate(code.data);
    } else {
      rafRef.current = requestAnimationFrame(() => scanFrameRef.current?.());
    }
  }, [stopScanning, verifyMutation]);

  React.useEffect(() => {
    scanFrameRef.current = scanFrame;
  }, [scanFrame]);

  const startScanning = async () => {
    setCameraError(null);
    setResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsScanning(true);
      rafRef.current = requestAnimationFrame(() => scanFrameRef.current?.());
    } catch {
      setCameraError("Camera unavailable or permission denied. Use manual entry below instead.");
    }
  };

  React.useEffect(() => stopScanning, [stopScanning]);

  const handleManualVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCode.trim()) return;
    setResult(null);
    verifyMutation.mutate(manualCode.trim());
  };

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-5 space-y-4">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Scan &amp; Verify QR</span>

        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 space-y-2">
            <div className="relative aspect-square max-w-xs mx-auto sm:mx-0 rounded-lg overflow-hidden bg-slate-900 flex items-center justify-center">
              <video ref={videoRef} muted playsInline hidden={!isScanning} className="w-full h-full object-cover" />
              <canvas ref={canvasRef} hidden />
              {!isScanning && <QrCode className="w-10 h-10 text-slate-600" />}
            </div>
            <Button
              type="button"
              size="sm"
              variant={isScanning ? "outline" : "default"}
              onClick={isScanning ? stopScanning : startScanning}
              className="gap-1.5 text-xs w-full max-w-xs"
            >
              {isScanning ? <CameraOff className="w-3.5 h-3.5" /> : <Camera className="w-3.5 h-3.5" />}
              {isScanning ? "Stop Camera" : "Start Camera Scan"}
            </Button>
            {cameraError && <p className="text-[11px] text-amber-600 max-w-xs">{cameraError}</p>}
          </div>

          <div className="flex-1 space-y-3">
            <form onSubmit={handleManualVerify} className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-700 block">
                Or enter the code manually
              </label>
              <div className="flex gap-2">
                <input
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  placeholder="QR code value"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
                />
                <Button type="submit" size="sm" disabled={verifyMutation.isPending} className="text-xs shrink-0">
                  {verifyMutation.isPending ? "Verifying..." : "Verify"}
                </Button>
              </div>
            </form>

            {result && <QRResultCard result={result} />}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function QRDisplayCard() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManageQueue = hasPermission("opd.manage_queue");

  const [nameFilter, setNameFilter] = React.useState("");
  const [selected, setSelected] = React.useState<OPDEncounter | null>(null);
  const [confirmRevokeOpen, setConfirmRevokeOpen] = React.useState(false);

  const todayIso = new Date().toISOString().slice(0, 10);

  const encountersQuery = useQuery({
    queryKey: ["opd-encounters-today", todayIso],
    queryFn: () => listEncounters({ visit_date: todayIso }),
  });

  const revokeMutation = useMutation({
    mutationFn: (encounterId: string) => revokeQr(encounterId),
    onSuccess: (encounter) => {
      toast({ title: "QR code revoked", description: encounter.encounterNumber, variant: "success" });
      setSelected(encounter);
      setConfirmRevokeOpen(false);
      queryClient.invalidateQueries({ queryKey: ["opd-encounters-today"] });
    },
    onError: (error: ApiError) => {
      toast({ title: "Unable to revoke QR", description: error?.message, variant: "destructive" });
      setConfirmRevokeOpen(false);
    },
  });

  const filtered = (encountersQuery.data ?? []).filter((e) =>
    nameFilter.trim() ? e.patient.fullName.toLowerCase().includes(nameFilter.trim().toLowerCase()) : true
  );

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-5 space-y-3">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">
          Today&apos;s Registrations — Display QR
        </span>
        <SearchInput
          placeholder="Filter by patient name..."
          onSearchChange={setNameFilter}
          isLoading={encountersQuery.isFetching}
        />

        {filtered.length === 0 ? (
          <p className="text-xs text-slate-400 py-4 text-center">No registrations found for today.</p>
        ) : (
          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
            {filtered.map((e) => (
              <div key={e.id} className="flex items-center justify-between py-2 text-xs">
                <div>
                  <div className="font-semibold text-slate-900">{e.patient.fullName}</div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    {e.encounterNumber} • Token #{e.token?.tokenNumber ?? "—"} • {e.doctor.fullName}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={
                      e.qrStatus === "ACTIVE"
                        ? "text-[10px] bg-emerald-50 text-emerald-700 border-emerald-300"
                        : "text-[10px] bg-rose-50 text-rose-700 border-rose-300"
                    }
                  >
                    {e.qrStatus === "ACTIVE" ? "QR Active" : "QR Revoked"}
                  </Badge>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setSelected(e)}
                    className="h-7 text-xs gap-1"
                  >
                    <QrCode className="w-3 h-3" />
                    Show QR
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent size="sm">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>{selected.patient.fullName}</DialogTitle>
                <DialogDescription>
                  {selected.encounterNumber} • Token #{selected.token?.tokenNumber ?? "—"}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-col items-center gap-3 py-2">
                {selected.qrStatus === "ACTIVE" ? (
                  <QRCodeSVG value={selected.qrCode} size={180} />
                ) : (
                  <div className="w-45 h-45 rounded-lg bg-slate-100 flex flex-col items-center justify-center gap-2 text-slate-400">
                    <ShieldX className="w-8 h-8" />
                    <span className="text-xs font-semibold">Revoked</span>
                  </div>
                )}
                <div className="text-[11px] text-slate-500 text-center">
                  Expires {new Date(selected.qrExpiresAt).toLocaleString()}
                </div>

                {selected.qrStatus === "ACTIVE" && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!canManageQueue}
                    title={canManageQueue ? undefined : "You don't have permission to revoke QR codes"}
                    onClick={() => setConfirmRevokeOpen(true)}
                    className="gap-1.5 text-xs text-destructive border-destructive/30 hover:bg-destructive/5"
                  >
                    <ShieldOff className="w-3.5 h-3.5" />
                    Revoke QR
                  </Button>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmRevokeOpen}
        onOpenChange={setConfirmRevokeOpen}
        title="Revoke this QR code?"
        description="The patient will no longer be able to check in with this QR. This cannot be undone."
        confirmLabel="Revoke"
        variant="destructive"
        isLoading={revokeMutation.isPending}
        onConfirm={() => {
          if (selected) revokeMutation.mutate(selected.id);
        }}
      />
    </Card>
  );
}

function QRTab() {
  return (
    <div className="space-y-4">
      <QRScanCard />
      <QRDisplayCard />
    </div>
  );
}

function OPDPageContent() {
  return (
    <PageContainer>
      <PageHeader
        title="OPD Registration & Queue"
        description="Register OPD visits and manage each doctor's live token queue."
      />

      <Tabs defaultValue="register">
        <TabsList>
          <TabsTrigger value="register">Register Visit</TabsTrigger>
          <TabsTrigger value="queue">Live Queue</TabsTrigger>
          <TabsTrigger value="qr">QR Check-in</TabsTrigger>
        </TabsList>
        <TabsContent value="register">
          <RegistrationTab />
        </TabsContent>
        <TabsContent value="queue">
          <QueueTab />
        </TabsContent>
        <TabsContent value="qr">
          <QRTab />
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}

export default function OPDPage() {
  return (
    <AppShell>
      <OPDPageContent />
    </AppShell>
  );
}
