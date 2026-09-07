"use client";

import React, { useState } from "react";
import { Building2, ChevronDown, Check } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export function FacilitySwitcher() {
  const { facility, availableFacilities, switchFacility } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  if (!facility) return null;

  const handleSelect = (facilityId: string) => {
    switchFacility(facilityId);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 text-xs font-medium shadow-xs transition-colors cursor-pointer"
        aria-expanded={isOpen}
      >
        <Building2 className="w-4 h-4 text-primary" />
        <div className="text-left flex flex-col">
          <span className="font-semibold text-slate-900 leading-tight">{facility.name}</span>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
            {facility.facility_code}
          </span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 mt-1.5 w-64 rounded-md border border-slate-200 bg-white shadow-lg z-50 py-1 text-sm">
            <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
              Active Hospital / Branch
            </div>
            {availableFacilities.map((fac) => {
              const isSelected = fac.id === facility.id;
              return (
                <button
                  key={fac.id}
                  type="button"
                  onClick={() => handleSelect(fac.id)}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 transition-colors ${
                    isSelected ? "bg-teal-50/50 text-primary font-medium" : "text-slate-700"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-xs">{fac.name}</span>
                    <span className="text-[10px] text-slate-400">{fac.facility_code}</span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-primary" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
