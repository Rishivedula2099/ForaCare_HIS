"use client";

import * as React from "react";
import Link from "next/link";
import { Logo } from "@/components/common/logo";
import { Button } from "@/components/ui/button";
import { AuthCta } from "@/components/public/auth-cta";
import { APP_NAME } from "@/lib/constants";

/**
 * Chrome for unauthenticated pages (landing, onboarding enquiry). Deliberately
 * independent of `AppShell`: no sidebar, no facility switcher, no module
 * navigation, and nothing here reads clinical or administrative data.
 */
export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" aria-label={`${APP_NAME} home`}>
            <Logo variant="full" size="sm" />
          </Link>
          <nav className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/#modules"
              className="hidden text-sm font-medium text-slate-600 hover:text-slate-900 sm:inline"
            >
              Product
            </Link>
            <Link
              href="/#onboarding"
              className="hidden text-sm font-medium text-slate-600 hover:text-slate-900 sm:inline"
            >
              How it works
            </Link>
            <Button asChild variant="outline" size="sm">
              <Link href="/request-onboarding">Request onboarding</Link>
            </Button>
            <AuthCta size="sm" />
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-slate-200 bg-slate-50">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>&copy; {new Date().getFullYear()} ForaSoftware. All rights reserved.</p>
          <p>
            {APP_NAME} is for use by authorised hospital and clinic staff. Patient and
            administrative data is never shown on public pages.
          </p>
        </div>
      </footer>
    </div>
  );
}
