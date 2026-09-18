"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BedDouble,
  Building2,
  DoorOpen,
  Search,
  User as UserIcon,
  ArrowRightLeft,
  LogOut,
  ShieldAlert,
  ClipboardPlus,
  Wrench,
  FileText,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SearchInput } from "@/components/ui/search-input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { cn } from "@/lib/utils";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { fromBackendListItem, listPatients } from "@/lib/patient-api";
import {
  admitPatient,
  dischargeAdmission,
  listBeds,
  listWards,
  transferAdmission,
  updateBedStatus,
} from "@/lib/ipd-api";
import { Patient } from "@/types/patient";
import { ApiError } from "@/types/api";
import {
  ADMISSION_TYPES,
  AdmissionType,
  Bed,
  BED_STATUS_BADGE_CLASS,
  BED_STATUS_TRANSITIONS,
  BED_STATUSES,
  BedStatus,
} from "@/types/ipd";

function BedTile({ bed, onClick, canChangeStatus }: { bed: Bed; onClick: () => void; canChangeStatus: boolean }) {
  const isManualStatus = bed.status !== "AVAILABLE" && bed.status !== "OCCUPIED";
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-shadow hover:shadow-sm",
        BED_STATUS_BADGE_CLASS[bed.status]
      )}
    >
      <div className="flex items-center gap-1.5 w-full">
        <BedDouble className="w-3.5 h-3.5 shrink-0" />
        <span className="text-xs font-bold">{bed.bedNumber}</span>
        {isManualStatus && canChangeStatus && (
          <Wrench className="w-3 h-3 shrink-0 ml-auto opacity-60" aria-label="Click to change status" />
        )}
      </div>
      <span className="text-[10px] font-semibold uppercase tracking-wide">{bed.status}</span>
      {bed.currentOccupant && (
        <span className="text-[11px] font-medium truncate w-full" title={bed.currentOccupant.patient.fullName}>
          {bed.currentOccupant.patient.fullName}
        </span>
      )}
    </button>
  );
}

