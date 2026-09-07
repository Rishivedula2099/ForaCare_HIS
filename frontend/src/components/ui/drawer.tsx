"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  position?: "right" | "left";
  size?: "sm" | "md" | "lg" | "xl";
}

export function Drawer({
  open,
  onOpenChange,
  children,
  position = "right",
  size = "md",
}: DrawerProps) {
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  const widthClasses = {
    sm: "max-w-xs",
    md: "max-w-md",
    lg: "max-w-xl",
    xl: "max-w-2xl",
  }[size];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in"
        onClick={() => onOpenChange(false)}
      />

      <div className={cn("fixed inset-y-0 flex max-w-full", position === "right" ? "right-0" : "left-0")}>
        <div
          className={cn(
            "w-screen bg-white shadow-2xl flex flex-col border-slate-200 animate-in slide-in-from-right duration-200",
            position === "right" ? "border-l" : "border-r",
            widthClasses
          )}
          role="dialog"
          aria-modal="true"
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export function DrawerHeader({
  className,
  onClose,
  title,
  description,
}: {
  className?: string;
  onClose?: () => void;
  title: string;
  description?: string;
}) {
  return (
    <div className={cn("p-5 border-b border-slate-100 flex items-start justify-between bg-slate-50/50", className)}>
      <div className="space-y-1">
        <h3 className="font-bold text-base text-slate-900 leading-tight">{title}</h3>
        {description && <p className="text-xs text-slate-500">{description}</p>}
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export function DrawerBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex-1 overflow-y-auto p-5 space-y-4", className)}>
      {children}
    </div>
  );
}

export function DrawerFooter({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("p-4 border-t border-slate-100 bg-slate-50/70 flex items-center justify-end gap-2", className)}>
      {children}
    </div>
  );
}
