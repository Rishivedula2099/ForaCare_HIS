"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Clock,
  Link2,
  Link2Off,
  Loader2,
  RotateCw,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  AbdmAuthMethod,
  AbhaConsentPurpose,
  getAbdmStatus,
  getAbhaStatus,
  grantAbhaConsent,
  linkAbha,
  requestAbhaOtp,
  revokeAbhaConsent,
  unlinkAbha,
  verifyAbha,
} from "@/lib/patient-api";
import { ApiError } from "@/types/api";

const PURPOSES: { value: AbhaConsentPurpose; label: string }[] = [
  { value: "CARE_MANAGEMENT", label: "Care management" },
  { value: "HEALTH_RECORDS_SHARING", label: "Health records sharing" },
  { value: "RESEARCH", label: "Research" },
];

const STATUS_BADGE: Record<string, string> = {
  UNVERIFIED: "bg-amber-50 text-amber-800 border-amber-300",
  VERIFIED: "bg-blue-50 text-blue-700 border-blue-300",
  LINKED: "bg-emerald-50 text-emerald-700 border-emerald-300",
};

function Field({ label, value }: { label: string; value?: React.ReactNode }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="text-sm font-medium text-slate-800">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Integration states (P8-F03)
// ---------------------------------------------------------------------------

/** What the user sees for a failed ABDM call, derived from the backend's
 *  error code (see `_GATEWAY_STATUS_CODES` in backend abdm/service.py).
 *  `retryable` failures are transient - the same request may well succeed. */
export type IntegrationFailure = {
  kind: "timeout" | "unavailable" | "failed";
  title: string;
  message: string;
  retryable: boolean;
};

// Only these backend codes carry a message written for end users. Anything
// else (gateway/auth/config/internal errors) is replaced with fixed copy so
// raw server text can never reach the screen (P8-F04).
const USER_SAFE_MESSAGE_CODES = new Set([
  "ABDM_INVALID_OTP",
  "ABDM_INVALID_TRANSACTION",
  "CONFLICT",
  "NOT_FOUND",
  "FORBIDDEN",
  "VALIDATION_ERROR",
]);

export function toIntegrationFailure(
  error: ApiError | undefined,
  fallback: string,
): IntegrationFailure {
  switch (error?.code) {
    case "ABDM_TIMEOUT":
    case "TIMEOUT":
      return {
        kind: "timeout",
        title: "ABDM timed out",
        message:
          "The ABDM gateway did not respond in time. Nothing was changed - you can try again.",
        retryable: true,
      };
    case "ABDM_UNAVAILABLE":
    case "NETWORK_ERROR":
      return {
        kind: "unavailable",
        title: "ABDM unavailable",
        message:
          "The ABDM gateway is currently unreachable. Try again in a moment.",
        retryable: true,
      };
    case "ABDM_NOT_CONFIGURED":
    case "ABDM_AUTH_FAILED":
    case "ABDM_NOT_IMPLEMENTED":
      return {
        kind: "failed",
        title: "ABDM integration unavailable",
        message:
          "The ABDM integration is not available for this hospital. Please contact your administrator.",
        retryable: false,
      };
    case "ABDM_REJECTED":
      return {
        kind: "failed",
        title: "Request not accepted",
        message:
          "ABDM could not process this request. Check the details and try again.",
        retryable: false,
      };
    default:
      return {
        kind: "failed",
        title: "Request failed",
        message:
          error?.code &&
          USER_SAFE_MESSAGE_CODES.has(error.code) &&
          error.message
            ? error.message
            : fallback,
        retryable: false,
      };
  }
}

function FailureBanner({
  failure,
  attempt,
  onRetry,
  retrying,
}: {
  failure: IntegrationFailure;
  attempt: number;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  const Icon = failure.kind === "timeout" ? Clock : AlertTriangle;
  return (
    <div
      role="alert"
      className={`rounded-lg border p-3 text-xs space-y-2 ${
        failure.kind === "failed"
          ? "border-rose-200 bg-rose-50 text-rose-800"
          : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <p className="flex items-center gap-1.5 font-semibold">
        <Icon className="w-3.5 h-3.5" />
        {failure.title}
        {attempt > 1 && (
          <span className="font-normal opacity-70">(attempt {attempt})</span>
        )}
      </p>
      <p>{failure.message}</p>
      {failure.retryable && onRetry && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={retrying}
          onClick={onRetry}
        >
          <RotateCw className="w-3.5 h-3.5 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

function PendingBanner({ label }: { label: string }) {
  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700"
    >
      <Loader2 className="w-3.5 h-3.5 animate-spin" />
      {label}
    </div>
  );
}

function VerifyDialog({
  patientId,
  defaultMobile,
  open,
  onOpenChange,
}: {
  patientId: string;
  defaultMobile?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [method, setMethod] = useState<AbdmAuthMethod>("MOBILE_OTP");
  const [identifier, setIdentifier] = useState(
    (defaultMobile ?? "").replace(/\D/g, "").slice(-10),
  );
  const [otp, setOtp] = useState("");
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [failure, setFailure] = useState<{
    step: "otp" | "verify";
    info: IntegrationFailure;
  } | null>(null);
  const [attempt, setAttempt] = useState(1);
  const [verified, setVerified] = useState(false);

  const close = (next: boolean) => {
    if (!next) {
      setTransactionId(null);
      setOtp("");
      setFailure(null);
      setAttempt(1);
      setVerified(false);
    }
    onOpenChange(next);
  };

  const sendOtp = useMutation({
    mutationFn: () => requestAbhaOtp(method, identifier),
    onSuccess: (challenge) => {
      setFailure(null);
      setTransactionId(challenge.transaction_id);
    },
    onError: (e: ApiError) =>
      setFailure({
        step: "otp",
        info: toIntegrationFailure(e, "Could not send the OTP."),
      }),
  });

  const verify = useMutation({
    mutationFn: () => verifyAbha(patientId, transactionId as string, otp),
    onSuccess: () => {
      setOtp("");
      setFailure(null);
      setVerified(true);
      toast({ title: "ABHA verified", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["abha-status", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patient", patientId] });
    },
    onError: (e: ApiError) => {
      setOtp(""); // an OTP is single-use - never keep a spent one around
      const info = toIntegrationFailure(e, "Verification failed.");
      // A wrong OTP can be corrected in place; an expired/unknown transaction
      // cannot, so send the user back to request a fresh OTP.
      if (e?.code === "ABDM_INVALID_TRANSACTION") setTransactionId(null);
      setFailure({ step: "verify", info });
    },
  });

  const isPending = sendOtp.isPending || verify.isPending;

  const runStep = (step: "otp" | "verify", isRetry: boolean) => {
    if (isRetry) setAttempt((n) => n + 1);
    else setAttempt(1);
    if (step === "otp") sendOtp.mutate();
    else verify.mutate();
  };

  const identifierValid =
    identifier.length === (method === "MOBILE_OTP" ? 10 : 12);

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Verify ABHA</DialogTitle>
          <DialogDescription>
            Verify the patient&apos;s identity with the ABDM gateway using an
            OTP.
          </DialogDescription>
        </DialogHeader>

        {verified ? (
          <div role="status" className="py-4 text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <p className="text-sm font-semibold text-slate-900">
              ABHA verified
            </p>
            <p className="text-xs text-slate-500">
              Link it to the patient record to finish.
            </p>
          </div>
        ) : (
          <>
            {!transactionId ? (
              <div className="space-y-3 py-2">
                <div className="flex gap-2">
                  {(["MOBILE_OTP", "AADHAAR_OTP"] as const).map((m) => (
                    <Button
                      key={m}
                      type="button"
                      size="sm"
                      variant={method === m ? "default" : "outline"}
                      disabled={isPending}
                      onClick={() => {
                        setMethod(m);
                        setIdentifier("");
                        setFailure(null);
                      }}
                    >
                      {m === "MOBILE_OTP" ? "Mobile OTP" : "Aadhaar OTP"}
                    </Button>
                  ))}
                </div>
                <Input
                  placeholder={
                    method === "MOBILE_OTP"
                      ? "10-digit mobile number"
                      : "12-digit Aadhaar number"
                  }
                  value={identifier}
                  disabled={isPending}
                  onChange={(e) =>
                    setIdentifier(
                      e.target.value.replace(/\D/g, "").slice(0, 12),
                    )
                  }
                  inputMode="numeric"
                  type={method === "AADHAAR_OTP" ? "password" : "text"}
                  autoComplete="off"
                />
              </div>
            ) : (
              <div className="space-y-3 py-2">
                <p className="text-xs text-slate-600">
                  Enter the 6-digit OTP sent by ABDM.
                </p>
                <Input
                  placeholder="000000"
                  value={otp}
                  disabled={isPending}
                  onChange={(e) =>
                    setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  className="text-center font-mono tracking-widest"
                  inputMode="numeric"
                  type="password"
                  autoComplete="one-time-code"
                  autoFocus
                />
              </div>
            )}

            {sendOtp.isPending && (
              <PendingBanner label="Requesting OTP from ABDM..." />
            )}
            {verify.isPending && (
              <PendingBanner label="Verifying with ABDM..." />
            )}
            {failure && !isPending && (
              <FailureBanner
                failure={failure.info}
                attempt={attempt}
                retrying={isPending}
                onRetry={() => runStep(failure.step, true)}
              />
            )}
          </>
        )}

        <DialogFooter>
          {verified ? (
            <Button type="button" size="sm" onClick={() => close(false)}>
              Done
            </Button>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => close(false)}
              >
                Cancel
              </Button>
              {!transactionId ? (
                <Button
                  type="button"
                  size="sm"
                  disabled={!identifierValid || isPending}
                  onClick={() => runStep("otp", false)}
                >
                  Send OTP
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  disabled={otp.length !== 6 || isPending}
                  onClick={() => runStep("verify", false)}
                >
                  Verify
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AbhaWorkflow({
  patientId,
  mobile,
}: {
  patientId: string;
  mobile?: string;
}) {
  const { hasPermission } = useAuth();
  const canLink = hasPermission("patients.link_abha");
  const canUnlink = hasPermission("patients.unlink_abha");
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [unlinkOpen, setUnlinkOpen] = useState(false);
  const [selectedPurpose, setSelectedPurpose] =
    useState<AbhaConsentPurpose>("CARE_MANAGEMENT");
  const [actionFailure, setActionFailure] = useState<IntegrationFailure | null>(
    null,
  );
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null);

  const statusQuery = useQuery({
    queryKey: ["abha-status", patientId],
    queryFn: () => getAbhaStatus(patientId),
    retry: false,
  });
  const gatewayQuery = useQuery({
    queryKey: ["abdm-status"],
    queryFn: getAbdmStatus,
    retry: false,
    staleTime: 60_000,
  });

  const handlers = (success: string) => ({
    onSuccess: () => {
      setActionFailure(null);
      setRetryAction(null);
      toast({ title: success, variant: "success" as const });
      queryClient.invalidateQueries({ queryKey: ["abha-status", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patient", patientId] });
    },
    onError: (e: ApiError) =>
      setActionFailure(toIntegrationFailure(e, "Action failed.")),
  });

  // Remembers the last action so a transient failure can be retried as-is.
  const runAction = (action: () => void) => {
    setRetryAction(() => action);
    action();
  };

  const link = useMutation({
    mutationFn: () => linkAbha(patientId),
    ...handlers("ABHA linked"),
  });
  const unlink = useMutation({
    mutationFn: () => unlinkAbha(patientId),
    ...handlers("ABHA unlinked"),
    onSettled: () => setUnlinkOpen(false),
  });
  const grant = useMutation({
    mutationFn: (purpose: AbhaConsentPurpose) =>
      grantAbhaConsent(patientId, purpose),
    ...handlers("Consent recorded"),
  });
  const revoke = useMutation({
    mutationFn: (consentId: string) => revokeAbhaConsent(patientId, consentId),
    ...handlers("Consent revoked"),
  });

  const abha = statusQuery.data;
  const gateway = gatewayQuery.data;
  const status = abha?.status ?? "UNVERIFIED";
  const consents = abha?.consents ?? [];
  const granted = new Set(
    consents.filter((c) => c.status === "GRANTED").map((c) => c.purpose),
  );
  const available = PURPOSES.filter((p) => !granted.has(p.value));
  const purpose = available.some((p) => p.value === selectedPurpose)
    ? selectedPurpose
    : available[0]?.value;

  return (
    <Card className="shadow-xs border-teal-200 bg-teal-50/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-600" />
          Ayushman Bharat Digital Mission (ABHA)
          <Badge variant="outline" className={STATUS_BADGE[status]}>
            {status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {statusQuery.isError ? (
          <p className="text-xs text-rose-600">Could not load ABHA status.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="ABHA Number" value={abha?.abha_number} />
              <Field label="ABHA Address" value={abha?.abha_address} />
              <Field
                label="ABDM Connection"
                value={
                  gateway
                    ? `${gateway.connected ? "Connected" : "Not connected"} (${gateway.mode})`
                    : gatewayQuery.isLoading
                      ? "Checking..."
                      : "Status unavailable"
                }
              />
              <Field
                label="Linked At"
                value={
                  abha?.linked_at && new Date(abha.linked_at).toLocaleString()
                }
              />
            </div>
            {gateway && !gateway.connected && gateway.message && (
              <p className="text-xs text-amber-700">{gateway.message}</p>
            )}

            {(canLink || canUnlink) && (
              <div className="flex flex-wrap gap-2">
                {canLink && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setVerifyOpen(true)}
                  >
                    <BadgeCheck className="w-3.5 h-3.5 mr-1" />
                    {status === "UNVERIFIED" ? "Verify ABHA" : "Re-verify"}
                  </Button>
                )}
                {canLink && status === "VERIFIED" && (
                  <Button
                    type="button"
                    size="sm"
                    disabled={link.isPending}
                    onClick={() => runAction(() => link.mutate())}
                  >
                    <Link2 className="w-3.5 h-3.5 mr-1" />
                    Link ABHA
                  </Button>
                )}
                {canUnlink && status !== "UNVERIFIED" && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setUnlinkOpen(true)}
                  >
                    <Link2Off className="w-3.5 h-3.5 mr-1" />
                    Unlink
                  </Button>
                )}
              </div>
            )}
            {(link.isPending ||
              unlink.isPending ||
              grant.isPending ||
              revoke.isPending) && (
              <PendingBanner label="Updating with ABDM..." />
            )}
            {actionFailure && (
              <FailureBanner
                failure={actionFailure}
                attempt={1}
                onRetry={retryAction ?? undefined}
              />
            )}

            {status === "UNVERIFIED" && (
              <p className="text-xs text-slate-500">
                This patient hasn&apos;t verified an ABHA yet. The internal
                Patient UID remains the permanent identifier regardless of ABHA
                status.
              </p>
            )}

            {status === "LINKED" && (
              <div className="space-y-2 border-t border-teal-100 pt-3">
                <p className="text-xs font-semibold text-teal-900">Consent</p>
                {consents.length === 0 && (
                  <p className="text-xs text-slate-500">No consent recorded.</p>
                )}
                <ul className="space-y-1.5">
                  {consents.map((c) => (
                    <li
                      key={c.id}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <span className="flex items-center gap-1.5">
                        {c.status === "GRANTED" ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <ShieldOff className="w-3.5 h-3.5 text-slate-400" />
                        )}
                        {PURPOSES.find((p) => p.value === c.purpose)?.label ??
                          c.purpose}
                        <span className="text-slate-400">
                          {c.status === "GRANTED"
                            ? `granted ${new Date(c.granted_at).toLocaleDateString()}`
                            : `revoked ${c.revoked_at ? new Date(c.revoked_at).toLocaleDateString() : ""}`}
                        </span>
                      </span>
                      {canLink && c.status === "GRANTED" && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={revoke.isPending}
                          onClick={() => runAction(() => revoke.mutate(c.id))}
                        >
                          Revoke
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
                {canLink && purpose && (
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      aria-label="Consent purpose"
                      className="h-8 rounded-md border border-slate-300 bg-white px-2 text-xs"
                      value={purpose}
                      onChange={(e) =>
                        setSelectedPurpose(e.target.value as AbhaConsentPurpose)
                      }
                    >
                      {available.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                    <Button
                      type="button"
                      size="sm"
                      disabled={grant.isPending}
                      onClick={() => runAction(() => grant.mutate(purpose))}
                    >
                      Record consent
                    </Button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>

      <VerifyDialog
        patientId={patientId}
        defaultMobile={mobile}
        open={verifyOpen}
        onOpenChange={setVerifyOpen}
      />
      <ConfirmDialog
        open={unlinkOpen}
        onOpenChange={setUnlinkOpen}
        title="Unlink ABHA?"
        description="This removes the ABHA number and address from the patient and revokes all active consents."
        confirmLabel="Unlink"
        isLoading={unlink.isPending}
        onConfirm={() => runAction(() => unlink.mutate())}
      />
    </Card>
  );
}
