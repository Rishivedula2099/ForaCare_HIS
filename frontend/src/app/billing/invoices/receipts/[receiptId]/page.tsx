"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getPatient, toPatient } from "@/lib/patient-api";
import { getReceipt } from "@/lib/billing-api";

const RECEIPT_TYPE_LABEL: Record<string, string> = {
  PAYMENT: "Payment Receipt",
  DEPOSIT: "Deposit Receipt",
  REFUND: "Refund Receipt",
};

export default function ReceiptPrintPage() {
  const params = useParams<{ receiptId: string }>();
  const receiptId = params.receiptId;

  const receiptQuery = useQuery({ queryKey: ["billing-receipt", receiptId], queryFn: () => getReceipt(receiptId) });
  const receipt = receiptQuery.data;

  const patientQuery = useQuery({
    queryKey: ["patient", receipt?.patientId],
    queryFn: async () => toPatient(await getPatient(receipt!.patientId)),
    enabled: !!receipt,
  });
  const patient = patientQuery.data;

  if (receiptQuery.isLoading || patientQuery.isLoading) {
    return <p className="p-8 text-sm text-slate-400">Loading...</p>;
  }
  if (!receipt || !patient) {
    return <p className="p-8 text-sm text-destructive">Unable to load this receipt.</p>;
  }

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="print:hidden flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h1 className="text-sm font-bold">{RECEIPT_TYPE_LABEL[receipt.receiptType] ?? "Receipt"}</h1>
        <Button size="sm" className="gap-1.5 text-xs" onClick={() => window.print()}>
          <Printer className="w-3.5 h-3.5" />
          Print
        </Button>
      </div>

      <div className="max-w-md mx-auto p-8 print:p-6">
        <div className="text-center border-b-2 border-slate-900 pb-3 mb-5">
          <h2 className="text-lg font-black">ForaCare Hospital</h2>
          <p className="text-xs text-slate-500">{RECEIPT_TYPE_LABEL[receipt.receiptType] ?? "Receipt"}</p>
        </div>

        <div className="flex items-center justify-between text-xs mb-4">
          <div>
            <span className="text-[11px] text-slate-500 block">Receipt No.</span>
            <span className="font-mono font-bold">{receipt.receiptNumber}</span>
          </div>
          <div className="text-right">
            <span className="text-[11px] text-slate-500 block">Issued</span>
            <span className="font-semibold">{new Date(receipt.issuedAt).toLocaleString()}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm border-t border-slate-200 pt-4">
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
        </div>

        <div className="border-t-2 border-slate-900 mt-5 pt-4 flex items-center justify-between">
          <span className="text-sm font-bold">Amount</span>
          <span className="text-xl font-black">₹{receipt.amount.toFixed(2)}</span>
        </div>

        <p className="text-[10px] text-slate-400 mt-8 text-center">
          This is a system-generated receipt and does not require a signature.
        </p>
      </div>
    </div>
  );
}