function AdmitPatientDialog({
  bed,
  open,
  onOpenChange,
}: {
  bed: Bed | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] = React.useState<Patient | null>(null);
  const [admissionType, setAdmissionType] = React.useState<AdmissionType>("ELECTIVE");
  const [notes, setNotes] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);

  const patientSearchQuery = useQuery({
    queryKey: ["ipd-patient-search", patientQuery],
    queryFn: async () => (await listPatients({ name: patientQuery })).map(fromBackendListItem),
    enabled: patientQuery.trim().length >= 2 && !selectedPatient,
  });

  const admitMutation = useMutation({
    mutationFn: () =>
      admitPatient({
        patient_id: selectedPatient!.id,
        bed_id: bed!.id,
        admission_type: admissionType,
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Patient admitted", description: selectedPatient?.fullName, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to admit this patient."),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!selectedPatient) {
      setFormError("Please search for and select a patient.");
      return;
    }
    admitMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Admit Patient</DialogTitle>
          <DialogDescription>
            {bed ? `Assign a patient to bed ${bed.bedNumber} (${bed.room.roomNumber}, ${bed.ward.name}).` : ""}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-slate-700 block">Search Patient</label>
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
                          onClick={() => {
                            setSelectedPatient(patient);
                            setPatientQuery("");
                          }}
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
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Any relevant admission notes"
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={admitMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={admitMutation.isPending}>
              {admitMutation.isPending ? "Admitting..." : "Admit Patient"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function OccupiedBedDialog({
  bed,
  open,
  onOpenChange,
  canManage,
}: {
  bed: Bed | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canManage: boolean;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [confirmDischargeOpen, setConfirmDischargeOpen] = React.useState(false);
  const [confirmTransferOpen, setConfirmTransferOpen] = React.useState(false);
  const [transferBedId, setTransferBedId] = React.useState("");
  const [transferReason, setTransferReason] = React.useState("");
  const [actionError, setActionError] = React.useState<string | null>(null);

  const availableBedsQuery = useQuery({
    queryKey: ["ipd-beds", "AVAILABLE"],
    queryFn: () => listBeds({ status: "AVAILABLE" }),
    enabled: open && canManage,
  });
  // Excludes this bed defensively - it's already OCCUPIED so the AVAILABLE
  // filter above rules it out server-side, but a stale cache shouldn't be
  // able to offer "transfer to the bed the patient is already in".
  const destinationBeds = (availableBedsQuery.data ?? []).filter((b) => b.id !== bed?.id);
  const destinationBed = destinationBeds.find((b) => b.id === transferBedId) ?? null;

  const dischargeMutation = useMutation({
    mutationFn: () => dischargeAdmission(bed!.currentOccupant!.admissionId, { discharge_type: "NORMAL" }),
    onSuccess: () => {
      toast({ title: "Patient discharged", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      setConfirmDischargeOpen(false);
      onOpenChange(false);
    },
    onError: (error: ApiError) => {
      setActionError(error?.message || "Unable to discharge this patient.");
      setConfirmDischargeOpen(false);
    },
  });

  const transferMutation = useMutation({
    mutationFn: () =>
      transferAdmission(bed!.currentOccupant!.admissionId, {
        to_bed_id: transferBedId,
        reason: transferReason.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Patient transferred", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      setConfirmTransferOpen(false);
      onOpenChange(false);
    },
    onError: (error: ApiError) => {
      // The destination bed may have just been taken by someone else (or
      // put into maintenance) between selecting it and confirming - drop
      // back to the picker with a fresh bed list rather than letting the
      // user retry against a bed that's no longer available.
      setActionError(error?.message || "Unable to transfer this patient. Please choose a different bed.");
      queryClient.invalidateQueries({ queryKey: ["ipd-beds", "AVAILABLE"] });
      setConfirmTransferOpen(false);
      setTransferBedId("");
    },
  });

  if (!bed?.currentOccupant) return null;
  const occupant = bed.currentOccupant;
  const bedOptions = destinationBeds.map((b) => ({
    value: b.id,
    label: `${b.bedNumber} — ${b.room.roomNumber}, ${b.ward.name}`,
  }));

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{occupant.patient.fullName}</DialogTitle>
            <DialogDescription>
              {occupant.admissionNumber} • Bed {bed.bedNumber} ({bed.room.roomNumber}, {bed.ward.name})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 rounded-md p-3">
              <div>
                <span className="text-[10px] text-slate-500 block">UID / MRN</span>
                <span className="font-mono font-semibold text-slate-900">
                  {occupant.patient.uid} / {occupant.patient.mrn}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Admitted</span>
                <span className="font-semibold text-slate-900">
                  {new Date(occupant.admittedAt).toLocaleString()}
                </span>
              </div>
            </div>

            {canManage && (
              <div className="space-y-2 border-t border-slate-100 pt-3">
                <label className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
                  <ArrowRightLeft className="w-3.5 h-3.5" />
                  Transfer to another bed
                </label>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 rounded-md p-2.5">
                  <div>
                    <span className="text-[10px] text-slate-500 block">Source Bed</span>
                    <span className="font-mono font-semibold text-slate-900">
                      {bed.bedNumber} — {bed.room.roomNumber}, {bed.ward.name}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Destination Bed</span>
                    <span className="font-mono font-semibold text-slate-900">
                      {destinationBed ? `${destinationBed.bedNumber} — ${destinationBed.room.roomNumber}, ${destinationBed.ward.name}` : "Not selected"}
                    </span>
                  </div>
                </div>

                <Select
                  options={bedOptions}
                  value={transferBedId}
                  onChange={setTransferBedId}
                  placeholder={
                    availableBedsQuery.isLoading
                      ? "Loading available beds..."
                      : bedOptions.length === 0
                        ? "No available beds"
                        : "Select destination bed"
                  }
                  disabled={availableBedsQuery.isLoading || bedOptions.length === 0}
                />
                <Input
                  value={transferReason}
                  onChange={(e) => setTransferReason(e.target.value)}
                  placeholder="Reason (optional)"
                  className="text-xs"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-xs"
                  disabled={!transferBedId || transferMutation.isPending}
                  onClick={() => setConfirmTransferOpen(true)}
                >
                  Transfer Patient
                </Button>
              </div>
            )}

            {actionError && (
              <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
                {actionError}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" className="gap-1.5 mr-auto" asChild>
              <Link href={`/ipd/admissions/${occupant.admissionId}`}>
                <FileText className="w-3.5 h-3.5" />
                View Admission
              </Link>
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
              Close
            </Button>
            {canManage && (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                className="gap-1.5"
                onClick={() => setConfirmDischargeOpen(true)}
              >
                <LogOut className="w-3.5 h-3.5" />
                Discharge
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmDischargeOpen}
        onOpenChange={setConfirmDischargeOpen}
        title="Discharge this patient?"
        description={`This frees bed ${bed.bedNumber} and marks the admission as discharged.`}
        confirmLabel="Discharge"
        variant="destructive"
        isLoading={dischargeMutation.isPending}
        onConfirm={() => dischargeMutation.mutate()}
      />

      <ConfirmDialog
        open={confirmTransferOpen}
        onOpenChange={setConfirmTransferOpen}
        title="Transfer this patient?"
        description={
          destinationBed
            ? `Move ${occupant.patient.fullName} from bed ${bed.bedNumber} (${bed.room.roomNumber}, ${bed.ward.name}) to bed ${destinationBed.bedNumber} (${destinationBed.room.roomNumber}, ${destinationBed.ward.name}).`
            : ""
        }
        confirmLabel="Transfer"
        variant="warning"
        isLoading={transferMutation.isPending}
        onConfirm={() => transferMutation.mutate()}
      />
    </>
  );
}

function ChangeBedStatusDialog({
  bed,
  open,
  onOpenChange,
}: {
  bed: Bed | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [nextStatus, setNextStatus] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);

  const statusMutation = useMutation({
    mutationFn: () => updateBedStatus(bed!.id, nextStatus as BedStatus),
    onSuccess: () => {
      toast({ title: "Bed status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-beds"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update this bed's status."),
  });

  if (!bed) return null;
  const options = BED_STATUS_TRANSITIONS[bed.status].map((status) => ({
    value: status,
    label: BED_STATUSES.find((s) => s.value === status)?.label ?? status,
  }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Change Bed Status</DialogTitle>
          <DialogDescription>
            Bed {bed.bedNumber} ({bed.room.roomNumber}, {bed.ward.name}) is currently{" "}
            <span className="font-semibold">{bed.status}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {options.length === 0 ? (
            <p className="text-xs text-slate-400">This bed has no available manual status changes.</p>
          ) : (
            <Select
              options={options}
              value={nextStatus}
              onChange={setNextStatus}
              placeholder="Select a new status"
            />
          )}

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={statusMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!nextStatus || statusMutation.isPending}
            onClick={() => statusMutation.mutate()}
          >
            {statusMutation.isPending ? "Updating..." : "Update Status"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function BedBoardPageContent() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("ipd.manage_beds");

  const [wardFilter, setWardFilter] = React.useState("ALL");
  const [statusFilter, setStatusFilter] = React.useState("ALL");
  const [admitDialogBed, setAdmitDialogBed] = React.useState<Bed | null>(null);
  const [occupiedDialogBed, setOccupiedDialogBed] = React.useState<Bed | null>(null);
  const [statusDialogBed, setStatusDialogBed] = React.useState<Bed | null>(null);

  const wardsQuery = useQuery({ queryKey: ["ipd-wards"], queryFn: listWards });
  const activeWards = (wardsQuery.data ?? []).filter((w) => w.isActive);

  const bedsQuery = useQuery({
    queryKey: ["ipd-beds", wardFilter, statusFilter],
    queryFn: () =>
      listBeds({
        ward_id: wardFilter !== "ALL" ? wardFilter : undefined,
        status: statusFilter !== "ALL" ? (statusFilter as BedStatus) : undefined,
      }),
  });

  const bedsByRoom = React.useMemo(() => {
    const groups = new Map<string, { room: Bed["room"]; beds: Bed[] }>();
    for (const bed of bedsQuery.data ?? []) {
      const existing = groups.get(bed.roomId);
      if (existing) {
        existing.beds.push(bed);
      } else {
        groups.set(bed.roomId, { room: bed.room, beds: [bed] });
      }
    }
    return Array.from(groups.values()).sort((a, b) => a.room.roomNumber.localeCompare(b.room.roomNumber));
  }, [bedsQuery.data]);

  const wardOptions = [
    { value: "ALL", label: "All Wards" },
    ...activeWards.map((w) => ({ value: w.id, label: `${w.name} (${w.code})` })),
  ];
  const statusOptions = [{ value: "ALL", label: "All Statuses" }, ...BED_STATUSES];

  const handleBedClick = (bed: Bed) => {
    if (bed.status === "AVAILABLE") {
      if (canManage) setAdmitDialogBed(bed);
      return;
    }
    if (bed.status === "OCCUPIED" && bed.currentOccupant) {
      setOccupiedDialogBed(bed);
      return;
    }
    // RESERVED / CLEANING / MAINTENANCE / BLOCKED - the only way to move a
    // bed out of these is a manual status change (P4-B02).
    if (canManage) setStatusDialogBed(bed);
  };

  return (
    <PageContainer>
      <PageHeader
        title="IPD Bed Board"
        description="Live occupancy across all wards and rooms."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd/wards">
                <Building2 className="w-3.5 h-3.5" />
                Wards
              </Link>
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd/rooms">
                <DoorOpen className="w-3.5 h-3.5" />
                Rooms
              </Link>
            </Button>
            {canManage && (
              <Button size="sm" className="gap-1.5 text-xs" asChild>
                <Link href="/ipd/allocate">
                  <ClipboardPlus className="w-3.5 h-3.5" />
                  Allocate Bed
                </Link>
              </Button>
            )}
          </div>
        }
      />

      {!canManage && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <span>You have read-only access to the bed board. Contact a Hospital Admin for admit/transfer/discharge access.</span>
        </div>
      )}

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="w-full sm:w-64">
              <Select options={wardOptions} value={wardFilter} onChange={setWardFilter} placeholder="Filter by ward" />
            </div>
            <div className="w-full sm:w-56">
              <Select options={statusOptions} value={statusFilter} onChange={setStatusFilter} placeholder="Filter by status" />
            </div>
          </div>

          {bedsQuery.isLoading ? (
            <p className="text-xs text-slate-400 py-8 text-center">Loading bed board...</p>
          ) : bedsByRoom.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">No beds match the current filters.</p>
          ) : (
            <div className="space-y-5">
              {bedsByRoom.map(({ room, beds: roomBeds }) => (
                <div key={room.id}>
                  <div className="flex items-center gap-2 mb-2">
                    <DoorOpen className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs font-bold text-slate-700">
                      {room.roomNumber} — {room.ward.name}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                    {roomBeds.map((bed) => (
                      <BedTile key={bed.id} bed={bed} onClick={() => handleBedClick(bed)} canChangeStatus={canManage} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AdmitPatientDialog
        key={admitDialogBed?.id ?? "admit-dialog-empty"}
        bed={admitDialogBed}
        open={!!admitDialogBed}
        onOpenChange={(open) => !open && setAdmitDialogBed(null)}
      />
      <OccupiedBedDialog
        key={occupiedDialogBed?.currentOccupant?.admissionId ?? "occupied-dialog-empty"}
        bed={occupiedDialogBed}
        open={!!occupiedDialogBed}
        onOpenChange={(open) => !open && setOccupiedDialogBed(null)}
        canManage={canManage}
      />
      <ChangeBedStatusDialog
        key={statusDialogBed?.id ?? "status-dialog-empty"}
        bed={statusDialogBed}
        open={!!statusDialogBed}
        onOpenChange={(open) => !open && setStatusDialogBed(null)}
      />
    </PageContainer>
  );
}

export default function IpdBedBoardPage() {
  return (
    <AppShell>
      <BedBoardPageContent />
    </AppShell>
  );
}
