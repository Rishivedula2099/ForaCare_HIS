import type { Metadata } from "next";
import Link from "next/link";
import {
  BedDouble,
  Building2,
  CalendarClock,
  FileText,
  FlaskConical,
  Fingerprint,
  Receipt,
  ShieldCheck,
  Stethoscope,
  Users,
} from "lucide-react";
import { AuthCta } from "@/components/public/auth-cta";
import { PublicShell } from "@/components/public/public-shell";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "ForaCare HIS | Hospital & clinic information system",
  description:
    "One system for patient registration, OPD, IPD, billing and the diagnostic laboratory - built for hospitals, clinics and multi-branch groups.",
};

const MODULES = [
  {
    icon: Users,
    title: "Patient 360",
    text: "Register once, get a permanent patient UID, and see the whole history in one place.",
  },
  {
    icon: CalendarClock,
    title: "OPD & queue",
    text: "Appointments and walk-ins, tokens with QR check-in, a live doctor queue, consultation and prescriptions.",
  },
  {
    icon: BedDouble,
    title: "IPD & beds",
    text: "Wards, rooms and beds with a clear bed board, admissions, transfers, consent and discharge.",
  },
  {
    icon: Receipt,
    title: "Billing & payments",
    text: "Service and package tariffs, invoices, deposits, payments, refunds and receipts.",
  },
  {
    icon: FlaskConical,
    title: "Laboratory",
    text: "Orders, sample accessioning with barcodes, result entry, verification, approval and QR-verifiable reports.",
  },
  {
    icon: FileText,
    title: "Documents & printing",
    text: "Versioned, facility-specific templates for tokens, receipts, consents, prescriptions and reports.",
  },
  {
    icon: Fingerprint,
    title: "ABHA / ABDM ready",
    text: "An integration layer for ABHA verification and consent, kept separate from your core records.",
  },
  {
    icon: ShieldCheck,
    title: "Access control & audit",
    text: "Role-based permissions, strict hospital separation, and an audit trail of sensitive actions.",
  },
];

const AUDIENCES = [
  { icon: Building2, title: "Hospitals", text: "OPD, IPD, diagnostics and billing under one roof." },
  { icon: Stethoscope, title: "Clinics", text: "A lighter day-to-day workflow for outpatient practices." },
  { icon: FlaskConical, title: "Diagnostic centres", text: "Sample-to-report workflow with barcode tracking." },
  { icon: Users, title: "Multi-branch groups", text: "Several facilities, one organisation, separate records." },
];

const STEPS = [
  { n: "1", title: "Tell us about your facility", text: "Send an onboarding request with a few details about your hospital or clinic." },
  { n: "2", title: "We set up your organisation", text: "Your hospital is created with its own facilities, and your administrator receives a secure activation link." },
  { n: "3", title: "Your team signs in", text: "Your administrator sets a password, adds staff and roles, and configures departments, doctors and tariffs." },
];

export default function LandingPage() {
  return (
    <PublicShell>
      {/* Hero */}
      <section className="bg-linear-to-b from-teal-50 to-white">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary">
            Hospital Information System
          </p>
          <h1 className="mt-3 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            One patient. One record. Better care.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-slate-600">
            ForaCare HIS brings registration, OPD, IPD, billing and the diagnostic laboratory
            into one system, so every team works from the same, up-to-date record.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <AuthCta size="lg" />
            <Button asChild size="lg" variant="outline">
              <Link href="/request-onboarding">Request onboarding</Link>
            </Button>
            <Button asChild size="lg" variant="ghost">
              <Link href="#modules">Explore the product</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Who it's for */}
      <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
        <h2 className="text-xl font-bold text-slate-900">Built for the way facilities really work</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {AUDIENCES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-xl border border-slate-200 p-5">
              <Icon className="h-5 w-5 text-primary" />
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-xs text-slate-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="scroll-mt-20 bg-slate-50">
        <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
          <h2 className="text-xl font-bold text-slate-900">What&apos;s in the box</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Each module works on its own and shares the same patient record. What a user sees
            depends on the permissions their hospital gives them.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {MODULES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Onboarding */}
      <section id="onboarding" className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-14 sm:px-6">
        <h2 className="text-xl font-bold text-slate-900">Getting your facility onboarded</h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map((step) => (
            <li key={step.n} className="rounded-xl border border-slate-200 p-5">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                {step.n}
              </span>
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{step.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Closing call to action */}
      <section className="bg-[#04222b] text-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-12 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <h2 className="text-xl font-bold">Ready to bring your facility onto ForaCare HIS?</h2>
            <p className="mt-1 text-sm text-slate-300">
              Already onboarded? Sign in with the account your administrator created for you.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="secondary" size="lg">
              <Link href="/request-onboarding">Request onboarding</Link>
            </Button>
            <AuthCta size="lg" />
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
