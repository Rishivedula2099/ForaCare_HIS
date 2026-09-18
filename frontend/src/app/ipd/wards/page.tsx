"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BedDouble, Plus, Pencil, DoorOpen } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
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
import { createWard, listWards, toWardCreatePayload, updateWard } from "@/lib/ipd-api";
import { Ward, WardFormData, WARD_TYPES } from "@/types/ipd";
import { ApiError } from "@/types/api";

const EMPTY_FORM: WardFormData = { departmentId: "", name: "", code: "", wardType: "GENERAL", floor: "" };

function WardsPageContent() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("ipd.manage_beds");

  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [editingWard, setEditingWard] = React.useState<Ward | null>(null);
  const [formData, setFormData] = React.useState<WardFormData>(EMPTY_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);

  const wardsQuery = useQuery({ queryKey: ["ipd-wards"], queryFn: listWards });

  const createMutation = useMutation({
    mutationFn: (data: WardFormData) => createWard(toWardCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Ward created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-wards"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to create ward."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: WardFormData }) =>
      updateWard(id, {
        name: data.name.trim(),
        ward_type: data.wardType,
        floor: data.floor.trim() || null,
      }),
    onSuccess: () => {
      toast({ title: "Ward updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-wards"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update ward."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updateWard(id, { is_active: isActive }),
    onSuccess: () => {
      toast({ title: "Ward status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-wards"] });
    },
    onError: () => toast({ title: "Unable to update ward status", variant: "destructive" }),
  });

  const openCreateDialog = () => {
    setEditingWard(null);
    setFormData(EMPTY_FORM);
    setFormError(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (ward: Ward) => {
    setEditingWard(ward);
    setFormData({
      departmentId: ward.departmentId ?? "",
      name: ward.name,
      code: ward.code,
      wardType: ward.wardType,
      floor: ward.floor ?? "",
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

    if (editingWard) {
      updateMutation.mutate({ id: editingWard.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const wards = wardsQuery.data ?? [];
  const wardTypeOptions = WARD_TYPES.map((t) => ({ value: t.value, label: t.label }));

  return (
    <PageContainer>
      <PageHeader
        title="Ward Master"
        description="Manage the inpatient wards available for bed assignment."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd">
                <BedDouble className="w-3.5 h-3.5" />
                Bed Board
              </Link>
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd/rooms">
                <DoorOpen className="w-3.5 h-3.5" />
                Rooms
              </Link>
            </Button>
            {canManage ? (
              <Button size="sm" className="gap-1.5 text-xs" onClick={openCreateDialog}>
                <Plus className="w-3.5 h-3.5" />
                Add Ward
              </Button>
            ) : (
              <Button
                size="sm"
                disabled
                title="You don't have permission to manage wards"
                className="gap-1.5 text-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Ward
              </Button>
            )}
          </div>
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ward</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Floor</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {wards.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-xs text-slate-400 py-8">
                      {wardsQuery.isLoading ? "Loading wards..." : "No wards found."}
                    </TableCell>
                  </TableRow>
                ) : (
                  wards.map((ward) => (
                    <TableRow key={ward.id}>
                      <TableCell className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                        <BedDouble className="w-3.5 h-3.5 text-slate-400" />
                        {ward.name}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-700">{ward.code}</TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {WARD_TYPES.find((t) => t.value === ward.wardType)?.label ?? ward.wardType}
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">{ward.floor || "—"}</TableCell>
                      <TableCell>
                        <button
                          type="button"
                          disabled={!canManage || toggleActiveMutation.isPending}
                          onClick={() => toggleActiveMutation.mutate({ id: ward.id, isActive: !ward.isActive })}
                          title={canManage ? "Click to toggle status" : undefined}
                        >
                          <Badge
                            variant="outline"
                            className={
                              ward.isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                : "bg-slate-100 text-slate-500 border-slate-300"
                            }
                          >
                            {ward.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={!canManage}
                          onClick={() => openEditDialog(ward)}
                          className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                          title={canManage ? "Edit ward" : "You don't have permission to edit wards"}
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
            <DialogTitle>{editingWard ? "Edit Ward" : "Add Ward"}</DialogTitle>
            <DialogDescription>
              {editingWard ? "Update this ward's details." : "Create a new inpatient ward for this facility."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Ward Name</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. General Ward A"
                className="text-xs"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Ward Code</label>
              <Input
                value={formData.code}
                onChange={(e) => setFormData((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. GW-A"
                disabled={!!editingWard}
                className="text-xs font-mono uppercase"
              />
              {editingWard && <p className="text-[10px] text-slate-400 mt-1">Ward code cannot be changed.</p>}
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Ward Type</label>
              <Select
                options={wardTypeOptions}
                value={formData.wardType}
                onChange={(value) => setFormData((f) => ({ ...f, wardType: value as WardFormData["wardType"] }))}
                placeholder="Select a ward type"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Floor (optional)</label>
              <Input
                value={formData.floor}
                onChange={(e) => setFormData((f) => ({ ...f, floor: e.target.value }))}
                placeholder="e.g. 2"
                className="text-xs"
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
                {isSaving ? "Saving..." : editingWard ? "Save Changes" : "Create Ward"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

export default function WardsPage() {
  return (
    <AppShell>
      <WardsPageContent />
    </AppShell>
  );
}
