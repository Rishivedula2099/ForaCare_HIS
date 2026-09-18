"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getPatient, toPatient } from "@/lib/patient-api";
import { getAdmission } from "@/lib/ipd-api";

const LABEL_COUNT = 12;

export default function AdmissionLabelsPage() {
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
        <h1 className="text-sm font-bold">Admission Labels</h1>
        <Button size="sm" className="gap-1.5 text-xs" onClick={() => window.print()}>
          <Printer className="w-3.5 h-3.5" />
          Print Sheet
        </Button>
      </div>

      <div className="max-w-3xl mx-auto p-6 print:p-2">
        <div className="grid grid-cols-2 gap-3 print:gap-2">
          {Array.from({ length: LABEL_COUNT }).map((_, i) => (
            <div
              key={i}
              className="border border-dashed border-slate-400 rounded-md p-3 text-xs leading-tight print:break-inside-avoid"
            >
              <div className="font-black text-sm truncate">{patient.fullName}</div>
              <div className="font-mono">
                {patient.uid} • {patient.mrn}
              </div>
              <div>
                {patient.gender}, {patient.dob}
              </div>
              <div className="font-semibold mt-1">
                ADM {admission.admissionNumber} — Bed {bed?.bedNumber ?? "—"}
              </div>
              <div className="text-slate-500">
                {bed ? `${bed.room.roomNumber}, ${bed.ward.name}` : "Not assigned"}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
