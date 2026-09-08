"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Ticket, PlusCircle, Printer, Users, Copy, Check, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Patient } from "@/types/patient";

interface RegistrationSuccessDialogProps {
  patient: Patient | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRegisterAnother: () => void;
}

export function RegistrationSuccessDialog({
  patient,
  open,
  onOpenChange,
  onRegisterAnother,
}: RegistrationSuccessDialogProps) {
  const router = useRouter();
  const [copied, setCopied] = React.useState(false);

  if (!patient) return null;

  const handleCopyUid = () => {
    navigator.clipboard.writeText(patient.uid);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrintCard = () => {
    window.print();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader className="text-center sm:text-left">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-slate-900">
                Patient Registered Successfully
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-500">
                Hospital master record created and indexed. Patient UID generated.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Main Identifier Card */}
          <div className="rounded-xl border border-teal-200 bg-gradient-to-br from-teal-50 to-slate-50 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                  Hospital Patient UID
                </span>
                <div className="text-xl font-extrabold text-slate-900 font-mono tracking-tight flex items-center gap-2">
                  {patient.uid}
                  <button
                    type="button"
                    onClick={handleCopyUid}
                    className="p-1 text-slate-400 hover:text-slate-700 transition-colors"
                    title="Copy UID"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  MRN
                </span>
                <div className="text-sm font-semibold font-mono text-slate-700">
                  {patient.mrn}
                </div>
              </div>
            </div>

            {/* Demographics Overview */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-teal-100/80 text-xs">
              <div>
                <span className="text-[10px] text-slate-500 block">Name</span>
                <span className="font-semibold text-slate-900">{patient.fullName}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Gender &amp; Age</span>
                <span className="font-semibold text-slate-900">
                  {patient.gender} • {patient.ageYears} yrs
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Blood Group</span>
                <span className="font-semibold text-slate-900">
                  {patient.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Mobile</span>
                <span className="font-semibold text-slate-900 font-mono">{patient.mobile}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">City</span>
                <span className="font-semibold text-slate-900">{patient.address.city}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">ABHA Status</span>
                <Badge
                  variant="outline"
                  className={
                    patient.abha.status === "VERIFIED"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-300 text-[10px]"
                      : "bg-slate-100 text-slate-600 text-[10px]"
                  }
                >
                  {patient.abha.status}
                </Badge>
              </div>
            </div>
          </div>

          {/* Quick Flow Actions */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
              Immediate Clinical Workflows
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  onOpenChange(false);
                  router.push(`/opd?patientUid=${encodeURIComponent(patient.uid)}`);
                }}
                className="justify-start gap-2 h-auto py-2.5 px-3 bg-white border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 text-left"
              >
                <div className="w-7 h-7 rounded-lg bg-teal-100 text-teal-800 flex items-center justify-center shrink-0">
                  <Ticket className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">Book OPD Token</div>
                  <div className="text-[10px] text-slate-500">Queue for consultation</div>
                </div>
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  onOpenChange(false);
                  router.push(`/ipd?patientUid=${encodeURIComponent(patient.uid)}`);
                }}
                className="justify-start gap-2 h-auto py-2.5 px-3 bg-white border-slate-200 hover:border-blue-500 hover:bg-blue-50/50 text-left"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center shrink-0">
                  <PlusCircle className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">Admit to IPD</div>
                  <div className="text-[10px] text-slate-500">Ward &amp; bed allocation</div>
                </div>
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 border-t border-slate-100 pt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handlePrintCard}
            className="gap-1.5 text-xs w-full sm:w-auto"
          >
            <Printer className="w-3.5 h-3.5 text-slate-600" />
            Print Card / Slip
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRegisterAnother}
            className="text-xs w-full sm:w-auto"
          >
            Register Another
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={() => {
              onOpenChange(false);
              router.push("/patients");
            }}
            className="bg-primary text-white gap-1 text-xs w-full sm:w-auto"
          >
            Go to Patient Directory
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
