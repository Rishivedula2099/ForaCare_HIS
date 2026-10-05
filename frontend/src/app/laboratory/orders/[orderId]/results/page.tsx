"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { LabAccessRestricted } from "@/components/lab/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { enterResults, getResultEntryForm } from "@/lib/lab-api";
import { ApiError } from "@/types/api";
import { ResultEntryField, ResultEntryForm, ResultFlag } from "@/types/lab";

/** Client-side mirror of `service._calculate_flag` - purely for live
 * "critical-value display" feedback while the tech types; the server
 * recomputes authoritatively on submit and this preview is discarded. */
function previewFlag(value: string, field: ResultEntryField): ResultFlag | null {
  if (!value.trim()) return null;
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return null;
  if (field.criticalLow !== undefined && numeric < field.criticalLow) return "CRITICAL";
  if (field.criticalHigh !== undefined && numeric > field.criticalHigh) return "CRITICAL";
  if (field.normalMin !== undefined && numeric < field.normalMin) return "LOW";
  if (field.normalMax !== undefined && numeric > field.normalMax) return "HIGH";
  if (field.normalMin !== undefined && field.normalMax !== undefined) return "NORMAL";
  return null;
}

function flagTone(flag: ResultFlag | null): string {
  if (flag === "CRITICAL") return "bg-rose-100 text-rose-800 border-rose-400 font-bold";
  if (flag === "HIGH" || flag === "LOW") return "bg-amber-50 text-amber-700 border-amber-300";
  if (flag === "NORMAL") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  return "bg-slate-100 text-slate-500 border-slate-300";
}

function referenceRangeLabel(field: ResultEntryField): string {
  if (field.normalMin === undefined || field.normalMax === undefined) return "No reference range on file";
  return `${field.normalMin} – ${field.normalMax}${field.unit ? ` ${field.unit}` : ""}`;
}

type EntryState = Record<string, { value: string; unit: string }>;

function ResultEntryFormBody({ form, canEnter }: { form: ResultEntryForm; canEnter: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const isEditable = form.orderStatus === "PROCESSING";

  const [entries, setEntries] = React.useState<EntryState>(() =>
    Object.fromEntries(
      form.fields.map((field) => [field.parameterId, { value: field.value ?? "", unit: field.unit ?? "" }])
    )
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const submitMutation = useMutation({
    mutationFn: () =>
      enterResults(
        form.labOrderId,
        form.fields.map((field) => ({
          parameter_id: field.parameterId,
          value: entries[field.parameterId]?.value ?? "",
          unit: entries[field.parameterId]?.unit || undefined,
        }))
      ),
    onSuccess: () => {
      toast({ title: "Results submitted", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["result-entry-form", form.labOrderId] });
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to submit results."),
  });

  const hasCritical = Object.entries(entries).some(([parameterId, entry]) => {
    const field = form.fields.find((f) => f.parameterId === parameterId);
    return field && previewFlag(entry.value, field) === "CRITICAL";
  });

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">{form.testName}</h2>
            <p className="text-[11px] text-slate-500 font-mono">{form.orderNumber}</p>
          </div>
          <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-300">
            {form.orderStatus}
          </Badge>
        </div>

        {!isEditable && (
          <p className="text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-md px-3 py-2">
            This order is no longer PROCESSING, so these results are read-only.
          </p>
        )}

        {hasCritical && isEditable && (
          <div className="flex items-center gap-2 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-800">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            One or more values are outside the critical range. Double-check before submitting.
          </div>
        )}

        <div className="space-y-3">
          {form.fields.map((field) => {
            const entry = entries[field.parameterId] ?? { value: "", unit: "" };
            const flag = field.flag ?? previewFlag(entry.value, field);
            return (
              <div
                key={field.parameterId}
                className="grid grid-cols-[1fr_auto] items-center gap-3 border border-slate-200 rounded-md px-3 py-2.5"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900">{field.name}</span>
                    <span className="text-[10px] font-mono text-slate-400">{field.parameterCode}</span>
                  </div>
                  <div className="text-[10px] text-slate-400">Reference: {referenceRangeLabel(field)}</div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={entry.value}
                      disabled={!isEditable || !canEnter}
                      onChange={(e) =>
                        setEntries((prev) => ({
                          ...prev,
                          [field.parameterId]: { ...prev[field.parameterId], value: e.target.value },
                        }))
                      }
                      placeholder="Value"
                      className="text-xs max-w-40"
                    />
                    <Input
                      value={entry.unit}
                      disabled={!isEditable || !canEnter}
                      onChange={(e) =>
                        setEntries((prev) => ({
                          ...prev,
                          [field.parameterId]: { ...prev[field.parameterId], unit: e.target.value },
                        }))
                      }
                      placeholder={field.unit || "Unit"}
                      className="text-xs max-w-24"
                    />
                  </div>
                </div>
                <Badge variant="outline" className={flagTone(flag ?? null)}>
                  {flag ?? "—"}
                </Badge>
              </div>
            );
          })}
        </div>

        {formError && (
          <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
            {formError}
          </p>
        )}

        {isEditable && (
          <Button
            size="sm"
            className="text-xs"
            disabled={!canEnter || submitMutation.isPending}
            onClick={() => {
              setFormError(null);
              submitMutation.mutate();
            }}
          >
            {submitMutation.isPending ? "Submitting..." : "Submit Results"}
          </Button>
        )}

        {!isEditable && (
          <Button variant="outline" size="sm" className="text-xs" asChild>
            <Link href={`/laboratory/orders/${form.labOrderId}/review`}>Go to Verification & Approval</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ResultEntryPageContent() {
  const { orderId } = useParams<{ orderId: string }>();
  const { hasPermission } = useAuth();
  const canView = hasPermission("lab.view");
  const canEnter = hasPermission("lab.enter_results");

  const formQuery = useQuery({
    queryKey: ["result-entry-form", orderId],
    queryFn: () => getResultEntryForm(orderId),
    enabled: canView && !!orderId,
  });

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Result Entry" description="Enter and review lab test results." />
        <LabAccessRestricted />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Result Entry"
        description="Dynamic parameter fields, units, reference ranges, and critical-value flags."
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/laboratory/accessioning">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Accessioning
            </Link>
          </Button>
        }
      />

      {formQuery.isLoading && <p className="text-xs text-slate-400">Loading...</p>}
      {formQuery.isError && (
        <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
          {(formQuery.error as Error | null)?.message || "Unable to load this order."}
        </p>
      )}
      {formQuery.data && (
        <ResultEntryFormBody key={formQuery.data.orderStatus} form={formQuery.data} canEnter={canEnter} />
      )}
    </PageContainer>
  );
}

export default function ResultEntryPage() {
  return (
    <AppShell>
      <ResultEntryPageContent />
    </AppShell>
  );
}
