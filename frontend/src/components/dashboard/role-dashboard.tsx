import type { ComponentType } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ROLES, UserRole } from "@/lib/constants";
import { ROLE_METADATA_MAP } from "@/types/auth";
import {
  Building2,
  ClipboardList,
  FlaskConical,
  ShieldCheck,
  Stethoscope,
  Ticket,
  Users,
} from "lucide-react";

interface RoleDashboardProps {
  role: UserRole;
}

// Per-role dashboard resolution (S1-F02): each supported role gets a
// purpose-built view; anything without a bespoke layout yet falls back to
// a generic summary built from its permission catalog so every role still
// has a usable home screen.
export function RoleDashboard({ role }: RoleDashboardProps) {
  switch (role) {
    case ROLES.SUPER_ADMIN:
      return <SuperAdminDashboard />;
    case ROLES.HOSPITAL_ADMIN:
      return <HospitalAdminDashboard />;
    case ROLES.DOCTOR:
      return <DoctorDashboard />;
    case ROLES.RECEPTIONIST:
      return <ReceptionDashboard />;
    default:
      return <GenericRoleDashboard role={role} />;
  }
}

function StatCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-500">{label}</p>
          <div className="text-xl font-bold text-slate-900 tracking-tight">{value}</div>
          <p className="text-[11px] text-slate-500">{detail}</p>
        </div>
        <div className="w-10 h-10 rounded-lg flex items-center justify-center text-primary bg-primary/10">
          <Icon className="w-5 h-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function SuperAdminDashboard() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard icon={Building2} label="Tenants" value="2" detail="Active hospital networks" />
      <StatCard icon={Users} label="Facilities" value="4" detail="Across all tenants" />
      <StatCard icon={ShieldCheck} label="Roles Configured" value="9" detail="System + custom roles" />
      <StatCard icon={ClipboardList} label="Audit Events (24h)" value="—" detail="See Audit Logs" />
    </div>
  );
}

function HospitalAdminDashboard() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard icon={Users} label="Staff Accounts" value="9" detail="Across this tenant's facilities" />
      <StatCard icon={Building2} label="Facilities" value="3" detail="Active under this tenant" />
      <StatCard icon={ShieldCheck} label="Role Assignments" value="9" detail="Manage in Roles & Permissions" />
    </div>
  );
}

function DoctorDashboard() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard icon={Stethoscope} label="Patients in Queue" value="4" detail="Waiting for consultation" />
      <StatCard icon={ClipboardList} label="Admitted Under Your Care" value="—" detail="IPD module pending" />
      <StatCard icon={FlaskConical} label="Pending Lab Results" value="—" detail="Lab module pending" />
    </div>
  );
}

function ReceptionDashboard() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <StatCard icon={Ticket} label="OPD Tokens Issued Today" value="—" detail="OPD module pending" />
      <StatCard icon={Users} label="New Registrations Today" value="—" detail="See Patients" />
      <StatCard icon={ClipboardList} label="Pending Appointments" value="—" detail="Scheduling module pending" />
    </div>
  );
}

function GenericRoleDashboard({ role }: { role: UserRole }) {
  const metadata = ROLE_METADATA_MAP[role];

  return (
    <Card className="shadow-xs border-slate-200">
      <CardHeader>
        <CardTitle className="text-base">Your Access Summary</CardTitle>
        <CardDescription className="text-xs">
          A dedicated {metadata.label} workspace for this module is not built yet - here is what
          your role can currently do.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {metadata.keyPermissions.map((permission) => (
            <Badge key={permission} variant="secondary">
              {permission}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
