"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, MailCheck } from "lucide-react";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";

interface ResetRequestData {
  requested: boolean;
  /** Present only in local development, where no mail server exists. */
  debug_token?: string | null;
}

export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [sent, setSent] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [debugToken, setDebugToken] = React.useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await apiClient.post<ResetRequestData>("/auth/password-reset/request", {
        identifier: identifier.trim(),
      });
      setDebugToken(response.data?.debug_token ?? null);
      setSent(true);
    } catch (err) {
      const apiError = err as ApiError;
      setError(
        apiError?.status_code === 429
          ? "Too many requests. Please wait before trying again."
          : apiError?.message || "Unable to send the reset link. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm space-y-6">
        <Link href="/" aria-label="ForaCare HIS home">
          <Logo variant="full" size="md" />
        </Link>

        {!sent ? (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Forgot your password?</h2>
              <p className="text-sm text-slate-500 mt-1">
                Enter your username or email and we&apos;ll send a link to choose a new one.
              </p>
            </div>
            {error && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="identifier" className="text-xs font-semibold text-slate-700">
                  Username or email
                </label>
                <Input
                  id="identifier"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting || !identifier.trim()}>
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {isSubmitting ? "Sending..." : "Send reset link"}
              </Button>
            </form>
          </>
        ) : (
          <div className="flex flex-col items-center text-center gap-3 py-6">
            <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
              <MailCheck className="w-5 h-5 text-emerald-600" />
            </div>
            <p className="text-sm font-semibold text-slate-900">Check your email</p>
            <p className="text-xs text-slate-500 max-w-xs">
              If an active account matches, a reset link is on its way. It works once and expires
              shortly. Nothing is revealed about whether the account exists.
            </p>
            {debugToken && (
              <Alert variant="info">
                <AlertDescription>
                  Local development (no mail server):{" "}
                  <Link className="font-medium underline" href={`/reset-password?token=${encodeURIComponent(debugToken)}`}>
                    open the reset link
                  </Link>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <Link href="/login" className="flex items-center justify-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to sign in
        </Link>
      </div>
    </div>
  );
}
