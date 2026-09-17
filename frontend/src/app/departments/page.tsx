"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus, Pencil } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import {
  createDepartment,
  listDepartments,
  toCreatePayload,
  updateDepartment,
} from "@/lib/department-api";
import { Department, DepartmentFormData } from "@/types/department";
import { ApiError } from "@/types/api";

const EMPTY_FORM: DepartmentFormData = { name: "", code: "", description: "" };

function DepartmentsPageContent() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("departments.manage");

  const [searchQuery, setSearchQuery] = React.useState("");
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [editingDepartment, setEditingDepartment] = React.useState<Department | null>(null);
  const [formData, setFormData] = React.useState<DepartmentFormData>(EMPTY_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);

  const departmentsQuery = useQuery({
    queryKey: ["departments", searchQuery],
    queryFn: () => listDepartments({ name: searchQuery || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: (data: DepartmentFormData) => createDepartment(toCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Department created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to create department.");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: DepartmentFormData }) =>
      updateDepartment(id, {
        name: data.name.trim(),
        description: data.description.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Department updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to update department.");
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateDepartment(id, { is_active: isActive }),
    onSuccess: () => {
      toast({ title: "Department status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: () => {
      toast({ title: "Unable to update department status", variant: "destructive" });
    },
  });

  const openCreateDialog = () => {
    setEditingDepartment(null);
    setFormData(EMPTY_FORM);
    setFormError(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (department: Department) => {
    setEditingDepartment(department);
    setFormData({
      name: department.name,
      code: department.code,
      description: department.description || "",
    });
    setFormError(null);
    setIsDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.name.trim() || !formData.code.trim()) {
      setFormError("Name and code are required.");
      return;
    }

    if (editingDepartment) {
      updateMutation.mutate({ id: editingDepartment.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const departments = departmentsQuery.data ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Department Master"
        description="Manage the clinical and administrative departments available for OPD scheduling."
        actions={
          canManage ? (
            <Button size="sm" className="gap-1.5 text-xs" onClick={openCreateDialog}>
              <Plus className="w-3.5 h-3.5" />
              Add Department
            </Button>
          ) : (
            <Button
              size="sm"
              disabled
              title="You don't have permission to manage departments"
              className="gap-1.5 text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Department
            </Button>
          )
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <SearchInput
            placeholder="Search departments by name..."
            onSearchChange={setSearchQuery}
            isLoading={departmentsQuery.isFetching}
            className="max-w-sm"
          />

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {departments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-xs text-slate-400 py-8">
                      {departmentsQuery.isLoading ? "Loading departments..." : "No departments found."}
                    </TableCell>
                  </TableRow>
                ) : (
                  departments.map((department) => (
                    <TableRow key={department.id}>
                      <TableCell className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        {department.name}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-700">{department.code}</TableCell>
                      <TableCell className="text-xs text-slate-500 max-w-xs truncate">
                        {department.description || "—"}
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          disabled={!canManage || toggleActiveMutation.isPending}
                          onClick={() =>
                            toggleActiveMutation.mutate({
                              id: department.id,
                              isActive: !department.isActive,
                            })
                          }
                          title={canManage ? "Click to toggle status" : undefined}
                        >
                          <Badge
                            variant="outline"
                            className={
                              department.isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                : "bg-slate-100 text-slate-500 border-slate-300"
                            }
                          >
                            {department.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={!canManage}
                          onClick={() => openEditDialog(department)}
                          className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                          title={canManage ? "Edit department" : "You don't have permission to edit departments"}
                        >
                          <Pencil className="w-3.5 h-3.5" />
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

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingDepartment ? "Edit Department" : "Add Department"}</DialogTitle>
            <DialogDescription>
              {editingDepartment
                ? "Update this department's name and description."
                : "Create a new department for this facility."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Department Name
              </label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Cardiology"
                className="text-xs"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Department Code
              </label>
              <Input
                value={formData.code}
                onChange={(e) => setFormData((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. CARDIO"
                disabled={!!editingDepartment}
                className="text-xs font-mono uppercase"
              />
              {editingDepartment && (
                <p className="text-[10px] text-slate-400 mt-1">Department code cannot be changed.</p>
              )}
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                placeholder="Brief description of this department"
                rows={3}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {formError && (
              <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
                {formError}
              </p>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsDialogOpen(false)}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSaving}>
                {isSaving ? "Saving..." : editingDepartment ? "Save Changes" : "Create Department"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

export default function DepartmentsPage() {
  return (
    <AppShell>
      <DepartmentsPageContent />
    </AppShell>
  );
}
