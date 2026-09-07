"use client";

import React, { useState } from "react";
import {
  Bell,
  FlaskConical,
  BedDouble,
  Receipt,
  CheckCheck,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface NotificationItem {
  id: string;
  title: string;
  description: string;
  time: string;
  read: boolean;
  icon: React.ComponentType<{ className?: string }>;
  tone: "info" | "warning" | "success";
}

const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "n1",
    title: "Lab result pending approval",
    description: "CBC panel for FC01-202609-000102 is awaiting pathologist sign-off.",
    time: "5 min ago",
    read: false,
    icon: FlaskConical,
    tone: "warning",
  },
  {
    id: "n2",
    title: "Bed released — Ward B, Bed 12",
    description: "Housekeeping marked Ward B / Bed 12 as ready for allocation.",
    time: "22 min ago",
    read: false,
    icon: BedDouble,
    tone: "success",
  },
  {
    id: "n3",
    title: "Cashier shift closing reminder",
    description: "Shift #1 has been open for 8 hours. Reconcile collections before handover.",
    time: "1 hr ago",
    read: true,
    icon: Receipt,
    tone: "info",
  },
];

const TONE_STYLES: Record<NotificationItem["tone"], string> = {
  info: "text-blue-600 bg-blue-50",
  warning: "text-amber-600 bg-amber-50",
  success: "text-emerald-600 bg-emerald-50",
};

export function NotificationCenter() {
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);
  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="relative p-2 rounded-md hover:bg-slate-100 text-slate-500 transition-colors cursor-pointer"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500" />
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-slate-100">
          <span className="text-sm font-semibold text-slate-900">Notifications</span>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={markAllRead}
              className="flex items-center gap-1 text-[11px] font-medium text-primary hover:underline cursor-pointer"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all read
            </button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="py-8 px-4 text-center text-xs text-slate-400">
            You&apos;re all caught up.
          </div>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            {notifications.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.id}
                  className={cn(
                    "flex gap-2.5 px-3 py-2.5 border-b border-slate-50 last:border-0",
                    !item.read && "bg-teal-50/30"
                  )}
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-md flex items-center justify-center shrink-0",
                      TONE_STYLES[item.tone]
                    )}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-semibold text-slate-900 leading-tight">
                        {item.title}
                      </p>
                      {!item.read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1 shrink-0" />
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                      {item.description}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-1">{item.time}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="border-t border-slate-100 px-3 py-2">
          <button
            type="button"
            className="w-full text-center text-[11px] font-medium text-primary hover:underline cursor-pointer"
          >
            View all notifications
          </button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
