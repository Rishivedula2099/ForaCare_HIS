"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { LogOut, Settings, ShieldCheck, UserCircle } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DisplayUser {
  full_name: string;
  /** Display label, e.g. role + specialty — not restricted to the UserRole enum. */
  role: string;
  email?: string;
}

interface UserMenuProps {
  user?: DisplayUser;
}

const DEFAULT_USER: DisplayUser = {
  full_name: "Dr. Priya Raman",
  role: "OPD Physician - Cardiologist",
  email: "priya.raman@foracare.local",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function UserMenu({ user = DEFAULT_USER }: UserMenuProps) {
  const router = useRouter();

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("foracare_access_token");
      localStorage.removeItem("foracare_tenant_id");
      localStorage.removeItem("foracare_facility_id");
    }
    router.push("/login");
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-2.5 pl-1 pr-1.5 py-1 rounded-md hover:bg-slate-100 transition-colors cursor-pointer"
        >
          <Avatar className="h-8 w-8 border border-slate-200">
            <AvatarFallback>{getInitials(user.full_name)}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-900 leading-tight">
              {user.full_name}
            </span>
            <span className="text-[10px] text-teal-700 font-medium">
              {user.role}
            </span>
          </div>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="normal-case tracking-normal text-xs font-semibold text-slate-700">
          {user.email || user.full_name}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <UserCircle className="w-4 h-4 text-slate-500" />
          My Profile
        </DropdownMenuItem>
        <DropdownMenuItem>
          <Settings className="w-4 h-4 text-slate-500" />
          Preferences
        </DropdownMenuItem>
        <DropdownMenuItem>
          <ShieldCheck className="w-4 h-4 text-slate-500" />
          Roles & Permissions
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleLogout}
          className="text-rose-600 focus:bg-rose-50 focus:text-rose-700"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
