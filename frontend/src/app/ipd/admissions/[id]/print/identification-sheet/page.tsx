"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getPatient, toPatient } from "@/lib/patient-api";
import { getAdmission } from "@/lib/ipd-api";
import { ADMISSION_TYPES, PAYMENT_CATEGORIES, REFERRAL_SOURCES } from "@/types/ipd";

function labelFor(options: readonly { value: string; label: string }[], value: string) {
  return options.find((o) => o.value === value)?.label ?? value;
}

export default function IdentificationSheetPage() {
  const params = useParams<{ id: string }>();
  const admissionId = params.id;

  const admissionQuery = useQuery({ queryKey: ["ipd-admission", admissionId], queryFn: () => getAdmission(admissionId) });
  const admission = admissionQuery.data;

  const patientQuery = useQuery({
    queryKey: ["patient", admission?.patientId],
    queryFn: async () => toPatient(await getPatient(admission!.patientId)),
    enabled: !!admission,
  });
  const patient = patientQuery.data;

  if (admissionQuery.isLoading || patientQuery.isLoading) {
    return <p className="p-8 text-sm text-slate-400">Loading...</p>;
  }
  if (!admission || !patient) {
    return <p className="p-8 text-sm text-destructive">Unable to load this admission.</p>;
  }

  const bed = admission.bedAssignments.find((a) => a.status === "ACTIVE")?.bed;

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="print:hidden flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h1 className="text-sm font-bold">Identification Sheet</h1>
        <Button size="sm" className="gap-1.5 text-xs" onClick={() => window.print()}>
          <Printer className="w-3.5 h-3.5" />
          Print
        </Button>
      </div>

      <div className="max-w-2xl mx-auto p-8 print:p-6">
        <div className="flex items-center justify-between border-b-2 border-slate-900 pb-3 mb-5">
          <div>
            <h2 className="text-lg font-black">ForaCare Hospital</h2>
            <p className="text-xs text-slate-500">Patient Identification Sheet</p>
          </div>
          <div className="text-right text-xs">
            <div className="font-mono font-bold">{admission.admissionNumber}</div>
            <div className="text-slate-500">{new Date(admission.admittedAt).toLocaleDateString()}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div className="col-span-2">
            <span className="text-[11px] text-slate-500 block">Patient Name</span>
            <span className="font-bold text-base">{patient.fullName}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">UID</span>
            <span className="font-mono font-semibold">{patient.uid}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">MRN</span>
            <span className="font-mono font-semibold">{patient.mrn}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Gender / DOB</span>
            <span className="font-semibold">
              {patient.gender}, {patient.dob}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Age</span>
            <span className="font-semibold">{patient.ageYears} yrs</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Blood Group</span>
            <span className="font-semibold">{patient.bloodGroup || "Not recorded"}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Mobile</span>
            <span className="font-semibold">{patient.mobile}</span>
          </div>
          <div className="col-span-2">
            <span className="text-[11px] text-slate-500 block">Address</span>
            <span className="font-semibold">
              {[patient.address?.street, patient.address?.city, patient.address?.state, patient.address?.pincode]
                .filter(Boolean)
                .join(", ") || "Not recorded"}
            </span>
          </div>

          <div className="col-span-2 border-t border-slate-200 mt-2 pt-3" />

          <div>
            <span className="text-[11px] text-slate-500 block">Admission Number</span>
            <span className="font-mono font-semibold">{admission.admissionNumber}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Admission Type</span>
            <span className="font-semibold">{labelFor(ADMISSION_TYPES, admission.admissionType)}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Bed</span>
            <span className="font-semibold">
              {bed ? `${bed.bedNumber} — ${bed.room.roomNumber}, ${bed.ward.name}` : "Not assigned"}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Referral</span>
            <span className="font-semibold">{labelFor(REFERRAL_SOURCES, admission.referralSource)}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Payment Category</span>
            <span className="font-semibold">{labelFor(PAYMENT_CATEGORIES, admission.paymentCategory)}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Admitted At</span>
            <span className="font-semibold">{new Date(admission.admittedAt).toLocaleString()}</span>
          </div>

          {patient.guardian?.name && (
            <>
              <div className="col-span-2 border-t border-slate-200 mt-2 pt-3" />
              <div>
                <span className="text-[11px] text-slate-500 block">Guardian / Emergency Contact</span>
                <span className="font-semibold">{patient.guardian.name}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block">Guardian Phone</span>
                <span className="font-semibold">{patient.guardian.phone || "—"}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
