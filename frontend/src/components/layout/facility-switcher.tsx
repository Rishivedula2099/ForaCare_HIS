"use client";

import React, { useState } from "react";
import { Building2, ChevronDown, Check } from "lucide-react";
import { Facility } from "@/types/auth";

interface FacilitySwitcherProps {
  currentFacility?: Facility;
  facilities?: Facility[];
  onFacilityChange?: (facility: Facility) => void;
}

const DEFAULT_FACILITIES: Facility[] = [
  {
    id: "fac_main_01",
    tenant_id: "ten_foracare_01",
    name: "ForaCare City Hospital (Main Branch)",
    facility_code: "FC-MAIN-01",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_active: true,
  },
  {
    id: "fac_satellite_02",
    tenant_id: "ten_foracare_01",
    name: "ForaCare South Clinic",
    facility_code: "FC-ST-02",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_active: true,
  },
];

export function FacilitySwitcher({
  currentFacility,
  facilities = DEFAULT_FACILITIES,
  onFacilityChange,
}: FacilitySwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFacility, setSelectedFacility] = useState<Facility>(
    currentFacility || facilities[0]
  );

  const handleSelect = (fac: Facility) => {
    setSelectedFacility(fac);
    setIsOpen(false);
    if (typeof window !== "undefined") {
      localStorage.setItem("foracare_facility_id", fac.id);
      localStorage.setItem("foracare_tenant_id", fac.tenant_id);
    }
    onFacilityChange?.(fac);
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
          <span className="font-semibold text-slate-900 leading-tight">
            {selectedFacility?.name || "Select Facility"}
          </span>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
            {selectedFacility?.facility_code || "FACILITY"}
          </span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute left-0 mt-1.5 w-64 rounded-md border border-slate-200 bg-white shadow-lg z-50 py-1 text-sm">
            <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
              Active Hospital / Branch
            </div>
            {facilities.map((fac) => {
              const isSelected = fac.id === selectedFacility.id;
              return (
                <button
                  key={fac.id}
                  type="button"
                  onClick={() => handleSelect(fac)}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 transition-colors ${
                    isSelected ? "bg-teal-50/50 text-primary font-medium" : "text-slate-700"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-xs">{fac.name}</span>
                    <span className="text-[10px] text-slate-400">
                      {fac.facility_code}
                    </span>
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
