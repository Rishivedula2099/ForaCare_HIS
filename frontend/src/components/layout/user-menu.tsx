"use client";

import React from "react";
import { KeyRound, LogOut, Settings, ShieldCheck, UserCircle } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChangePasswordDialog } from "@/components/auth/change-password-dialog";
import { useAuth } from "@/hooks/use-auth";
import { ROLE_METADATA_MAP } from "@/types/auth";
import { cn } from "@/lib/utils";

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function UserMenu() {
  const { user, logout } = useAuth();
  const [isChangePasswordOpen, setIsChangePasswordOpen] = React.useState(false);

  if (!user) return null;

  const roleMeta = ROLE_METADATA_MAP[user.role];

  return (
    <>
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
              <span className="text-[10px] text-teal-700 font-medium">{roleMeta.label}</span>
            </div>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuLabel className="normal-case tracking-normal text-xs font-semibold text-slate-700">
            {user.email}
            <span
              className={cn(
                "block w-fit mt-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full border",
                roleMeta.badgeClassName
              )}
            >
              {roleMeta.label}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <UserCircle className="w-4 h-4 text-slate-500" />
            My Profile
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setIsChangePasswordOpen(true)}>
            <KeyRound className="w-4 h-4 text-slate-500" />
            Change Password
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
            onClick={() => logout()}
            className="text-rose-600 focus:bg-rose-50 focus:text-rose-700"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ChangePasswordDialog open={isChangePasswordOpen} onOpenChange={setIsChangePasswordOpen} />
    </>
  );
}
