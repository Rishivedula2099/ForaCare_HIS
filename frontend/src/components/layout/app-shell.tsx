"use client";

import React from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

interface AppShellProps {
  children: React.ReactNode;
  activePatientBanner?: React.ReactNode;
}

export function AppShell({ children, activePatientBanner }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Permanent Desktop Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        {/* Persistent Patient Context Banner (When operating in patient scope) */}
        {activePatientBanner && (
          <div className="border-b border-teal-100 bg-teal-50/70 px-6 py-2">
            {activePatientBanner}
          </div>
        )}

        {/* Viewport Content */}
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
