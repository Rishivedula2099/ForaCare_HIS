"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Plus } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { LabAccessRestricted } from "@/components/lab/access-restricted";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SearchInput } from "@/components/ui/search-input";
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
import { listDepartments } from "@/lib/department-api";
import { createTest, listTests, toTestCreatePayload, updateTest } from "@/lib/lab-api";
import { ApiError } from "@/types/api";
import { CONTAINER_TYPES, LabTest, LabTestFormData, SPECIMEN_TYPES } from "@/types/lab";

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

const EMPTY_TEST_FORM: LabTestFormData = {
  testCode: "",
  name: "",
  specimenType: "EDTA_BLOOD",
  containerType: "LAVENDER_TOP",
  departmentId: "",
  tatMinutes: "60",
  unitPrice: "0",
};

function TestDialog({
  open,
  onOpenChange,
  editingTest,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingTest: LabTest | null;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => listDepartments(), enabled: open });

  // The parent remounts this dialog (via a `key` on open-state + the test
  // being edited), so this initializer runs fresh instead of needing an
  // effect to reset it - see the equivalent note in
  // frontend/src/app/billing/page.tsx's ServiceDialog.
  const [formData, setFormData] = React.useState<LabTestFormData>(
    editingTest
      ? {
          testCode: editingTest.testCode,
          name: editingTest.name,
          specimenType: editingTest.specimenType,
          containerType: editingTest.containerType,
          departmentId: editingTest.departmentId ?? "",
          tatMinutes: String(editingTest.tatMinutes),
          unitPrice: String(editingTest.unitPrice),
        }
      : EMPTY_TEST_FORM
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: LabTestFormData) => createTest(toTestCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Test created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-tests"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to create test."),
  });

  const updateMutation = useMutation({
    mutationFn: (data: LabTestFormData) =>
      updateTest(editingTest!.id, {
        name: data.name.trim(),
        specimen_type: data.specimenType,
        container_type: data.containerType,
        department_id: data.departmentId || null,
        tat_minutes: Number(data.tatMinutes || "60"),
        unit_price: Number(data.unitPrice || "0"),
      }),
    onSuccess: () => {
      toast({ title: "Test updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["lab-tests"] });
      onOpenChange(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update test."),
  });

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formData.testCode.trim() || !formData.name.trim()) {
      setFormError("Test code and name are required.");
      return;
    }
    const tat = Number(formData.tatMinutes);
    if (!formData.tatMinutes || Number.isNaN(tat) || tat <= 0) {
      setFormError("Enter a valid turnaround time greater than zero.");
      return;
    }
    const price = Number(formData.unitPrice);
    if (formData.unitPrice.trim() === "" || Number.isNaN(price) || price < 0) {
      setFormError("Enter a valid unit price.");
      return;
    }
    if (editingTest) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingTest ? "Edit Test" : "Add Test"}</DialogTitle>
          <DialogDescription>
            {editingTest ? "Update this test's details." : "Add a new orderable test to the master."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] font-semibold text-slate-700 block mb-1">Test Name</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Complete Blood Count"
              className="text-xs"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Test Code</label>
              <Input
                value={formData.testCode}
                onChange={(e) => setFormData((f) => ({ ...f, testCode: e.target.value }))}
                placeholder="e.g. CBC"
                disabled={!!editingTest}
                className="text-xs font-mono uppercase"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Turnaround (minutes)</label>
              <Input
                type="number"
                min="1"
                value={formData.tatMinutes}
                onChange={(e) => setFormData((f) => ({ ...f, tatMinutes: e.target.value }))}
                className="text-xs"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Specimen Type</label>
              <Select
                options={SPECIMEN_TYPES.map((s) => ({ value: s.value, label: s.label }))}
                value={formData.specimenType}
                onChange={(value) => setFormData((f) => ({ ...f, specimenType: value as LabTestFormData["specimenType"] }))}
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Container Type</label>
              <Select
                options={CONTAINER_TYPES.map((c) => ({ value: c.value, label: c.label }))}
                value={formData.containerType}
                onChange={(value) => setFormData((f) => ({ ...f, containerType: value as LabTestFormData["containerType"] }))}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Department (optional)</label>
              <Select
                options={(departmentsQuery.data ?? []).map((d) => ({ value: d.id, label: d.name }))}
                value={formData.departmentId}
                onChange={(value) => setFormData((f) => ({ ...f, departmentId: value }))}
                placeholder="Select a department"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Unit Price</label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={formData.unitPrice}
                onChange={(e) => setFormData((f) => ({ ...f, unitPrice: e.target.value }))}
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
              {isSaving ? "Saving..." : editingTest ? "Save Changes" : "Add Test"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LabPageContent() {
  const { hasPermission } = useAuth();
  const canView = hasPermission("lab.view");
  const canManage = hasPermission("lab.manage_master");
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = React.useState("");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingTest, setEditingTest] = React.useState<LabTest | null>(null);

  const testsQuery = useQuery({
    queryKey: ["lab-tests", searchQuery],
    queryFn: () => listTests({ name: searchQuery || undefined }),
    enabled: canView,
  });
  const tests = testsQuery.data ?? [];

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updateTest(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lab-tests"] }),
  });

  if (!canView) {
    return (
      <PageContainer>
        <PageHeader title="Laboratory" description="Test master, parameters, and reference ranges." />
        <LabAccessRestricted />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Laboratory"
        description="Test master, parameters, and reference ranges."
        actions={
          canManage ? (
            <Button size="sm" className="gap-1.5 text-xs" onClick={() => { setEditingTest(null); setDialogOpen(true); }}>
              <Plus className="w-3.5 h-3.5" />
              Add Test
            </Button>
          ) : undefined
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <SearchInput
            placeholder="Search tests by name..."
            onSearchChange={setSearchQuery}
            isLoading={testsQuery.isFetching}
            className="max-w-sm"
          />

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Test</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Specimen</TableHead>
                  <TableHead>Container</TableHead>
                  <TableHead className="text-right">TAT (min)</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tests.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-xs text-slate-400 py-8">
                      {testsQuery.isLoading ? "Loading tests..." : "No tests found."}
                    </TableCell>
                  </TableRow>
                ) : (
                  tests.map((test) => (
                    <TableRow key={test.id}>
                      <TableCell className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                        <FlaskConical className="w-3.5 h-3.5 text-slate-400" />
                        <Link href={`/laboratory/tests/${test.id}`} className="hover:underline">
                          {test.name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-700">{test.testCode}</TableCell>
                      <TableCell className="text-xs text-slate-500">
                        {SPECIMEN_TYPES.find((s) => s.value === test.specimenType)?.label ?? test.specimenType}
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">
                        {CONTAINER_TYPES.find((c) => c.value === test.containerType)?.label ?? test.containerType}
                      </TableCell>
                      <TableCell className="text-right text-xs text-slate-600">{test.tatMinutes}</TableCell>
                      <TableCell className="text-right text-xs font-semibold text-slate-900">{currency(test.unitPrice)}</TableCell>
                      <TableCell>
                        <button
                          type="button"
                          disabled={!canManage || toggleActiveMutation.isPending}
                          onClick={() => toggleActiveMutation.mutate({ id: test.id, isActive: !test.isActive })}
                        >
                          <Badge
                            variant="outline"
                            className={
                              test.isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                : "bg-slate-100 text-slate-500 border-slate-300"
                            }
                          >
                            {test.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={!canManage}
                          className="h-7 text-xs"
                          onClick={() => { setEditingTest(test); setDialogOpen(true); }}
                        >
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <TestDialog
        key={`${dialogOpen}-${editingTest?.id ?? "new"}`}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingTest={editingTest}
      />
    </PageContainer>
  );
}

export default function LaboratoryPage() {
  return (
    <AppShell>
      <LabPageContent />
    </AppShell>
  );
}
