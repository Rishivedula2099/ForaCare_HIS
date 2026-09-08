"use client";

import React, { useState } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { Breadcrumbs } from "./breadcrumbs";
import { GlobalSearch } from "./global-search";
import { AuthGuard } from "@/components/auth/auth-guard";
import { UserRole } from "@/lib/constants";

interface AppShellProps {
  children: React.ReactNode;
  activePatientBanner?: React.ReactNode;
  /** Hide the auto breadcrumb bar for pages that render their own via PageHeader. */
  hideBreadcrumbBar?: boolean;
  /** Restrict this page to the given roles; redirects to /forbidden otherwise. */
  allowedRoles?: UserRole[];
}

export function AppShell({
  children,
  activePatientBanner,
  hideBreadcrumbBar,
  allowedRoles,
}: AppShellProps) {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <AuthGuard allowedRoles={allowedRoles}>
      <div className="flex min-h-screen bg-slate-50 text-slate-900">
        {/* Permanent Desktop Navigation Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Header onSearchClick={() => setSearchOpen(true)} />

          {/* Breadcrumb Trail */}
          {!hideBreadcrumbBar && (
            <div className="border-b border-slate-200 bg-white px-6 py-2">
              <Breadcrumbs />
            </div>
          )}

          {/* Persistent Patient Context Banner (When operating in patient scope) */}
          {activePatientBanner && (
            <div className="border-b border-teal-100 bg-teal-50/70 px-6 py-2">
              {activePatientBanner}
            </div>
          )}

          {/* Viewport Content */}
          <main className="flex-1 p-6 overflow-y-auto">{children}</main>
        </div>

        {/* Global Search Command Palette (Ctrl+K / Cmd+K) */}
        <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
      </div>
    </AuthGuard>
  );
}
