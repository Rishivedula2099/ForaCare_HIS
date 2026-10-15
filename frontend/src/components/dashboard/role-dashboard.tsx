"use client";

import Link from "next/link";
import {
  Building2,
  CalendarClock,
  FlaskConical,
  KeyRound,
  LayoutDashboard,
  Printer,
  Receipt,
  ShieldCheck,
  SlidersHorizontal,
  Stethoscope,
  Users,
  BedDouble,
} from "lucide-react";
import type { ComponentType } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { IS_DEV_BUILD } from "@/lib/constants";
import { accessibleModules } from "@/lib/route-access";

const ICONS: Record<string, ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
  ShieldCheck,
  SlidersHorizontal,
  KeyRound,
  Building2,
  Stethoscope,
};

/**
 * The signed-in user's workspace, built from their effective permissions:
 * one tile per module the route policy admits. No role is special-cased and
 * no figures are invented - live counts belong to each module's own page.
 */
export function RoleDashboard() {
  const { hasPermission } = useAuth();
  const modules = accessibleModules(hasPermission, { devToolsEnabled: IS_DEV_BUILD });

  if (modules.length === 0) {
    return (
      <Card className="shadow-xs border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">No modules assigned</CardTitle>
          <CardDescription className="text-xs">
            Your account has no module permissions in this facility yet. Ask your hospital
            administrator to assign you a role.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {modules.map((item) => {
        const Icon = ICONS[item.iconName] ?? LayoutDashboard;
        return (
          <Link key={item.href} href={item.href} className="group">
            <Card className="shadow-xs border-slate-200 transition-colors group-hover:border-primary/50">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-primary bg-primary/10">
                  <Icon className="w-5 h-5" />
                </div>
                <div className="text-sm font-semibold text-slate-900">{item.title}</div>
              </CardContent>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}
