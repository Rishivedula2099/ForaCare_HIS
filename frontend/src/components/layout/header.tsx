"use client";

import React from "react";
import { Search } from "lucide-react";
import { FacilitySwitcher } from "./facility-switcher";
import { NotificationCenter } from "./notification-center";
import { UserMenu } from "./user-menu";

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
            readOnly
            placeholder="Search Patient by UID, Name, or Mobile (Ctrl+K)..."
            onClick={onSearchClick}
            onFocus={(e) => {
              e.currentTarget.blur();
              onSearchClick?.();
            }}
            className="w-full pl-9 pr-12 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary focus:bg-white transition-all cursor-pointer"
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
        <NotificationCenter />

        <div className="h-6 w-[1px] bg-slate-200 mx-1" />

        {/* User Profile */}
        <UserMenu />
      </div>
    </header>
  );
}
