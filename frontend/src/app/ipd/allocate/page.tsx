"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BedDouble,
  Search,
  User as UserIcon,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  RotateCcw,
  ArrowLeft,
  FileText,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { SearchInput } from "@/components/ui/search-input";
import { cn } from "@/lib/utils";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { fromBackendListItem, listPatients } from "@/lib/patient-api";
import { admitPatient, listBeds, listRooms, listWards } from "@/lib/ipd-api";
import { listDoctors } from "@/lib/doctor-api";
import { Patient } from "@/types/patient";
import { ApiError } from "@/types/api";
import {
  ADMISSION_TYPES,
  AdmissionType,
  Bed,
  BED_STATUS_BADGE_CLASS,
  PAYMENT_CATEGORIES,
  PaymentCategory,
  PAYMENT_MODES,
  PaymentMode,
  REFERRAL_SOURCES,
  ReferralSource,
} from "@/types/ipd";

function AllocateBedPageContent() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("ipd.manage_beds");

  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] = React.useState<Patient | null>(null);
  const [wardId, setWardId] = React.useState("");
  const [roomId, setRoomId] = React.useState("");
  const [selectedBed, setSelectedBed] = React.useState<Bed | null>(null);
  const [admissionType, setAdmissionType] = React.useState<AdmissionType>("ELECTIVE");
  const [consultantId, setConsultantId] = React.useState("");
  const [referralSource, setReferralSource] = React.useState<ReferralSource>("SELF");
  const [referralDetail, setReferralDetail] = React.useState("");
  const [paymentCategory, setPaymentCategory] = React.useState<PaymentCategory>("CASH");
  const [depositAmount, setDepositAmount] = React.useState("");
  const [depositPaymentMode, setDepositPaymentMode] = React.useState<PaymentMode>("CASH");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);
  const [confirmedFor, setConfirmedFor] = React.useState<Patient | null>(null);
  const [confirmedAdmissionId, setConfirmedAdmissionId] = React.useState<string | null>(null);

  const doctorsQuery = useQuery({ queryKey: ["ipd-allocate-doctors"], queryFn: () => listDoctors() });
  const activeDoctors = (doctorsQuery.data ?? []).filter((d) => d.isActive);

  const patientSearchQuery = useQuery({
    queryKey: ["ipd-allocate-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  const wardsQuery = useQuery({ queryKey: ["ipd-wards"], queryFn: listWards });
  const activeWards = (wardsQuery.data ?? []).filter((w) => w.isActive);

  const roomsQuery = useQuery({
    queryKey: ["ipd-rooms", wardId],
    queryFn: () => listRooms({ ward_id: wardId }),
    enabled: !!wardId,
  });
  const activeRooms = (roomsQuery.data ?? []).filter((r) => r.isActive);

  const bedsQuery = useQuery({
    queryKey: ["ipd-allocate-beds", roomId],
    queryFn: () => listBeds({ room_id: roomId }),
    enabled: !!roomId,
  });
  const allocatableBeds = (bedsQuery.data ?? []).filter(
    (b) => b.isActive && (b.status === "AVAILABLE" || b.status === "RESERVED")
  );

  const admitMutation = useMutation({
    mutationFn: () =>
      admitPatient({
        patient_id: selectedPatient!.id,
        bed_id: selectedBed!.id,
        admitting_doctor_id: consultantId || null,
        admission_type: admissionType,
        referral_source: referralSource,
        referral_detail: referralDetail.trim() || null,
        payment_category: paymentCategory,
        notes: notes.trim() || null,
        deposit_amount: depositAmount ? Number(depositAmount) : null,
        deposit_payment_mode: depositPaymentMode,
      }),
    onSuccess: (admission) => {
      toast({ title: "Bed allocated", description: selectedPatient?.fullName, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      setConfirmedFor(selectedPatient);
      setConfirmedAdmissionId(admission.id);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to allocate this bed. Please try a different bed.");
      // A lost race or an already-admitted patient both mean the currently
      // selected bed can no longer be trusted - drop back to step 4 with a
      // fresh bed list rather than silently retrying.
      queryClient.invalidateQueries({ queryKey: ["ipd-allocate-beds", roomId] });
      setSelectedBed(null);
    },
  });

  const handleSelectPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setPatientQuery("");
  };

  const handleWardChange = (value: string) => {
    setWardId(value);
    setRoomId("");
    setSelectedBed(null);
  };

  const handleRoomChange = (value: string) => {
    setRoomId(value);
    setSelectedBed(null);
  };

  const handleConfirm = () => {
    setFormError(null);
    admitMutation.mutate();
  };

  const resetForAnother = () => {
    setConfirmedFor(null);
    setConfirmedAdmissionId(null);
    setSelectedPatient(null);
    setWardId("");
    setRoomId("");
    setSelectedBed(null);
    setAdmissionType("ELECTIVE");
    setConsultantId("");
    setReferralSource("SELF");
    setReferralDetail("");
    setPaymentCategory("CASH");
    setDepositAmount("");
    setDepositPaymentMode("CASH");
    setNotes("");
    setFormError(null);
  };

  const wardOptions = activeWards.map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));
  const roomOptions = activeRooms.map((r) => ({ value: r.id, label: r.roomNumber }));

  if (!canManage) {
    return (
      <PageContainer>
        <PageHeader title="Allocate Bed" description="Admit a patient into a bed through a guided, step-by-step flow." />
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">You don&apos;t have permission to allocate beds.</p>
            <p className="text-amber-700 mt-0.5">Contact a Hospital Admin if you believe you should have access.</p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
          <Link href="/ipd">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Bed Board
          </Link>
        </Button>
      </PageContainer>
    );
  }

  if (confirmedFor) {
    return (
      <PageContainer>
        <PageHeader title="Allocate Bed" description="Admit a patient into a bed through a guided, step-by-step flow." />
        <Card className="border-emerald-200 bg-emerald-50/40 shadow-xs">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Bed allocated successfully</h3>
                <p className="text-xs text-slate-500">{confirmedFor.fullName}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" size="sm" onClick={resetForAnother} className="gap-1.5 text-xs">
                <RotateCcw className="w-3.5 h-3.5" />
                Allocate Another Bed
              </Button>
              {confirmedAdmissionId && (
                <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
                  <Link href={`/ipd/admissions/${confirmedAdmissionId}`}>
                    <FileText className="w-3.5 h-3.5" />
                    View Admission
                  </Link>
                </Button>
              )}
              <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
                <Link href="/ipd">
                  <BedDouble className="w-3.5 h-3.5" />
                  View Bed Board
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Allocate Bed"
        description="Admit a patient into a bed through a guided, step-by-step flow."
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/ipd">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Bed Board
            </Link>
          </Button>
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-5">
          {/* Step 1: Patient */}
          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-slate-700 block">1. Select Patient</label>
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
                <Button type="button" variant="ghost" size="sm" onClick={() => setSelectedPatient(null)} className="text-xs h-7">
                  Change
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <SearchInput
                  placeholder="Search by patient UID, MRN, or name..."
                  onSearchChange={setPatientQuery}
                  isLoading={patientSearchQuery.isFetching}
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

          {/* Step 2: Ward */}
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">2. Select Ward</label>
            <Select
              options={wardOptions}
              value={wardId}
              onChange={handleWardChange}
              placeholder="Select a ward"
              disabled={!selectedPatient}
            />
          </div>

          {/* Step 3: Room */}
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">3. Select Room</label>
            <Select
              options={roomOptions}
              value={roomId}
              onChange={handleRoomChange}
              placeholder={wardId ? "Select a room" : "Select a ward first"}
              disabled={!wardId}
            />
            {wardId && !roomsQuery.isLoading && roomOptions.length === 0 && (
              <p className="text-[11px] text-amber-600 mt-1">No active rooms in this ward.</p>
            )}
          </div>

          {/* Step 4: Bed */}
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">4. Select Bed</label>
            {!roomId ? (
              <p className="text-xs text-slate-400">Select a room first.</p>
            ) : bedsQuery.isLoading ? (
              <p className="text-xs text-slate-400">Loading beds...</p>
            ) : allocatableBeds.length === 0 ? (
              <p className="text-[11px] text-amber-600">No available or reserved beds in this room.</p>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                {allocatableBeds.map((bed) => (
                  <button
                    key={bed.id}
                    type="button"
                    onClick={() => setSelectedBed(bed)}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-lg border p-2.5 text-center transition-shadow hover:shadow-sm",
                      BED_STATUS_BADGE_CLASS[bed.status],
                      selectedBed?.id === bed.id && "ring-2 ring-primary ring-offset-1"
                    )}
                  >
                    <BedDouble className="w-3.5 h-3.5" />
                    <span className="text-xs font-bold">{bed.bedNumber}</span>
                    <span className="text-[9px] font-semibold uppercase tracking-wide">{bed.status}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Admission Type</label>
              <Select
                options={ADMISSION_TYPES.map((t) => ({ value: t.value, label: t.label }))}
                value={admissionType}
                onChange={(value) => setAdmissionType(value as AdmissionType)}
                placeholder="Select admission type"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Consultant (optional)</label>
              <Select
                options={activeDoctors.map((d) => ({ value: d.id, label: `${d.fullName} (${d.specialization})` }))}
                value={consultantId}
                onChange={setConsultantId}
                placeholder="Select a consultant"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Referral</label>
              <Select
                options={REFERRAL_SOURCES.map((r) => ({ value: r.value, label: r.label }))}
                value={referralSource}
                onChange={(value) => setReferralSource(value as ReferralSource)}
                placeholder="Select referral source"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Referral Detail (optional)</label>
              <input
                type="text"
                value={referralDetail}
                onChange={(e) => setReferralDetail(e.target.value)}
                placeholder="Referring doctor / hospital name"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Payment Category</label>
              <Select
                options={PAYMENT_CATEGORIES.map((p) => ({ value: p.value, label: p.label }))}
                value={paymentCategory}
                onChange={(value) => setPaymentCategory(value as PaymentCategory)}
                placeholder="Select payment category"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Deposit Amount (optional)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                placeholder="0.00"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Deposit Mode</label>
              <Select
                options={PAYMENT_MODES.map((m) => ({ value: m.value, label: m.label }))}
                value={depositPaymentMode}
                onChange={(value) => setDepositPaymentMode(value as PaymentMode)}
                placeholder="Select payment mode"
                disabled={!depositAmount}
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={1}
              placeholder="Any relevant admission notes"
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {/* Step 5: Confirmation */}
          <div className="border-t border-slate-100 pt-4 space-y-3">
            <label className="text-[11px] font-semibold text-slate-700 block">5. Allocation Confirmation</label>
            {selectedPatient && selectedBed ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 block">Patient</span>
                  <span className="font-semibold text-slate-900">{selectedPatient.fullName}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Ward / Room</span>
                  <span className="font-semibold text-slate-900">
                    {selectedBed.ward.name} / {selectedBed.room.roomNumber}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Bed</span>
                  <span className="font-mono font-semibold text-slate-900">{selectedBed.bedNumber}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Admission Type</span>
                  <span className="font-semibold text-slate-900">
                    {ADMISSION_TYPES.find((t) => t.value === admissionType)?.label}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Complete steps 1–4 to review the allocation here.</p>
            )}

            {formError && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                type="button"
                size="sm"
                className="gap-1.5 text-xs"
                disabled={!selectedPatient || !selectedBed || admitMutation.isPending}
                onClick={handleConfirm}
              >
                {admitMutation.isPending ? "Allocating..." : "Confirm Allocation"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  );
}

export default function AllocateBedPage() {
  return (
    <AppShell>
      <AllocateBedPageContent />
    </AppShell>
  );
}
