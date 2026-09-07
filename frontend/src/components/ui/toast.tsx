"use client";

import * as React from "react";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useToast, ToastMessage } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const ICONS = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  destructive: AlertCircle,
};

export function Toaster() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={() => dismiss(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: () => void;
}) {
  const Icon = ICONS[toast.variant || "default"];

  const borderVariant = {
    default: "border-slate-200 bg-white text-slate-900",
    info: "border-teal-200 bg-teal-50 text-teal-950",
    success: "border-emerald-200 bg-emerald-50 text-emerald-950",
    destructive: "border-rose-200 bg-rose-50 text-rose-950",
  }[toast.variant || "default"];

  const iconColor = {
    default: "text-slate-500",
    info: "text-primary",
    success: "text-emerald-600",
    destructive: "text-rose-600",
  }[toast.variant || "default"];

  return (
    <div
      className={cn(
        "pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-lg transition-all animate-in slide-in-from-bottom-5 duration-200",
        borderVariant
      )}
    >
      <Icon className={cn("w-4 h-4 shrink-0 mt-0.5", iconColor)} />

      <div className="flex-1 text-xs">
        {toast.title && <div className="font-bold leading-tight mb-0.5">{toast.title}</div>}
        {toast.description && <div className="opacity-90 leading-relaxed">{toast.description}</div>}
      </div>

      <button
        type="button"
        onClick={onDismiss}
        className="p-1 rounded-sm opacity-60 hover:opacity-100 transition-opacity"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
