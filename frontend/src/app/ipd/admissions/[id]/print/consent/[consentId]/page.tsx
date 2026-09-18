"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getPatient, toPatient } from "@/lib/patient-api";
import { getAdmission, listConsents } from "@/lib/ipd-api";
import { CONSENT_TYPES } from "@/types/ipd";

function labelFor(options: readonly { value: string; label: string }[], value: string) {
  return options.find((o) => o.value === value)?.label ?? value;
}

export default function ConsentPrintPage() {
  const params = useParams<{ id: string; consentId: string }>();
  const admissionId = params.id;
  const consentId = params.consentId;

  const admissionQuery = useQuery({ queryKey: ["ipd-admission", admissionId], queryFn: () => getAdmission(admissionId) });
  const admission = admissionQuery.data;

  const patientQuery = useQuery({
    queryKey: ["patient", admission?.patientId],
    queryFn: async () => toPatient(await getPatient(admission!.patientId)),
    enabled: !!admission,
  });
  const patient = patientQuery.data;

  const consentsQuery = useQuery({
    queryKey: ["ipd-consents", admissionId],
    queryFn: () => listConsents(admissionId),
  });
  const consent = consentsQuery.data?.find((c) => c.id === consentId);

  if (admissionQuery.isLoading || patientQuery.isLoading || consentsQuery.isLoading) {
    return <p className="p-8 text-sm text-slate-400">Loading...</p>;
  }
  if (!admission || !patient || !consent) {
    return <p className="p-8 text-sm text-destructive">Unable to load this consent record.</p>;
  }

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="print:hidden flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h1 className="text-sm font-bold">Consent Record</h1>
        <Button size="sm" className="gap-1.5 text-xs" onClick={() => window.print()}>
          <Printer className="w-3.5 h-3.5" />
          Print
        </Button>
      </div>

      <div className="max-w-2xl mx-auto p-8 print:p-6 text-sm">
        <div className="text-center border-b-2 border-slate-900 pb-3 mb-5">
          <h2 className="text-lg font-black">ForaCare Hospital</h2>
          <p className="text-xs text-slate-500">{labelFor(CONSENT_TYPES, consent.consentType)}</p>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <div>
            <span className="text-[11px] text-slate-500 block">Patient</span>
            <span className="font-semibold">{patient.fullName}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">UID / MRN</span>
            <span className="font-mono font-semibold">
              {patient.uid} / {patient.mrn}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Admission Number</span>
            <span className="font-mono font-semibold">{admission.admissionNumber}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Recorded At</span>
            <span className="font-semibold">{new Date(consent.recordedAt).toLocaleString()}</span>
          </div>
        </div>

        <div className="mt-6 border border-slate-300 rounded-md p-4 space-y-3">
          <p className="leading-relaxed text-slate-700">
            I, <span className="font-bold">{consent.givenByName}</span>
            {consent.relationshipToPatient ? ` (${consent.relationshipToPatient})` : ""}, hereby{" "}
            <span className="font-bold">{consent.consentGiven ? "GIVE" : "DECLINE"}</span> consent for{" "}
            <span className="font-bold">{labelFor(CONSENT_TYPES, consent.consentType).toLowerCase()}</span> for the
            above-named patient.
          </p>
          {consent.notes && (
            <div>
              <span className="text-[11px] text-slate-500 block">Notes</span>
              <span>{consent.notes}</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-8 mt-10 text-xs">
          <div>
            <div className="border-t border-slate-400 pt-1">Signature ({consent.givenByName})</div>
          </div>
          <div>
            <div className="border-t border-slate-400 pt-1">Witness / Staff Signature</div>
          </div>
        </div>
      </div>
    </div>
  );
}
