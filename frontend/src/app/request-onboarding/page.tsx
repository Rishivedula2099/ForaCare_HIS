"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, Loader2 } from "lucide-react";
import { PublicShell } from "@/components/public/public-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";

const FACILITY_TYPES = [
  { value: "hospital", label: "Hospital" },
  { value: "clinic", label: "Clinic" },
  { value: "diagnostic_centre", label: "Diagnostic centre" },
  { value: "multi_branch_group", label: "Multi-branch group" },
  { value: "other", label: "Other" },
];

const EMPTY = {
  organization_name: "",
  contact_name: "",
  email: "",
  phone: "",
  facility_type: "hospital",
  message: "",
  website: "", // honeypot - real visitors never see or fill this
};

export default function RequestOnboardingPage() {
  const [form, setForm] = React.useState(EMPTY);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [done, setDone] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const set = (field: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await apiClient.post("/public/onboarding-requests", {
        ...form,
        phone: form.phone.trim() || null,
        message: form.message.trim() || null,
        website: form.website || null,
      });
      setDone(true);
    } catch (err) {
      const apiError = err as ApiError;
      setError(
        apiError?.status_code === 429
          ? "Too many requests from your connection. Please try again in a few minutes."
          : apiError?.status_code === 422
            ? "Please check the details you entered - the email address must be valid."
            : "We couldn't send your request. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PublicShell>
      <div className="mx-auto w-full max-w-xl px-4 py-12 sm:px-6">
        {done ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <CheckCircle2 className="h-10 w-10 text-emerald-600" />
            <h1 className="text-xl font-bold text-slate-900">Request received</h1>
            <p className="text-sm text-slate-600">
              Thank you. Our team will contact you at the email you provided to set up your
              organisation.
            </p>
            <Button asChild variant="outline">
              <Link href="/">Back to home</Link>
            </Button>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Request onboarding</h1>
            <p className="mt-1 text-sm text-slate-600">
              Tell us about your hospital or clinic. Please don&apos;t include any patient
              information - we only need organisation and contact details.
            </p>

            {error && (
              <Alert variant="destructive" className="mt-5" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <Field label="Hospital / clinic name" htmlFor="organization_name">
                <Input id="organization_name" value={form.organization_name} onChange={set("organization_name")} required minLength={2} maxLength={255} />
              </Field>
              <Field label="Type of facility" htmlFor="facility_type">
                <Select
                  id="facility_type"
                  options={FACILITY_TYPES}
                  value={form.facility_type}
                  onChange={(value) => setForm((prev) => ({ ...prev, facility_type: value }))}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Your name" htmlFor="contact_name">
                  <Input id="contact_name" value={form.contact_name} onChange={set("contact_name")} required minLength={2} maxLength={255} autoComplete="name" />
                </Field>
                <Field label="Work email" htmlFor="email">
                  <Input id="email" type="email" value={form.email} onChange={set("email")} required maxLength={255} autoComplete="email" />
                </Field>
              </div>
              <Field label="Phone (optional)" htmlFor="phone">
                <Input id="phone" type="tel" value={form.phone} onChange={set("phone")} maxLength={30} autoComplete="tel" />
              </Field>
              <Field label="Anything we should know? (optional)" htmlFor="message">
                <textarea
                  id="message"
                  value={form.message}
                  onChange={set("message")}
                  maxLength={2000}
                  rows={4}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </Field>

              {/* Honeypot: visually hidden and skipped by keyboard and screen readers. */}
              <div aria-hidden="true" className="absolute left-[-9999px] h-0 w-0 overflow-hidden">
                <label htmlFor="website">Website</label>
                <input id="website" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} />
              </div>

              <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {isSubmitting ? "Sending..." : "Send request"}
              </Button>
            </form>
          </>
        )}
      </div>
    </PublicShell>
  );
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="text-xs font-semibold text-slate-700">
        {label}
      </label>
      {children}
    </div>
  );
}
