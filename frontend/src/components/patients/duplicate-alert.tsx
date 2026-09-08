"use client";

import React from "react";
import Link from "next/link";
import { AlertTriangle, UserCheck, ExternalLink, X } from "lucide-react";
import { Patient } from "@/types/patient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface DuplicateAlertProps {
  duplicates: Patient[];
  onDismiss?: () => void;
}

export function DuplicateAlert({ duplicates, onDismiss }: DuplicateAlertProps) {
  if (!duplicates || duplicates.length === 0) return null;

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50/90 p-4 text-amber-950 shadow-xs animate-in fade-in-50">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-500 text-white flex items-center justify-center shrink-0 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">
              Potential Duplicate Patient Detected ({duplicates.length} match{duplicates.length > 1 ? "es" : ""})
            </h4>
            <p className="text-[11px] text-amber-800">
              A patient with matching mobile number, government ID, or Name + Year of Birth already exists in the system.
            </p>
          </div>
        </div>

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-amber-700 hover:text-amber-900 p-1 rounded hover:bg-amber-100"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="mt-3 divide-y divide-amber-200/60 rounded-lg bg-white/80 border border-amber-200 overflow-hidden">
        {duplicates.map((pat) => (
          <div
            key={pat.id}
            className="p-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900">{pat.fullName}</span>
                <Badge variant="outline" className="font-mono text-[10px] bg-slate-100">
                  {pat.uid}
                </Badge>
                <span className="text-slate-500 text-[11px]">
                  {pat.gender} • {pat.ageYears} yrs • Blood: {pat.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                </span>
              </div>
              <div className="text-[11px] text-slate-600 flex items-center gap-3">
                <span>📱 {pat.mobile}</span>
                {pat.primaryIdentity && (
                  <span>
                    🪪 {pat.primaryIdentity.type}: {pat.primaryIdentity.idNumber}
                  </span>
                )}
                <span>📍 {pat.address.city}, {pat.address.state}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href={`/patients?uid=${encodeURIComponent(pat.uid)}`}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
              >
                View Existing Patient <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
