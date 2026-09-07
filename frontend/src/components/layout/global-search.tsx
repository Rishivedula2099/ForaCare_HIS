"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
  UserPlus,
  Ticket,
  PlusCircle,
  User,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import { MAIN_NAV_ITEMS } from "@/lib/constants";

const NAV_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
};

const QUICK_ACTIONS = [
  { label: "Register New Patient", href: "/patients/new", icon: UserPlus, shortcut: "N P" },
  { label: "Generate New OPD Token", href: "/opd/token/new", icon: Ticket, shortcut: "N T" },
  { label: "Admit Patient to IPD", href: "/ipd/admit", icon: PlusCircle, shortcut: "N A" },
];

// Placeholder result set until the patient search API (P2) is wired in.
const RECENT_PATIENTS = [
  { name: "Sunita Verma", uid: "FC01-202609-000102", href: "/patients/FC01-202609-000102" },
  { name: "Rajesh Kumar", uid: "FC01-202609-000105", href: "/patients/FC01-202609-000105" },
  { name: "Ananya Sharma", uid: "FC01-202609-000098", href: "/patients/FC01-202609-000098" },
];

interface GlobalSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GlobalSearch({ open, onOpenChange }: GlobalSearchProps) {
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  const runCommand = (callback: () => void) => {
    onOpenChange(false);
    callback();
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search patients, modules, or actions..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Quick Actions">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <CommandItem
                key={action.href}
                value={action.label}
                onSelect={() => runCommand(() => router.push(action.href))}
              >
                <Icon />
                {action.label}
                <CommandShortcut>{action.shortcut}</CommandShortcut>
              </CommandItem>
            );
          })}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Recent Patients">
          {RECENT_PATIENTS.map((patient) => (
            <CommandItem
              key={patient.uid}
              value={`${patient.name} ${patient.uid}`}
              onSelect={() => runCommand(() => router.push(patient.href))}
            >
              <User />
              <span>{patient.name}</span>
              <CommandShortcut className="font-mono">{patient.uid}</CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Navigate">
          {MAIN_NAV_ITEMS.map((item) => {
            const Icon = NAV_ICON_MAP[item.iconName] || LayoutDashboard;
            return (
              <CommandItem
                key={item.href}
                value={item.title}
                onSelect={() => runCommand(() => router.push(item.href))}
              >
                <Icon />
                {item.title}
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
