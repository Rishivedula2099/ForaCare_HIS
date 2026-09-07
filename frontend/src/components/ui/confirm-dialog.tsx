"use client";

import * as React from "react";
import { AlertTriangle, AlertCircle, HelpCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "destructive" | "warning" | "default";
  isLoading?: boolean;
  onConfirm: () => void | Promise<void>;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "destructive",
  isLoading = false,
  onConfirm,
}: ConfirmDialogProps) {
  const Icon = {
    destructive: AlertCircle,
    warning: AlertTriangle,
    default: HelpCircle,
  }[variant];

  const iconBg = {
    destructive: "bg-rose-50 text-rose-600 border-rose-200",
    warning: "bg-amber-50 text-amber-600 border-amber-200",
    default: "bg-teal-50 text-primary border-teal-200",
  }[variant];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <div className="flex items-start gap-4">
          <div
            className={`w-10 h-10 rounded-full border flex items-center justify-center shrink-0 ${iconBg}`}
          >
            <Icon className="w-5 h-5" />
          </div>

          <div className="flex-1 space-y-1">
            <DialogHeader className="mb-1">
              <DialogTitle className="text-base">{title}</DialogTitle>
              <DialogDescription className="text-xs pt-1 leading-relaxed">
                {description}
              </DialogDescription>
            </DialogHeader>
          </div>
        </div>

        <DialogFooter className="mt-4 pt-3">
          <Button
            variant="outline"
            size="sm"
            disabled={isLoading}
            onClick={() => onOpenChange(false)}
          >
            {cancelLabel}
          </Button>

          <Button
            variant={variant === "destructive" ? "destructive" : "default"}
            size="sm"
            disabled={isLoading}
            onClick={onConfirm}
          >
            {isLoading ? "Processing..." : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
