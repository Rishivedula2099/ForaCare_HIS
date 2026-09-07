"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
  ShieldCheck,
  SlidersHorizontal,
  Activity,
} from "lucide-react";
import { MAIN_NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";

const ICONS_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
  ShieldCheck,
  SlidersHorizontal,
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 border-b border-slate-200 flex items-center px-5 gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shadow-xs">
          <Activity className="w-5 h-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-slate-900 tracking-tight text-base leading-tight">
            ForaCare <span className="text-primary font-extrabold">HIS</span>
          </span>
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-widest">
            Enterprise HMIS
          </span>
        </div>
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          Hospital Modules
        </div>
        {MAIN_NAV_ITEMS.map((item) => {
          const Icon = ICONS_MAP[item.iconName] || LayoutDashboard;
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all group",
                isActive
                  ? "bg-teal-50 text-primary font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-slate-400 group-hover:text-slate-600"
                )}
              />
              <span className="flex-1">{item.title}</span>
              {item.badge && (
                <span className="text-[10px] font-semibold bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* Footer / System Status */}
      <div className="p-4 border-t border-slate-200 bg-slate-50/70 text-xs">
        <div className="flex items-center justify-between text-slate-500">
          <span className="font-medium text-[11px]">System Status</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-emerald-700">Online</span>
          </div>
        </div>
        <div className="mt-1 text-[10px] text-slate-400">
          Local Hospital Engine v0.1.0
        </div>
      </div>
    </aside>
  );
}
