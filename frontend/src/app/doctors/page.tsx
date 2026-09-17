"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Stethoscope, Plus, Pencil, Phone, Mail } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
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
import { createDoctor, listDoctors, toCreatePayload, updateDoctor } from "@/lib/doctor-api";
import { Doctor, DoctorFormData } from "@/types/doctor";
import { ApiError } from "@/types/api";

const EMPTY_FORM: DoctorFormData = {
  departmentId: "",
  fullName: "",
  specialization: "",
  qualification: "",
  phone: "",
  email: "",
  consultationFee: "",
};

function DoctorsPageContent() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("doctors.manage");

  const [searchQuery, setSearchQuery] = React.useState("");
  const [departmentFilter, setDepartmentFilter] = React.useState("ALL");
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [editingDoctor, setEditingDoctor] = React.useState<Doctor | null>(null);
  const [formData, setFormData] = React.useState<DoctorFormData>(EMPTY_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);

  const departmentsQuery = useQuery({
    queryKey: ["departments", ""],
    queryFn: () => listDepartments(),
  });

  const doctorsQuery = useQuery({
    queryKey: ["doctors", searchQuery, departmentFilter],
    queryFn: () =>
      listDoctors({
        name: searchQuery || undefined,
        department_id: departmentFilter !== "ALL" ? departmentFilter : undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: DoctorFormData) => createDoctor(toCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Doctor added", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to create doctor.");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: DoctorFormData }) =>
      updateDoctor(id, toCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Doctor updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => {
      setFormError(error?.message || "Unable to update doctor.");
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateDoctor(id, { is_active: isActive }),
    onSuccess: () => {
      toast({ title: "Doctor status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
    },
    onError: () => {
      toast({ title: "Unable to update doctor status", variant: "destructive" });
    },
  });

  const departmentOptions = [
    { value: "ALL", label: "All Departments" },
    ...(departmentsQuery.data ?? []).map((d) => ({ value: d.id, label: d.name })),
  ];

  const formDepartmentOptions = (departmentsQuery.data ?? []).map((d) => ({
    value: d.id,
    label: `${d.name} (${d.code})`,
  }));

  const openCreateDialog = () => {
    setEditingDoctor(null);
    setFormData(EMPTY_FORM);
    setFormError(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (doctor: Doctor) => {
    setEditingDoctor(doctor);
    setFormData({
      departmentId: doctor.departmentId,
      fullName: doctor.fullName,
      specialization: doctor.specialization,
      qualification: doctor.qualification || "",
      phone: doctor.phone || "",
      email: doctor.email || "",
      consultationFee: doctor.consultationFee !== undefined ? String(doctor.consultationFee) : "",
    });
    setFormError(null);
    setIsDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.departmentId || !formData.fullName.trim() || !formData.specialization.trim()) {
      setFormError("Department, name, and specialization are required.");
      return;
    }

    if (editingDoctor) {
      updateMutation.mutate({ id: editingDoctor.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const doctors = doctorsQuery.data ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Doctor Master"
        description="Manage doctors, their department assignment, and consultation details for OPD scheduling."
        actions={
          canManage ? (
            <Button size="sm" className="gap-1.5 text-xs" onClick={openCreateDialog}>
              <Plus className="w-3.5 h-3.5" />
              Add Doctor
            </Button>
          ) : (
            <Button
              size="sm"
              disabled
              title="You don't have permission to manage doctors"
              className="gap-1.5 text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Doctor
            </Button>
          )
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <SearchInput
              placeholder="Search by doctor name, code, or specialization..."
              onSearchChange={setSearchQuery}
              isLoading={doctorsQuery.isFetching}
              className="flex-1"
            />
            <div className="w-full sm:w-56">
              <Select
                options={departmentOptions}
                value={departmentFilter}
                onChange={setDepartmentFilter}
                placeholder="Filter by department"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Doctor</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Fee</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {doctors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-xs text-slate-400 py-8">
                      {doctorsQuery.isLoading ? "Loading doctors..." : "No doctors found."}
                    </TableCell>
                  </TableRow>
                ) : (
                  doctors.map((doctor) => (
                    <TableRow key={doctor.id}>
                      <TableCell>
                        <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
                          <Stethoscope className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          {doctor.fullName}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {doctor.specialization} • <span className="font-mono">{doctor.doctorCode}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        <Badge variant="outline" className="text-[10px] bg-teal-50 text-teal-800 border-teal-200">
                          {doctor.departmentName}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-slate-600 space-y-0.5">
                        {doctor.phone && (
                          <div className="flex items-center gap-1">
                            <Phone className="w-3 h-3 text-slate-400" />
                            {doctor.phone}
                          </div>
                        )}
                        {doctor.email && (
                          <div className="flex items-center gap-1 text-[11px] text-slate-500">
                            <Mail className="w-3 h-3 text-slate-400" />
                            {doctor.email}
                          </div>
                        )}
                        {!doctor.phone && !doctor.email && <span className="text-slate-400">—</span>}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-700">
                        {doctor.consultationFee !== undefined ? `₹${doctor.consultationFee}` : "—"}
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          disabled={!canManage || toggleActiveMutation.isPending}
                          onClick={() =>
                            toggleActiveMutation.mutate({
                              id: doctor.id,
                              isActive: !doctor.isActive,
                            })
                          }
                          title={canManage ? "Click to toggle status" : undefined}
                        >
                          <Badge
                            variant="outline"
                            className={
                              doctor.isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                : "bg-slate-100 text-slate-500 border-slate-300"
                            }
                          >
                            {doctor.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={!canManage}
                          onClick={() => openEditDialog(doctor)}
                          className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                          title={canManage ? "Edit doctor" : "You don't have permission to edit doctors"}
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
        <DialogContent size="lg">
          <DialogHeader>
            <DialogTitle>{editingDoctor ? "Edit Doctor" : "Add Doctor"}</DialogTitle>
            <DialogDescription>
              {editingDoctor
                ? "Update this doctor's department, specialization, and contact details."
                : "Register a new doctor against a department for this facility."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Department
                </label>
                <Select
                  options={formDepartmentOptions}
                  value={formData.departmentId}
                  onChange={(value) => setFormData((f) => ({ ...f, departmentId: value }))}
                  placeholder="Select department"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Specialization
                </label>
                <Input
                  value={formData.specialization}
                  onChange={(e) => setFormData((f) => ({ ...f, specialization: e.target.value }))}
                  placeholder="e.g. Interventional Cardiology"
                  className="text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Full Name
              </label>
              <Input
                value={formData.fullName}
                onChange={(e) => setFormData((f) => ({ ...f, fullName: e.target.value }))}
                placeholder="e.g. Dr. Priya Nair"
                className="text-xs"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Qualification
                </label>
                <Input
                  value={formData.qualification}
                  onChange={(e) => setFormData((f) => ({ ...f, qualification: e.target.value }))}
                  placeholder="e.g. MBBS, DM Cardiology"
                  className="text-xs"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Consultation Fee (₹)
                </label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.consultationFee}
                  onChange={(e) => setFormData((f) => ({ ...f, consultationFee: e.target.value }))}
                  placeholder="e.g. 500"
                  className="text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Phone
                </label>
                <Input
                  value={formData.phone}
                  onChange={(e) => setFormData((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="10-digit mobile number"
                  className="text-xs"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Email
                </label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                  placeholder="doctor@foracare-his.com"
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
                {isSaving ? "Saving..." : editingDoctor ? "Save Changes" : "Add Doctor"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

export default function DoctorsPage() {
  return (
    <AppShell>
      <DoctorsPageContent />
    </AppShell>
  );
}
