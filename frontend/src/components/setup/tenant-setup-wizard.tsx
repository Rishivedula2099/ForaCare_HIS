"use client";

import * as React from "react";
import { AlertTriangle, Check, CheckCircle2, Copy, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { checkAvailability, createTenant, getSetupOptions, SetupOptions, SetupResult } from "@/lib/platform-api";
import {
  EMPTY_FORM,
  mapServerErrors,
  SetupErrors,
  SetupForm,
  STEPS,
  stepOf,
  suggestCode,
  toPayload,
  validateAll,
  validateField,
  validateStep,
} from "@/lib/setup-validation";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/types/api";

type Phase = "idle" | "validating" | "creating";

function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-slate-700">
        {label}
      </label>
      {children}
      {/* Always rendered with a fixed height: a message appearing on blur must not
          shift the layout, or the click that caused the blur lands on empty space. */}
      <p
        id={error ? `${id}-error` : undefined}
        role={error ? "alert" : undefined}
        className={cn("min-h-4 text-xs", error ? "text-rose-600" : "text-[11px] text-slate-500")}
      >
        {error ?? hint ?? ""}
      </p>
    </div>
  );
}

export function TenantSetupWizard() {
  const [options, setOptions] = React.useState<SetupOptions | null>(null);
  const [optionsError, setOptionsError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<SetupForm>(EMPTY_FORM);
  const [errors, setErrors] = React.useState<SetupErrors>({});
  const [step, setStep] = React.useState(0);
  const [reached, setReached] = React.useState(0);
  const [phase, setPhase] = React.useState<Phase>("idle");
  const [banner, setBanner] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SetupResult | null>(null);
  const [copied, setCopied] = React.useState(false);
  // Edited by hand = stop auto-suggesting that code.
  const codeTouched = React.useRef({ org: false, facility: false });
  // Synchronous guard: two clicks in the same tick must not send two requests.
  const submitting = React.useRef(false);

  React.useEffect(() => {
    let cancelled = false;
    getSetupOptions()
      .then((loaded) => {
        if (cancelled) return;
        setOptions(loaded);
        setForm((prev) => ({
          ...prev,
          facilityType: prev.facilityType || "hospital",
          timezone: prev.timezone || loaded.default_timezone,
          currency: prev.currency || loaded.default_currency,
        }));
      })
      .catch((err: ApiError) => !cancelled && setOptionsError(err?.message || "Could not load setup options."));
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = JSON.stringify(form) !== JSON.stringify({ ...EMPTY_FORM, facilityType: "hospital", timezone: options?.default_timezone ?? "", currency: options?.default_currency ?? "" });
  React.useEffect(() => {
    if (!dirty || result) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, result]);

  const busy = phase !== "idle";

  const update = <K extends keyof SetupForm>(field: K, value: SetupForm[K]) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "orgName" && !codeTouched.current.org) next.orgCode = suggestCode(String(value));
      if (field === "orgCode") codeTouched.current.org = true;
      if (field === "facilityCode") codeTouched.current.facility = true;
      if ((field === "orgName" || field === "orgCode") && !codeTouched.current.facility) {
        next.facilityCode = next.orgCode ? `${next.orgCode.toUpperCase()}-01` : "";
      }
      return next;
    });
    setErrors((prev) => {
      if (!prev[field]) return prev;
      const { [field]: _removed, ...rest } = prev;
      void _removed;
      return rest;
    });
    setBanner(null);
  };

  const blur = (field: keyof SetupForm) => {
    const message = validateField(field, form);
    if (message) setErrors((prev) => ({ ...prev, [field]: message }));
  };

  /** Asks the server whether the codes/username/email of this step are still free. */
  const uniquenessErrors = async (stepIndex: number): Promise<SetupErrors> => {
    const id = STEPS[stepIndex].id;
    const params =
      id === "organization"
        ? { organization_code: form.orgCode.trim() }
        : id === "facility"
          ? { facility_code: form.facilityCode.trim() }
          : id === "administrator"
            ? { username: form.adminUsername.trim(), email: form.adminEmail.trim() }
            : null;
    if (!params) return {};
    try {
      const free = await checkAvailability(params);
      const taken: SetupErrors = {};
      if (free.organization_code === false) taken.orgCode = "An organisation with this code already exists.";
      if (free.facility_code === false) taken.facilityCode = "A facility with this code already exists.";
      if (free.username === false) taken.adminUsername = "This username is already taken.";
      if (free.email === false) taken.adminEmail = "An account with this email address already exists.";
      return taken;
    } catch {
      return {}; // the create call re-checks authoritatively
    }
  };

  const goNext = async () => {
    if (busy) return;
    const local = validateStep(step, form);
    if (Object.keys(local).length) {
      setErrors((prev) => ({ ...prev, ...local }));
      return;
    }
    setPhase("validating");
    const taken = await uniquenessErrors(step);
    setPhase("idle");
    if (Object.keys(taken).length) {
      setErrors((prev) => ({ ...prev, ...taken }));
      return;
    }
    const next = Math.min(step + 1, STEPS.length - 1);
    setStep(next);
    setReached((r) => Math.max(r, next));
  };

  const submit = async () => {
    if (submitting.current || result) return;
    const all = validateAll(form);
    if (Object.keys(all).length) {
      setErrors(all);
      setStep(Math.min(...(Object.keys(all) as (keyof SetupForm)[]).map(stepOf)));
      setBanner("Some details are missing or invalid. Please correct them to continue.");
      return;
    }
    submitting.current = true;
    setBanner(null);
    try {
      setPhase("validating");
      for (const index of [0, 1, 4]) {
        const taken = await uniquenessErrors(index);
        if (Object.keys(taken).length) {
          setErrors(taken);
          setStep(index);
          setBanner("Some of these details are already in use.");
          return;
        }
      }
      setPhase("creating");
      const created = await createTenant(toPayload(form));
      setResult(created);
      setForm(EMPTY_FORM); // nothing left to resubmit
      setErrors({});
    } catch (raw) {
      const err = raw as ApiError;
      const fieldErrors = mapServerErrors(err?.details ?? []);
      if (Object.keys(fieldErrors).length) {
        setErrors(fieldErrors);
        setStep(Math.min(...(Object.keys(fieldErrors) as (keyof SetupForm)[]).map(stepOf)));
        setBanner(
          err.code === "DUPLICATE"
            ? "Some of these details are already in use. Nothing was created."
            : "Please correct the highlighted details. Nothing was created."
        );
      } else if (err?.status_code === 403) {
        setBanner("Only a platform operator can create hospitals.");
      } else if (err?.code === "DUPLICATE") {
        setBanner(err.message);
      } else if (err?.code === "NETWORK_ERROR" || err?.code === "TIMEOUT") {
        setBanner(
          "We lost contact with the server, so we cannot tell whether the hospital was created. " +
            "It is safe to press Create again: if it already exists you will be told it is a duplicate."
        );
      } else {
        setBanner(err?.message || "Something went wrong. Nothing was confirmed as created.");
      }
    } finally {
      setPhase("idle");
      submitting.current = false;
    }
  };

  const restart = () => {
    setResult(null);
    setStep(0);
    setReached(0);
    codeTouched.current = { org: false, facility: false };
    setForm({
      ...EMPTY_FORM,
      facilityType: "hospital",
      timezone: options?.default_timezone ?? "",
      currency: options?.default_currency ?? "",
    });
  };

  const copyLink = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.activation_link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const stepErrorCount = (index: number) => STEPS[index].fields.filter((f) => errors[f]).length;
  const typeLabel = (value: string) => options?.facility_types.find((o) => o.value === value)?.label ?? value;
  const tzLabel = (value: string) => options?.timezones.find((o) => o.value === value)?.label ?? value;
  const currencyLabel = (value: string) => options?.currencies.find((o) => o.value === value)?.label ?? value;

  if (optionsError) {
    return (
      <Alert variant="destructive" role="alert">
        <AlertDescription>{optionsError}</AlertDescription>
      </Alert>
    );
  }

  if (result) {
    return (
      <Card className="border-emerald-200 shadow-xs">
        <CardContent className="space-y-5 p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-6 w-6 text-emerald-600" />
            <div>
              <h2 className="text-lg font-bold text-slate-900">{result.tenant_name} is set up</h2>
              <p className="text-sm text-slate-600">
                {result.facility_name} ({typeLabel(result.facility_type)}, code {result.facility_code}) and its
                administrator <strong>{result.administrator_username}</strong> were created.
              </p>
            </div>
          </div>

          {result.activation_email_sent ? (
            <Alert variant="success">
              <AlertDescription>
                An activation email was sent to {result.administrator_email}. The link below is the same one,
                in case it does not arrive.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="warning">
              <AlertDescription>
                No email was sent. Give the link below to {result.administrator_email} through a channel you trust.
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-700">One-time activation link</p>
            <div className="flex gap-2">
              <Input readOnly value={result.activation_link} aria-label="Activation link" className="font-mono text-xs" />
              <Button type="button" variant="outline" onClick={copyLink}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <p className="flex items-center gap-1.5 text-[11px] text-amber-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              Shown only once and valid for {result.activation_expires_hours} hours. It cannot be retrieved later.
              The administrator chooses their own password; none is ever shown here.
            </p>
          </div>

          <Button type="button" onClick={restart}>
            Set up another hospital
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!options) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading setup options...
      </div>
    );
  }

  const inputProps = (field: keyof SetupForm, id: string) => ({
    id,
    value: form[field] as string,
    disabled: busy,
    "aria-invalid": !!errors[field],
    "aria-describedby": errors[field] ? `${id}-error` : undefined,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => update(field, e.target.value as SetupForm[typeof field]),
    onBlur: () => blur(field),
  });

  const current = STEPS[step].id;
  const reviewRows: [string, string][] = [
    ["Organisation", `${form.orgName} (${form.orgCode.toUpperCase()})`],
    ["Facility", `${form.facilityName} (${form.facilityCode.toUpperCase()}) - ${typeLabel(form.facilityType)}`],
    ["Contact", `${form.phone} - ${form.email}`],
    [
      "Address",
      [form.addressLine1, form.addressLine2, `${form.city}, ${form.state} ${form.postalCode}`].filter(Boolean).join(", "),
    ],
    ["Time zone / currency", `${tzLabel(form.timezone)} - ${currencyLabel(form.currency)}`],
    ["Administrator", `${form.adminName} - ${form.adminUsername} - ${form.adminEmail}`],
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      {/* Progress */}
      <nav aria-label="Setup progress">
        <ol className="space-y-1">
          {STEPS.map((s, index) => {
            const done = index < reached && index !== step && stepErrorCount(index) === 0;
            const failing = stepErrorCount(index) > 0;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  disabled={busy || index > reached}
                  onClick={() => setStep(index)}
                  aria-current={index === step ? "step" : undefined}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
                    index === step ? "bg-teal-50 font-semibold text-primary" : "text-slate-600 hover:bg-slate-100",
                    index > reached && "cursor-not-allowed opacity-50"
                  )}
                >
                  <span
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold",
                      failing
                        ? "border-rose-300 bg-rose-50 text-rose-600"
                        : done
                          ? "border-emerald-300 bg-emerald-50 text-emerald-600"
                          : index === step
                            ? "border-primary bg-primary text-white"
                            : "border-slate-300 text-slate-500"
                    )}
                  >
                    {failing ? "!" : done ? <Check className="h-3.5 w-3.5" /> : index + 1}
                  </span>
                  <span className="flex-1">{s.title}</span>
                </button>
              </li>
            );
          })}
        </ol>
        <p className="mt-3 px-2.5 text-[11px] text-slate-500">
          Step {step + 1} of {STEPS.length}
        </p>
      </nav>

      <Card className="shadow-xs">
        <CardContent className="space-y-5 p-6">
          {banner && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{banner}</AlertDescription>
            </Alert>
          )}

          {current === "organization" && (
            <>
              <Heading title="Organisation" text="The hospital group or company that owns the system. Its data is kept completely separate from every other organisation." />
              <Field id="orgName" label="Organisation name" error={errors.orgName}>
                <Input {...inputProps("orgName", "orgName")} autoFocus maxLength={255} />
              </Field>
              <Field id="orgCode" label="Organisation code" error={errors.orgCode} hint="Short and unique, e.g. SUNRISE. Cannot be changed later.">
                <Input {...inputProps("orgCode", "orgCode")} maxLength={50} className="uppercase" />
              </Field>
            </>
          )}

          {current === "facility" && (
            <>
              <Heading title="First facility" text="The first hospital, clinic or medical centre. More can be added later." />
              <Field id="facilityName" label="Facility name" error={errors.facilityName}>
                <Input {...inputProps("facilityName", "facilityName")} autoFocus maxLength={255} />
              </Field>
              <Field id="facilityType" label="Facility type" error={errors.facilityType}>
                <Select
                  id="facilityType"
                  options={options.facility_types}
                  value={form.facilityType}
                  disabled={busy}
                  onChange={(v) => update("facilityType", v)}
                  placeholder="Choose a type"
                />
              </Field>
              <Field id="facilityCode" label="Facility code" error={errors.facilityCode} hint="Appears on patient IDs and documents, e.g. SUN-MAIN-01.">
                <Input {...inputProps("facilityCode", "facilityCode")} maxLength={50} className="uppercase" />
              </Field>
            </>
          )}

          {current === "contact" && (
            <>
              <Heading title="Contact & address" text="Printed on documents and receipts." />
              <div className="grid gap-4 sm:grid-cols-2">
                <Field id="phone" label="Phone" error={errors.phone}>
                  <Input {...inputProps("phone", "phone")} type="tel" autoFocus maxLength={20} autoComplete="off" />
                </Field>
                <Field id="email" label="Contact email" error={errors.email}>
                  <Input {...inputProps("email", "email")} type="email" maxLength={255} autoComplete="off" />
                </Field>
              </div>
              <Field id="addressLine1" label="Address line 1" error={errors.addressLine1}>
                <Input {...inputProps("addressLine1", "addressLine1")} maxLength={200} />
              </Field>
              <Field id="addressLine2" label="Address line 2 (optional)" error={errors.addressLine2}>
                <Input {...inputProps("addressLine2", "addressLine2")} maxLength={200} />
              </Field>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field id="city" label="City" error={errors.city}>
                  <Input {...inputProps("city", "city")} maxLength={100} />
                </Field>
                <Field id="state" label="State / province" error={errors.state}>
                  <Input {...inputProps("state", "state")} maxLength={100} />
                </Field>
                <Field id="postalCode" label="Postal / PIN code" error={errors.postalCode}>
                  <Input {...inputProps("postalCode", "postalCode")} maxLength={12} />
                </Field>
              </div>
            </>
          )}

          {current === "operations" && (
            <>
              <Heading title="Operational settings" text="Used for appointment times, timestamps on documents and billing." />
              <Field id="timezone" label="Time zone" error={errors.timezone}>
                <Select id="timezone" options={options.timezones} value={form.timezone} disabled={busy} onChange={(v) => update("timezone", v)} />
              </Field>
              <Field id="currency" label="Currency" error={errors.currency}>
                <Select id="currency" options={options.currencies} value={form.currency} disabled={busy} onChange={(v) => update("currency", v)} />
              </Field>
            </>
          )}

          {current === "administrator" && (
            <>
              <Heading
                title="Hospital administrator"
                text="The first person to sign in. They receive a one-time link to choose their own password; you never see or set it."
              />
              <Field id="adminName" label="Full name" error={errors.adminName}>
                <Input {...inputProps("adminName", "adminName")} autoFocus maxLength={255} autoComplete="off" />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field id="adminUsername" label="Username" error={errors.adminUsername}>
                  <Input {...inputProps("adminUsername", "adminUsername")} maxLength={100} autoComplete="off" />
                </Field>
                <Field id="adminEmail" label="Email" error={errors.adminEmail}>
                  <Input {...inputProps("adminEmail", "adminEmail")} type="email" maxLength={255} autoComplete="off" />
                </Field>
              </div>
              {options.email_delivery_available && (
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.sendEmail}
                    disabled={busy}
                    onChange={(e) => update("sendEmail", e.target.checked)}
                  />
                  Email the activation link to the administrator
                </label>
              )}
            </>
          )}

          {current === "review" && (
            <>
              <Heading title="Review & create" text="Check everything. Creating is all-or-nothing: if anything fails, nothing is saved." />
              <dl className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                {reviewRows.map(([label, value]) => (
                  <div key={label} className="grid gap-1 px-4 py-2.5 sm:grid-cols-[170px_1fr]">
                    <dt className="text-xs font-semibold text-slate-500">{label}</dt>
                    <dd className="text-sm text-slate-900">{value}</dd>
                  </div>
                ))}
              </dl>
              {busy && (
                <ol className="space-y-1.5 text-sm" aria-live="polite">
                  <li className="flex items-center gap-2">
                    {phase === "validating" ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Check className="h-4 w-4 text-emerald-600" />}
                    Checking details
                  </li>
                  <li className={cn("flex items-center gap-2", phase !== "creating" && "text-slate-400")}>
                    {phase === "creating" ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <span className="h-4 w-4" />}
                    Creating organisation, facility and administrator
                  </li>
                </ol>
              )}
            </>
          )}

          <div className="flex items-center justify-between border-t border-slate-100 pt-4">
            <Button type="button" variant="outline" disabled={busy || step === 0} onClick={() => setStep(step - 1)}>
              Back
            </Button>
            {current === "review" ? (
              <Button type="button" onClick={submit} disabled={busy}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                {busy ? "Creating..." : "Create hospital"}
              </Button>
            ) : (
              <Button type="button" onClick={goNext} disabled={busy}>
                {phase === "validating" && <Loader2 className="h-4 w-4 animate-spin" />}
                {phase === "validating" ? "Checking..." : "Continue"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Heading({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h2 className="text-base font-bold text-slate-900">{title}</h2>
      <p className="mt-0.5 text-xs text-slate-500">{text}</p>
    </div>
  );
}
