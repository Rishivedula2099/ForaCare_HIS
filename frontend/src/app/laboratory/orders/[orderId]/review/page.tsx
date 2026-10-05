"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, FileCheck2, ShieldCheck, Stamp, XCircle } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { LabAccessRestricted } from "@/components/lab/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  amendResult,
  approveResults,
  finalizeOrder,
  getResultEntryForm,
  listApprovals,
  listResults,
  listVerifications,
  rejectApproval,
  rejectVerification,
  verifyResults,
} from "@/lib/lab-api";
import { ApiError } from "@/types/api";
import { Result } from "@/types/lab";

function flagTone(flag: string): string {
  if (flag === "CRITICAL") return "bg-rose-100 text-rose-800 border-rose-400 font-bold";
  if (flag === "HIGH" || flag === "LOW") return "bg-amber-50 text-amber-700 border-amber-300";
  if (flag === "NORMAL") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  return "bg-slate-100 text-slate-500 border-slate-300";
}

function formatDateTime(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function AmendRow({ result, canAmend }: { result: Result; canAmend: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [editing, setEditing] = React.useState(false);
  const [value, setValue] = React.useState(result.value);
  const [reason, setReason] = React.useState("");

  const amendMutation = useMutation({
    mutationFn: () => amendResult(result.id, value, reason, result.unit),
    onSuccess: () => {
      toast({ title: "Result amended", variant: "success" });
      setEditing(false);
      setReason("");
      queryClient.invalidateQueries({ queryKey: ["lab-results", result.labOrderId] });
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to amend result.", variant: "destructive" }),
  });

  return (
    <div className="border border-slate-200 rounded-md px-3 py-2.5 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-700">{result.value}</span>
          {result.unit && <span className="text-[11px] text-slate-400">{result.unit}</span>}
          <Badge variant="outline" className={flagTone(result.flag)}>
            {result.flag}
          </Badge>
          <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-300">
            {result.status}
          </Badge>
          <span className="text-[10px] text-slate-400">v{result.currentVersion}</span>
        </div>
        {canAmend && (
          <Button size="sm" variant="ghost" className="h-6 text-[11px]" onClick={() => setEditing((v) => !v)}>
            {editing ? "Cancel" : "Amend"}
          </Button>
        )}
      </div>
      {editing && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Input value={value} onChange={(e) => setValue(e.target.value)} className="text-xs max-w-32" />
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for amendment..."
            className="text-xs max-w-60"
          />
          <Button
            size="sm"
            className="text-xs"
            disabled={!value.trim() || !reason.trim() || amendMutation.isPending}
            onClick={() => amendMutation.mutate()}
          >
            {amendMutation.isPending ? "Saving..." : "Save Amendment"}
          </Button>
        </div>
      )}
    </div>
  );
}

function ReviewPageContent() {
  const { orderId } = useParams<{ orderId: string }>();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canView = hasPermission("lab.view");
  const canVerify = hasPermission("lab.verify_results");
  const canApprove = hasPermission("lab.approve_reports");

  const [verifyRemarks, setVerifyRemarks] = React.useState("");
  const [verifyRejectReason, setVerifyRejectReason] = React.useState("");
  const [approveRemarks, setApproveRemarks] = React.useState("");
  const [approveRejectReason, setApproveRejectReason] = React.useState("");

  const formQuery = useQuery({
    queryKey: ["result-entry-form", orderId],
    queryFn: () => getResultEntryForm(orderId),
    enabled: canView && !!orderId,
  });

  const resultsQuery = useQuery({
    queryKey: ["lab-results", orderId],
    queryFn: () => listResults(orderId),
    enabled: canView && !!orderId,
  });

  const verificationsQuery = useQuery({
    queryKey: ["lab-verifications", orderId],
    queryFn: () => listVerifications(orderId),
    enabled: canView && !!orderId,
  });

  const approvalsQuery = useQuery({
    queryKey: ["lab-approvals", orderId],
    queryFn: () => listApprovals(orderId),
    enabled: canView && !!orderId,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["result-entry-form", orderId] });
    queryClient.invalidateQueries({ queryKey: ["lab-results", orderId] });
    queryClient.invalidateQueries({ queryKey: ["lab-verifications", orderId] });
    queryClient.invalidateQueries({ queryKey: ["lab-approvals", orderId] });
  };

  const verifyMutation = useMutation({
    mutationFn: () => verifyResults(orderId, verifyRemarks || undefined),
    onSuccess: () => {
      toast({ title: "Results technically verified", variant: "success" });
      setVerifyRemarks("");
      invalidateAll();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to verify results.", variant: "destructive" }),
  });

  const rejectVerifyMutation = useMutation({
    mutationFn: () => rejectVerification(orderId, verifyRejectReason),
    onSuccess: () => {
      toast({ title: "Verification rejected", variant: "success" });
      setVerifyRejectReason("");
      invalidateAll();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to reject verification.", variant: "destructive" }),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveResults(orderId, approveRemarks || undefined),
    onSuccess: () => {
      toast({ title: "Results approved", variant: "success" });
      setApproveRemarks("");
      invalidateAll();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to approve results.", variant: "destructive" }),
  });

  const rejectApproveMutation = useMutation({
    mutationFn: () => rejectApproval(orderId, approveRejectReason),
    onSuccess: () => {
      toast({ title: "Approval rejected", variant: "success" });
      setApproveRejectReason("");
      invalidateAll();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to reject approval.", variant: "destructive" }),
  });

  const finalizeMutation = useMutation({
    mutationFn: () => finalizeOrder(orderId),
    onSuccess: () => {
      toast({ title: "Report finalized", variant: "success" });
      invalidateAll();
    },
    onError: (error: ApiError) => toast({ title: error?.message || "Unable to finalize order.", variant: "destructive" }),
  });

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Verification & Approval" description="Technical verification, approval, and finalization." />
        <LabAccessRestricted />
      </PageContainer>
    );
  }

  const form = formQuery.data;
  const status = form?.orderStatus;
  const canAmend = canApprove && (status === "APPROVED" || status === "FINALIZED");

  return (
    <PageContainer>
      <PageHeader
        title="Verification & Approval"
        description="Technician workflow: technical verification, authorized approval, and finalization."
        actions={
          <div className="flex items-center gap-2">
            {(status === "APPROVED" || status === "FINALIZED") && (
              <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
                <Link href={`/laboratory/orders/${orderId}/report`} target="_blank" rel="noopener noreferrer">
                  View Report
                </Link>
              </Button>
            )}
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/laboratory/accessioning">
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Accessioning
              </Link>
            </Button>
          </div>
        }
      />

      {formQuery.isLoading && <p className="text-xs text-slate-400">Loading...</p>}
      {formQuery.isError && (
        <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
          {(formQuery.error as Error | null)?.message || "Unable to load this order."}
        </p>
      )}

      {form && (
        <div className="space-y-4">
          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">{form.testName}</h2>
                  <p className="text-[11px] text-slate-500 font-mono">{form.orderNumber}</p>
                </div>
                <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-300">
                  {form.orderStatus}
                </Badge>
              </div>

              <div className="space-y-2">
                {(resultsQuery.data ?? []).length === 0 ? (
                  <p className="text-xs text-slate-400">No results entered yet.</p>
                ) : (
                  (resultsQuery.data ?? []).map((result) => (
                    <AmendRow key={result.id} result={result} canAmend={canAmend} />
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {status === "RESULT_ENTERED" && (
            <Card className="shadow-xs border-slate-200">
              <CardContent className="p-4 space-y-3">
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                  Technical Verification
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    value={verifyRemarks}
                    onChange={(e) => setVerifyRemarks(e.target.value)}
                    placeholder="Remarks (optional)..."
                    className="text-xs max-w-60"
                  />
                  <Button
                    size="sm"
                    className="text-xs gap-1"
                    disabled={!canVerify || verifyMutation.isPending}
                    onClick={() => verifyMutation.mutate()}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verify & Queue for Approval
                  </Button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    value={verifyRejectReason}
                    onChange={(e) => setVerifyRejectReason(e.target.value)}
                    placeholder="Rejection reason..."
                    className="text-xs max-w-60"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs gap-1"
                    disabled={!canVerify || !verifyRejectReason.trim() || rejectVerifyMutation.isPending}
                    onClick={() => rejectVerifyMutation.mutate()}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject (send back)
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {status === "PENDING_APPROVAL" && (
            <Card className="shadow-xs border-slate-200">
              <CardContent className="p-4 space-y-3">
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                  <FileCheck2 className="w-3.5 h-3.5 text-slate-400" />
                  Authorized Approval
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    value={approveRemarks}
                    onChange={(e) => setApproveRemarks(e.target.value)}
                    placeholder="Remarks (optional)..."
                    className="text-xs max-w-60"
                  />
                  <Button
                    size="sm"
                    className="text-xs gap-1"
                    disabled={!canApprove || approveMutation.isPending}
                    onClick={() => approveMutation.mutate()}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Approve
                  </Button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    value={approveRejectReason}
                    onChange={(e) => setApproveRejectReason(e.target.value)}
                    placeholder="Rejection reason..."
                    className="text-xs max-w-60"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs gap-1"
                    disabled={!canApprove || !approveRejectReason.trim() || rejectApproveMutation.isPending}
                    onClick={() => rejectApproveMutation.mutate()}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject (send back)
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {status === "APPROVED" && (
            <Card className="shadow-xs border-slate-200">
              <CardContent className="p-4 space-y-3">
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                  <Stamp className="w-3.5 h-3.5 text-slate-400" />
                  Finalization
                </h2>
                <Button
                  size="sm"
                  className="text-xs gap-1"
                  disabled={!canApprove || finalizeMutation.isPending}
                  onClick={() => finalizeMutation.mutate()}
                >
                  <Stamp className="w-3.5 h-3.5" />
                  {finalizeMutation.isPending ? "Finalizing..." : "Finalize Report"}
                </Button>
              </CardContent>
            </Card>
          )}

          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-4 space-y-3">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">History</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Verifications</div>
                  <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
                    {(verificationsQuery.data ?? []).length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-400">None yet.</div>
                    ) : (
                      (verificationsQuery.data ?? []).map((v) => (
                        <div key={v.id} className="flex items-center justify-between px-3 py-1.5">
                          <Badge
                            variant="outline"
                            className={
                              v.status === "REJECTED"
                                ? "bg-rose-50 text-rose-700 border-rose-300"
                                : "bg-emerald-50 text-emerald-700 border-emerald-300"
                            }
                          >
                            {v.status}
                          </Badge>
                          <span className="text-[11px] text-slate-500">{formatDateTime(v.verifiedAt)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">Approvals</div>
                  <div className="border border-slate-200 rounded-md divide-y divide-slate-100">
                    {(approvalsQuery.data ?? []).length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-400">None yet.</div>
                    ) : (
                      (approvalsQuery.data ?? []).map((a) => (
                        <div key={a.id} className="flex items-center justify-between px-3 py-1.5">
                          <Badge
                            variant="outline"
                            className={
                              a.status === "REJECTED"
                                ? "bg-rose-50 text-rose-700 border-rose-300"
                                : "bg-emerald-50 text-emerald-700 border-emerald-300"
                            }
                          >
                            {a.status}
                          </Badge>
                          <span className="text-[11px] text-slate-500">{formatDateTime(a.approvedAt)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </PageContainer>
  );
}

export default function ReviewPage() {
  return (
    <AppShell>
      <ReviewPageContent />
    </AppShell>
  );
}
