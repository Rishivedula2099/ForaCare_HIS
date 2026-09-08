"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { RoleBadge } from "@/components/common/role-badge";
import { PageLoadingState } from "@/components/states/loading-state";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/lib/api-client";
import { ROLES, UserRole } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface RoleSummary {
  id: string;
  code: UserRole;
  name: string;
  description: string | null;
  is_system: boolean;
  permission_count: number;
}

interface Permission {
  id: string;
  code: string;
  module: string;
  description: string;
}

interface RoleDetail extends Omit<RoleSummary, "permission_count"> {
  permissions: Permission[];
}

function groupByModule(permissions: Permission[]): Record<string, Permission[]> {
  return permissions.reduce<Record<string, Permission[]>>((groups, permission) => {
    (groups[permission.module] ??= []).push(permission);
    return groups;
  }, {});
}

interface RolePermissionEditorProps {
  roleDetail: RoleDetail;
  allPermissions: Permission[];
  canManageRoles: boolean;
}

/** Keyed by role id from the parent, so switching roles remounts this with
 * fresh initial state instead of needing an effect to re-sync it. */
function RolePermissionEditor({ roleDetail, allPermissions, canManageRoles }: RolePermissionEditorProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedPermissionIds, setSelectedPermissionIds] = React.useState<Set<string>>(
    () => new Set(roleDetail.permissions.map((p) => p.id))
  );

  const savePermissions = useMutation({
    mutationFn: async () => {
      await apiClient.patch(`/rbac/roles/${roleDetail.id}/permissions`, {
        permission_ids: Array.from(selectedPermissionIds),
      });
    },
    onSuccess: () => {
      toast({ title: "Permissions updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["rbac-roles"] });
      queryClient.invalidateQueries({ queryKey: ["rbac-role", roleDetail.id] });
    },
    onError: () => {
      toast({ title: "Unable to update permissions", variant: "destructive" });
    },
  });

  const togglePermission = (permissionId: string) => {
    if (!canManageRoles) return;
    setSelectedPermissionIds((prev) => {
      const next = new Set(prev);
      if (next.has(permissionId)) next.delete(permissionId);
      else next.add(permissionId);
      return next;
    });
  };

  const grouped = groupByModule(allPermissions);

  return (
    <>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm">{roleDetail.name}</CardTitle>
        <Button
          size="sm"
          disabled={!canManageRoles || savePermissions.isPending}
          onClick={() => savePermissions.mutate()}
          title={canManageRoles ? undefined : "You do not have permission to manage roles & permissions."}
        >
          {savePermissions.isPending ? "Saving..." : "Save changes"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-5">
        {!canManageRoles && (
          <p className="text-xs text-slate-500 rounded-md bg-slate-50 border border-slate-200 px-3 py-2">
            You have read-only access to this screen. Contact a Super Admin or Hospital Admin to
            change role permissions.
          </p>
        )}
        {Object.entries(grouped).map(([module, permissions]) => (
          <div key={module} className="space-y-2">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              {module}
            </p>
            <div className="flex flex-wrap gap-2">
              {permissions.map((permission) => {
                const isChecked = selectedPermissionIds.has(permission.id);
                return (
                  <button
                    key={permission.id}
                    type="button"
                    disabled={!canManageRoles}
                    onClick={() => togglePermission(permission.id)}
                    title={permission.description}
                    className={cn(
                      "text-xs font-medium px-2.5 py-1 rounded-full border transition-colors",
                      isChecked
                        ? "bg-teal-50 border-teal-200 text-teal-800"
                        : "bg-white border-slate-200 text-slate-500",
                      canManageRoles ? "cursor-pointer hover:border-teal-300" : "cursor-not-allowed opacity-70"
                    )}
                  >
                    {permission.code}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </>
  );
}

function RolesPageContent() {
  const { hasPermission } = useAuth();
  const canManageRoles = hasPermission("roles.manage");

  const [selectedRoleId, setSelectedRoleId] = React.useState<string | null>(null);

  const rolesQuery = useQuery({
    queryKey: ["rbac-roles"],
    queryFn: async () => (await apiClient.get<RoleSummary[]>("/rbac/roles")).data ?? [],
  });

  const activeRoleId = selectedRoleId ?? rolesQuery.data?.[0]?.id ?? null;

  const roleDetailQuery = useQuery({
    queryKey: ["rbac-role", activeRoleId],
    queryFn: async () =>
      (await apiClient.get<RoleDetail>(`/rbac/roles/${activeRoleId}`)).data ?? null,
    enabled: !!activeRoleId,
  });

  const permissionsQuery = useQuery({
    queryKey: ["rbac-permissions"],
    queryFn: async () => (await apiClient.get<Permission[]>("/rbac/permissions")).data ?? [],
  });

  const isLoading = rolesQuery.isLoading || permissionsQuery.isLoading;

  if (isLoading) {
    return <PageLoadingState label="Loading roles..." />;
  }

  return (
    <PageContainer>
      <PageHeader
        title="Roles & Permissions"
        description="Manage what each role in the hospital can see and do. The backend enforces every permission independently of this screen."
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm">Roles</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Permissions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(rolesQuery.data ?? []).map((role) => (
                  <TableRow
                    key={role.id}
                    onClick={() => setSelectedRoleId(role.id)}
                    className={cn(
                      "cursor-pointer",
                      role.id === activeRoleId && "bg-teal-50/70"
                    )}
                  >
                    <TableCell>
                      <RoleBadge role={role.code} />
                    </TableCell>
                    <TableCell className="text-right text-xs text-slate-500">
                      {role.permission_count}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          {roleDetailQuery.data ? (
            <RolePermissionEditor
              key={roleDetailQuery.data.id}
              roleDetail={roleDetailQuery.data}
              allPermissions={permissionsQuery.data ?? []}
              canManageRoles={canManageRoles}
            />
          ) : (
            <CardHeader>
              <CardTitle className="text-sm">Select a role</CardTitle>
            </CardHeader>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}

export default function RolesPage() {
  return (
    <AppShell allowedRoles={[ROLES.SUPER_ADMIN, ROLES.HOSPITAL_ADMIN]}>
      <RolesPageContent />
    </AppShell>
  );
}
