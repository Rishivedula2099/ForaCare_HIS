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
import { useRouteAccess } from "@/hooks/use-route-access";

const NAV_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  Printer,
};

// Only routes that exist; each is shown only if the user's permissions admit it.
const QUICK_ACTIONS = [
  { label: "Register New Patient", href: "/patients/new", icon: UserPlus, shortcut: "N P" },
  { label: "OPD Registration & Queue", href: "/opd", icon: Ticket, shortcut: "N T" },
  { label: "Admit Patient to IPD", href: "/ipd/allocate", icon: PlusCircle, shortcut: "N A" },
];

interface GlobalSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GlobalSearch({ open, onOpenChange }: GlobalSearchProps) {
  const router = useRouter();
  const canAccess = useRouteAccess();

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
          {QUICK_ACTIONS.filter((action) => canAccess(action.href)).map((action) => {
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

        <CommandGroup heading="Navigate">
          {MAIN_NAV_ITEMS.filter((item) => canAccess(item.href)).map((item) => {
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
