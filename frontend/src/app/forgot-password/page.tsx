"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, MailCheck } from "lucide-react";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { MOCK_FACILITIES } from "@/lib/auth-mock";

/**
 * Credential recovery is mock-only for now: there is no OTP delivery
 * backend yet (out of scope for P1-B04). This flow demonstrates the UX and
 * is ready to be pointed at a real endpoint once one exists.
 */
type Step = "identify" | "otp" | "done";

const FACILITY_OPTIONS = MOCK_FACILITIES.map((facility) => ({
  value: facility.id,
  label: `${facility.name} (${facility.facility_code})`,
}));

const RESEND_SECONDS = 30;

export default function ForgotPasswordPage() {
  const [step, setStep] = React.useState<Step>("identify");
  const [identifier, setIdentifier] = React.useState("");
  const [facilityId, setFacilityId] = React.useState(FACILITY_OPTIONS[0]?.value);
  const [otp, setOtp] = React.useState("");
  const [resendIn, setResendIn] = React.useState(RESEND_SECONDS);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (step !== "otp" || resendIn <= 0) return;
    const timer = setInterval(() => setResendIn((s) => s - 1), 1000);
    return () => clearInterval(timer);
  }, [step, resendIn]);

  const handleIdentify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSubmitting(false);
    setResendIn(RESEND_SECONDS);
    setStep("otp");
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSubmitting(false);
    setStep("done");
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm space-y-6">
        <Logo variant="full" size="md" />

        {step === "identify" && (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Forgot your password?</h2>
              <p className="text-sm text-slate-500 mt-1">
                Enter your staff ID or email and we&apos;ll send a verification code.
              </p>
            </div>
            <Alert variant="info">
              <AlertDescription>
                This is a demo flow (no OTP delivery is wired up yet) - any 6-digit code will be accepted.
              </AlertDescription>
            </Alert>
            <form onSubmit={handleIdentify} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Hospital / Facility</label>
                <Select options={FACILITY_OPTIONS} value={facilityId} onChange={setFacilityId} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Staff ID or Email</label>
                <Input
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="e.g. dr.priya or priya.raman@foracare-his.com"
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Sending..." : "Send Verification Code"}
              </Button>
            </form>
          </>
        )}

        {step === "otp" && (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Enter verification code</h2>
              <p className="text-sm text-slate-500 mt-1">
                We sent a 6-digit code to the contact on file for <span className="font-medium">{identifier}</span>.
              </p>
            </div>
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <Input
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                inputMode="numeric"
                className="text-center text-lg tracking-[0.5em]"
                required
              />
              <Button type="submit" className="w-full" disabled={isSubmitting || otp.length !== 6}>
                {isSubmitting ? "Verifying..." : "Verify Code"}
              </Button>
              <div className="text-center text-xs text-slate-500">
                {resendIn > 0 ? (
                  <span>Resend code in {resendIn}s</span>
                ) : (
                  <button
                    type="button"
                    onClick={() => setResendIn(RESEND_SECONDS)}
                    className="font-medium text-primary hover:underline"
                  >
                    Resend code
                  </button>
                )}
              </div>
            </form>
          </>
        )}

        {step === "done" && (
          <div className="flex flex-col items-center text-center gap-3 py-6">
            <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
              <MailCheck className="w-5 h-5 text-emerald-600" />
            </div>
            <p className="text-sm font-semibold text-slate-900">Code verified</p>
            <p className="text-xs text-slate-500 max-w-xs">
              You can now set a new password, or contact your hospital IT desk if you need further help.
            </p>
            <Button asChild size="sm" className="mt-2">
              <Link href="/reset-password">Set New Password</Link>
            </Button>
          </div>
        )}

        <Link href="/login" className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-primary">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Sign In
        </Link>
      </div>
    </div>
  );
}
