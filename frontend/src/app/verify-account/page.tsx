"use client";

import * as React from "react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";

type Channel = "email" | "phone";

export default function VerifyAccountPage() {
  return (
    <AuthGuard>
      <VerifyAccountContent />
    </AuthGuard>
  );
}

function VerifyAccountContent() {
  return (
    <AppShell>
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Verify Your Account</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Confirm access to your registered email and phone number.
          </p>
        </div>
        <VerificationCard channel="email" />
        <VerificationCard channel="phone" />
      </div>
    </AppShell>
  );
}

function VerificationCard({ channel }: { channel: Channel }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [codeSent, setCodeSent] = React.useState(false);
  const [code, setCode] = React.useState("");
  const [isSending, setIsSending] = React.useState(false);
  const [isVerifying, setIsVerifying] = React.useState(false);

  if (!user) return null;

  const isVerified = channel === "email" ? user.email_verified : user.phone_verified;
  const targetValue = channel === "email" ? user.email : user.phone;
  const label = channel === "email" ? "Email Address" : "Phone Number";
  const requestPath = `/auth/${channel}/change/request`;
  const verifyPath = `/auth/${channel}/change/verify`;
  const requestField = channel === "email" ? "new_email" : "new_phone";

  async function sendCode() {
    if (!targetValue) {
      toast({
        title: `No ${label.toLowerCase()} on file`,
        description: `Add a ${label.toLowerCase()} to your profile before verifying it.`,
        variant: "destructive",
      });
      return;
    }
    setIsSending(true);
    try {
      const response = await apiClient.post<{ debug_code?: string | null }>(requestPath, {
        [requestField]: targetValue,
      });
      setCodeSent(true);
      toast({
        title: "Verification code sent",
        description: response.data?.debug_code
          ? `Local dev code: ${response.data.debug_code}`
          : `Check your ${label.toLowerCase()} for the code.`,
        variant: "info",
      });
    } catch (error) {
      const apiError = error as ApiError;
      toast({
        title: "Could not send code",
        description: apiError?.message || "Please try again shortly.",
        variant: "destructive",
      });
    } finally {
      setIsSending(false);
    }
  }

  async function verifyCode() {
    if (!targetValue) return;
    setIsVerifying(true);
    try {
      await apiClient.post(verifyPath, { [requestField]: targetValue, code });
      toast({ title: `${label} verified`, variant: "success" });
      setCode("");
      setCodeSent(false);
      window.location.reload();
    } catch (error) {
      const apiError = error as ApiError;
      toast({
        title: "Verification failed",
        description: apiError?.message || "That code is invalid or has expired.",
        variant: "destructive",
      });
    } finally {
      setIsVerifying(false);
    }
  }

  return (
    <Card className="shadow-xs border-slate-200">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">{label}</CardTitle>
          <CardDescription className="text-xs mt-0.5">{targetValue ?? "Not set"}</CardDescription>
        </div>
        <Badge variant={isVerified ? "completed" : "waiting"}>
          {isVerified ? "Verified" : "Unverified"}
        </Badge>
      </CardHeader>
      {!isVerified && (
        <CardContent className="space-y-3">
          {!codeSent ? (
            <Button size="sm" onClick={sendCode} disabled={isSending || !targetValue}>
              {isSending ? "Sending..." : "Send verification code"}
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="6-digit code"
                maxLength={6}
                className="max-w-[160px]"
              />
              <Button size="sm" onClick={verifyCode} disabled={isVerifying || code.length !== 6}>
                {isVerifying ? "Verifying..." : "Verify"}
              </Button>
              <Button size="sm" variant="outline" onClick={sendCode} disabled={isSending}>
                Resend
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
