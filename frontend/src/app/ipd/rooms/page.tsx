"use client";

import React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BedDouble, Plus, Pencil, DoorOpen, Building2 } from "lucide-react";

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
import { createRoom, listRooms, listWards, toRoomCreatePayload, updateRoom } from "@/lib/ipd-api";
import { Room, RoomFormData, ROOM_TYPES } from "@/types/ipd";
import { ApiError } from "@/types/api";

const EMPTY_FORM: RoomFormData = { wardId: "", roomNumber: "", roomType: "GENERAL" };

function RoomsPageContent() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("ipd.manage_beds");

  const [wardFilter, setWardFilter] = React.useState("ALL");
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [editingRoom, setEditingRoom] = React.useState<Room | null>(null);
  const [formData, setFormData] = React.useState<RoomFormData>(EMPTY_FORM);
  const [formError, setFormError] = React.useState<string | null>(null);

  const wardsQuery = useQuery({ queryKey: ["ipd-wards"], queryFn: listWards });
  const activeWards = (wardsQuery.data ?? []).filter((w) => w.isActive);

  const roomsQuery = useQuery({
    queryKey: ["ipd-rooms", wardFilter],
    queryFn: () => listRooms({ ward_id: wardFilter !== "ALL" ? wardFilter : undefined }),
  });

  const createMutation = useMutation({
    mutationFn: (data: RoomFormData) => createRoom(toRoomCreatePayload(data)),
    onSuccess: () => {
      toast({ title: "Room created", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-rooms"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to create room."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: RoomFormData }) =>
      updateRoom(id, { room_number: data.roomNumber.trim(), room_type: data.roomType }),
    onSuccess: () => {
      toast({ title: "Room updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-rooms"] });
      setIsDialogOpen(false);
    },
    onError: (error: ApiError) => setFormError(error?.message || "Unable to update room."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updateRoom(id, { is_active: isActive }),
    onSuccess: () => {
      toast({ title: "Room status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["ipd-rooms"] });
    },
    onError: () => toast({ title: "Unable to update room status", variant: "destructive" }),
  });

  const openCreateDialog = () => {
    setEditingRoom(null);
    setFormData({ ...EMPTY_FORM, wardId: wardFilter !== "ALL" ? wardFilter : activeWards[0]?.id ?? "" });
    setFormError(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (room: Room) => {
    setEditingRoom(room);
    setFormData({ wardId: room.wardId, roomNumber: room.roomNumber, roomType: room.roomType });
    setFormError(null);
    setIsDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.wardId) {
      setFormError("Please select a ward.");
      return;
    }
    if (!formData.roomNumber.trim()) {
      setFormError("Room number is required.");
      return;
    }

    if (editingRoom) {
      updateMutation.mutate({ id: editingRoom.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const rooms = roomsQuery.data ?? [];
  const wardOptions = [
    { value: "ALL", label: "All Wards" },
    ...activeWards.map((w) => ({ value: w.id, label: `${w.name} (${w.code})` })),
  ];
  const formWardOptions = activeWards.map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));
  const roomTypeOptions = ROOM_TYPES.map((t) => ({ value: t.value, label: t.label }));

  return (
    <PageContainer>
      <PageHeader
        title="Room Master"
        description="Manage the rooms within each ward."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd">
                <BedDouble className="w-3.5 h-3.5" />
                Bed Board
              </Link>
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
              <Link href="/ipd/wards">
                <Building2 className="w-3.5 h-3.5" />
                Wards
              </Link>
            </Button>
            {canManage ? (
              <Button size="sm" className="gap-1.5 text-xs" onClick={openCreateDialog}>
                <Plus className="w-3.5 h-3.5" />
                Add Room
              </Button>
            ) : (
              <Button
                size="sm"
                disabled
                title="You don't have permission to manage rooms"
                className="gap-1.5 text-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Room
              </Button>
            )}
          </div>
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4 space-y-4">
          <div className="w-full sm:w-64">
            <Select options={wardOptions} value={wardFilter} onChange={setWardFilter} placeholder="Filter by ward" />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Room</TableHead>
                  <TableHead>Ward</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rooms.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-xs text-slate-400 py-8">
                      {roomsQuery.isLoading ? "Loading rooms..." : "No rooms found."}
                    </TableCell>
                  </TableRow>
                ) : (
                  rooms.map((room) => (
                    <TableRow key={room.id}>
                      <TableCell className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                        <DoorOpen className="w-3.5 h-3.5 text-slate-400" />
                        {room.roomNumber}
                      </TableCell>
                      <TableCell className="text-xs text-slate-700">
                        {room.ward.name} ({room.ward.code})
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {ROOM_TYPES.find((t) => t.value === room.roomType)?.label ?? room.roomType}
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          disabled={!canManage || toggleActiveMutation.isPending}
                          onClick={() => toggleActiveMutation.mutate({ id: room.id, isActive: !room.isActive })}
                          title={canManage ? "Click to toggle status" : undefined}
                        >
                          <Badge
                            variant="outline"
                            className={
                              room.isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                : "bg-slate-100 text-slate-500 border-slate-300"
                            }
                          >
                            {room.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={!canManage}
                          onClick={() => openEditDialog(room)}
                          className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                          title={canManage ? "Edit room" : "You don't have permission to edit rooms"}
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
            <DialogTitle>{editingRoom ? "Edit Room" : "Add Room"}</DialogTitle>
            <DialogDescription>
              {editingRoom ? "Update this room's details." : "Create a new room within a ward."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Ward</label>
              <Select
                options={formWardOptions}
                value={formData.wardId}
                onChange={(value) => setFormData((f) => ({ ...f, wardId: value }))}
                placeholder="Select a ward"
                disabled={!!editingRoom}
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Room Number</label>
              <Input
                value={formData.roomNumber}
                onChange={(e) => setFormData((f) => ({ ...f, roomNumber: e.target.value }))}
                placeholder="e.g. 101"
                className="text-xs"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">Room Type</label>
              <Select
                options={roomTypeOptions}
                value={formData.roomType}
                onChange={(value) => setFormData((f) => ({ ...f, roomType: value as RoomFormData["roomType"] }))}
                placeholder="Select a room type"
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
                {isSaving ? "Saving..." : editingRoom ? "Save Changes" : "Create Room"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

export default function RoomsPage() {
  return (
    <AppShell>
      <RoomsPageContent />
    </AppShell>
  );
}
