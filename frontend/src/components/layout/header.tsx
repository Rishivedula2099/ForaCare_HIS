"use client";

import React from "react";
import { Search, Bell, User } from "lucide-react";
import { FacilitySwitcher } from "./facility-switcher";

interface HeaderProps {
  onSearchClick?: () => void;
}

export function Header({ onSearchClick }: HeaderProps) {
  return (
    <header className="h-16 border-b border-slate-200 bg-white px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Quick Search */}
      <div className="flex items-center gap-4 flex-1 max-w-md">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search Patient by UID, Name, or Mobile (Ctrl+K)..."
            onClick={onSearchClick}
            className="w-full pl-9 pr-12 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary focus:bg-white transition-all"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 border border-slate-200 rounded">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right: Facility Switcher, Notifications, User Profile */}
      <div className="flex items-center gap-3">
        {/* Active Facility Context */}
        <FacilitySwitcher />

        {/* Alerts / Notifications */}
        <button
          type="button"
          className="relative p-2 rounded-md hover:bg-slate-100 text-slate-500 transition-colors cursor-pointer"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500" />
        </button>

        <div className="h-6 w-[1px] bg-slate-200 mx-1" />

        {/* User Pill */}
        <div className="flex items-center gap-2.5 pl-1">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600">
            <User className="w-4 h-4 text-slate-600" />
          </div>
          <div className="flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-900 leading-tight">
              Dr. Priya Raman
            </span>
            <span className="text-[10px] text-teal-700 font-medium">
              OPD Physician • Cardiologist
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
