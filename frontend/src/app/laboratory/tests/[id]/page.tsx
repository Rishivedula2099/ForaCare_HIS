"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ListPlus, Plus, Ruler } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { LabAccessRestricted } from "@/components/lab/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  createParameter,
  createReferenceRange,
  getTest,
  listParameters,
  listReferenceRanges,
  toParameterCreatePayload,
  toReferenceRangeCreatePayload,
  updateParameter,
  updateReferenceRange,
} from "@/lib/lab-api";
import { ApiError } from "@/types/api";
import {
  CONTAINER_TYPES,
  LabParameter,
  LabParameterFormData,
  LabReferenceRange,
  LabReferenceRangeFormData,
  REFERENCE_RANGE_GENDERS,
  SPECIMEN_TYPES,
} from "@/types/lab";

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

// ---------------------------------------------------------------------------
// Reference Ranges dialog (per parameter)
// ---------------------------------------------------------------------------

const EMPTY_RANGE_FORM: LabReferenceRangeFormData = {
  gender: "ALL",
  ageMinDays: "0",
  ageMaxDays: "",
  normalMin: "",
  normalMax: "",
  criticalLow: "",
  criticalHigh: "",
};

function ReferenceRangeForm({
  parameterId,
  editingRange,
  onDone,
}: {
  parameterId: string;
  editingRange: LabReferenceRange | null;
  onDone: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [formData, setFormData] = React.useState<LabReferenceRangeFormData>(
    editingRange
      ? {
          gender: editingRange.gender,
          ageMinDays: String(editingRange.ageMinDays),
          ageMaxDays: editingRange.ageMaxDays !== undefined ? String(editingRange.ageMaxDays) : "",
          normalMin: String(editingRange.normalMin),
          normalMax: String(editingRange.normalMax),
          criticalLow: editingRange.criticalLow !== undefined ? String(editingRange.criticalLow) : "",
          criticalHigh: editingRange.criticalHigh !== undefined ? String(editingRange.criticalHigh) : "",
        }
      : EMPTY_RANGE_FORM
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => createReferenceRange(parameterId, toReferenceRangeCreatePayload(formData)),
    onSuccess: () => {
      toast({ title: "Reference range added", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-reference-ranges", parameterId] });
      onDone();
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to add this reference range."),
  });

  const updateMutation = useMutation({
    mutationFn: () => updateReferenceRange(editingRange!.id, toReferenceRangeCreatePayload(formData)),
    onSuccess: () => {
      toast({ title: "Reference range updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-reference-ranges", parameterId] });
      onDone();
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update this reference range."),
  });

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const normalMin = Number(formData.normalMin);
    const normalMax = Number(formData.normalMax);
    if (formData.normalMin.trim() === "" || formData.normalMax.trim() === "" || Number.isNaN(normalMin) || Number.isNaN(normalMax)) {
      setFormError("Enter valid normal min/max values.");
      return;
    }
    if (normalMin >= normalMax) {
      setFormError("Normal min must be less than normal max.");
      return;
    }
    if (editingRange) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 border border-slate-200 rounded-md p-3 bg-slate-50/40">
      <div className="grid grid-cols-3 gap-2.5">
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Gender</label>
          <Select
            options={REFERENCE_RANGE_GENDERS.map((g) => ({ value: g.value, label: g.label }))}
            value={formData.gender}
            onChange={(value) => setFormData((f) => ({ ...f, gender: value as LabReferenceRangeFormData["gender"] }))}
          />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Age Min (days)</label>
          <Input
            type="number"
            min="0"
            value={formData.ageMinDays}
            onChange={(e) => setFormData((f) => ({ ...f, ageMinDays: e.target.value }))}
            className="text-xs"
          />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Age Max (days, optional)</label>
          <Input
            type="number"
            min="0"
            value={formData.ageMaxDays}
            onChange={(e) => setFormData((f) => ({ ...f, ageMaxDays: e.target.value }))}
            placeholder="No upper limit"
            className="text-xs"
          />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2.5">
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Normal Min</label>
          <Input type="number" step="0.001" value={formData.normalMin} onChange={(e) => setFormData((f) => ({ ...f, normalMin: e.target.value }))} className="text-xs" />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Normal Max</label>
          <Input type="number" step="0.001" value={formData.normalMax} onChange={(e) => setFormData((f) => ({ ...f, normalMax: e.target.value }))} className="text-xs" />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Critical Low (optional)</label>
          <Input type="number" step="0.001" value={formData.criticalLow} onChange={(e) => setFormData((f) => ({ ...f, criticalLow: e.target.value }))} className="text-xs" />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-slate-600 block mb-1">Critical High (optional)</label>
          <Input type="number" step="0.001" value={formData.criticalHigh} onChange={(e) => setFormData((f) => ({ ...f, criticalHigh: e.target.value }))} className="text-xs" />
        </div>
      </div>

      {formError && (
        <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
          {formError}
        </p>
      )}

      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="outline" size="sm" className="text-xs" onClick={onDone} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" size="sm" className="text-xs" disabled={isSaving}>
          {isSaving ? "Saving..." : editingRange ? "Save Changes" : "Add Range"}
        </Button>
      </div>
    </form>
  );
}

function ReferenceRangesDialog({
  open,
  onOpenChange,
  parameter,
  canManage,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  parameter: LabParameter | null;
  canManage: boolean;
}) {
  const [showForm, setShowForm] = React.useState(false);
  const [editingRange, setEditingRange] = React.useState<LabReferenceRange | null>(null);

  const rangesQuery = useQuery({
    queryKey: ["lab-reference-ranges", parameter?.id],
    queryFn: () => listReferenceRanges(parameter!.id),
    enabled: !!parameter && open,
  });
  const ranges = rangesQuery.data ?? [];

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) { setShowForm(false); setEditingRange(null); } onOpenChange(next); }}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Reference Ranges — {parameter?.name}</DialogTitle>
          <DialogDescription>Normal/critical bands by gender and age, used to flag results.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Gender</TableHead>
                  <TableHead>Age (days)</TableHead>
                  <TableHead className="text-right">Normal Range</TableHead>
                  <TableHead className="text-right">Critical Range</TableHead>
                  {canManage && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {ranges.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={canManage ? 5 : 4} className="text-center text-xs text-slate-400 py-6">
                      {rangesQuery.isLoading ? "Loading ranges..." : "No reference ranges defined yet."}
                    </TableCell>
                  </TableRow>
                ) : (
                  ranges.map((range) => (
                    <TableRow key={range.id}>
                      <TableCell className="text-xs font-semibold text-slate-900">
                        {REFERENCE_RANGE_GENDERS.find((g) => g.value === range.gender)?.label ?? range.gender}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {range.ageMinDays} – {range.ageMaxDays ?? "∞"}
                      </TableCell>
                      <TableCell className="text-right text-xs text-slate-900">
                        {range.normalMin} – {range.normalMax}
                      </TableCell>
                      <TableCell className="text-right text-xs text-rose-700">
                        {range.criticalLow ?? "—"} / {range.criticalHigh ?? "—"}
                      </TableCell>
                      {canManage && (
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => { setEditingRange(range); setShowForm(true); }}
                          >
                            Edit
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {canManage && !showForm && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => { setEditingRange(null); setShowForm(true); }}
            >
              <Plus className="w-3.5 h-3.5" />
              Add Reference Range
            </Button>
          )}

          {canManage && showForm && parameter && (
            <ReferenceRangeForm
              key={editingRange?.id ?? "new"}
              parameterId={parameter.id}
              editingRange={editingRange}
              onDone={() => { setShowForm(false); setEditingRange(null); }}
            />
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Add/edit Parameter dialog
// ---------------------------------------------------------------------------

const EMPTY_PARAMETER_FORM: LabParameterFormData = { parameterCode: "", name: "", unit: "", sequenceOrder: "0" };

function ParameterDialog({
  open,
  onOpenChange,
  testId,
  editingParameter,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  editingParameter: LabParameter | null;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [formData, setFormData] = React.useState<LabParameterFormData>(
    editingParameter
      ? {
          parameterCode: editingParameter.parameterCode,
          name: editingParameter.name,
          unit: editingParameter.unit ?? "",
          sequenceOrder: String(editingParameter.sequenceOrder),
        }
      : EMPTY_PARAMETER_FORM
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: LabParameterFormData) => createParameter(testId, toParameterCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Parameter added", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-parameters", testId] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to add this parameter."),
  });

  const updateMutation = useMutation({
    mutationFn: (data: LabParameterFormData) =>
      updateParameter(editingParameter!.id, {
        name: data.name.trim(),
        unit: data.unit.trim() || null,
        sequence_order: Number(data.sequenceOrder || "0"),
      }),
    onSuccess: () => {
      toast({ title: "Parameter updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-parameters", testId] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update this parameter."),
  });

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formData.parameterCode.trim() || !formData.name.trim()) {
      setFormError("Parameter code and name are required.");
      return;
    }
    if (editingParameter) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingParameter ? "Edit Parameter" : "Add Parameter"}</DialogTitle>
          <DialogDescription>
            {editingParameter ? "Update this parameter's details." : "Add a reportable analyte to this test."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Parameter Name</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Hemoglobin"
              className="text-xs"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Code</label>
              <Input
                value={formData.parameterCode}
                onChange={(e) => setFormData((f) => ({ ...f, parameterCode: e.target.value }))}
                placeholder="e.g. HB"
                disabled={!!editingParameter}
                className="text-xs font-mono uppercase"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Unit (optional)</label>
              <Input
                value={formData.unit}
                onChange={(e) => setFormData((f) => ({ ...f, unit: e.target.value }))}
                placeholder="e.g. g/dL"
                className="text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Order</label>
              <Input
                type="number"
                min="0"
                value={formData.sequenceOrder}
                onChange={(e) => setFormData((f) => ({ ...f, sequenceOrder: e.target.value }))}
                className="text-xs"
              />
            </div>
          </div>

          {formError && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {formError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isSaving}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSaving}>
              {isSaving ? "Saving..." : editingParameter ? "Save Changes" : "Add Parameter"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function TestDetailContent({ testId }: { testId: string }) {
  const { hasPermission } = useAuth();
  const canView = hasPermission("lab.view");
  const canManage = hasPermission("lab.manage_master");

  const [parameterDialogOpen, setParameterDialogOpen] = React.useState(false);
  const [editingParameter, setEditingParameter] = React.useState<LabParameter | null>(null);
  const [rangesDialogParameter, setRangesDialogParameter] = React.useState<LabParameter | null>(null);

  const testQuery = useQuery({ queryKey: ["lab-test", testId], queryFn: () => getTest(testId), enabled: canView });
  const test = testQuery.data;

  const parametersQuery = useQuery({
    queryKey: ["lab-parameters", testId],
    queryFn: () => listParameters(testId),
    enabled: canView,
  });
  const parameters = parametersQuery.data ?? [];

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Test Detail" description="Parameters and reference ranges for this test." />
        <LabAccessRestricted />
      </PageContainer>
    );
  }

  if (testQuery.isLoading) {
    return <p className="text-xs text-slate-400 py-8 text-center">Loading test...</p>;
  }
  if (testQuery.isError || !test) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
        Test not found, or you don&apos;t have access to it.
      </div>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={test.name}
        description={`Test code ${test.testCode}`}
        actions={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <Link href="/laboratory">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Laboratory
            </Link>
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        <Badge variant={test.isActive ? "completed" : "alert"}>{test.isActive ? "Active" : "Inactive"}</Badge>
      </div>

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Overview</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-[10px] text-slate-500 block">Specimen</span>
              <span className="font-semibold text-slate-900">
                {SPECIMEN_TYPES.find((s) => s.value === test.specimenType)?.label ?? test.specimenType}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Container</span>
              <span className="font-semibold text-slate-900">
                {CONTAINER_TYPES.find((c) => c.value === test.containerType)?.label ?? test.containerType}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Turnaround Time</span>
              <span className="font-semibold text-slate-900">{test.tatMinutes} minutes</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block">Unit Price</span>
              <span className="font-semibold text-slate-900">{currency(test.unitPrice)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <ListPlus className="w-4 h-4 text-slate-500" />
              Parameters
            </h3>
            {canManage && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => { setEditingParameter(null); setParameterDialogOpen(true); }}
              >
                <Plus className="w-3.5 h-3.5" />
                Add Parameter
              </Button>
            )}
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead className="text-right">Order</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {parameters.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-xs text-slate-400 py-6">
                      {parametersQuery.isLoading ? "Loading parameters..." : "No parameters defined yet."}
                    </TableCell>
                  </TableRow>
                ) : (
                  parameters.map((parameter) => (
                    <TableRow key={parameter.id}>
                      <TableCell className="text-xs font-semibold text-slate-900">{parameter.name}</TableCell>
                      <TableCell className="text-xs font-mono text-slate-600">{parameter.parameterCode}</TableCell>
                      <TableCell className="text-xs text-slate-500">{parameter.unit || "—"}</TableCell>
                      <TableCell className="text-right text-xs text-slate-600">{parameter.sequenceOrder}</TableCell>
                      <TableCell>
                        <Badge variant={parameter.isActive ? "completed" : "alert"}>
                          {parameter.isActive ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs gap-1"
                          onClick={() => setRangesDialogParameter(parameter)}
                        >
                          <Ruler className="w-3 h-3" />
                          Ranges
                        </Button>
                        {canManage && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => { setEditingParameter(parameter); setParameterDialogOpen(true); }}
                          >
                            Edit
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <ParameterDialog
        key={`${parameterDialogOpen}-${editingParameter?.id ?? "new"}`}
        open={parameterDialogOpen}
        onOpenChange={setParameterDialogOpen}
        testId={testId}
        editingParameter={editingParameter}
      />
      <ReferenceRangesDialog
        open={!!rangesDialogParameter}
        onOpenChange={(open) => !open && setRangesDialogParameter(null)}
        parameter={rangesDialogParameter}
        canManage={canManage}
      />
    </PageContainer>
  );
}

export default function TestDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <AppShell>
      <TestDetailContent testId={params.id} />
    </AppShell>
  );
}
