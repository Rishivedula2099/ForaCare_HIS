"use client";

import * as React from "react";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Requirement {
  label: string;
  test: (value: string) => boolean;
}

const REQUIREMENTS: Requirement[] = [
  { label: "At least 8 characters", test: (v) => v.length >= 8 },
  { label: "Upper & lower case letters", test: (v) => /[a-z]/.test(v) && /[A-Z]/.test(v) },
  { label: "At least one number", test: (v) => /\d/.test(v) },
  { label: "At least one special character", test: (v) => /[^A-Za-z0-9]/.test(v) },
];

const TIERS = [
  { label: "Weak", className: "bg-rose-500" },
  { label: "Fair", className: "bg-amber-500" },
  { label: "Good", className: "bg-teal-500" },
  { label: "Strong", className: "bg-emerald-500" },
];

export function getPasswordStrength(password: string): number {
  return REQUIREMENTS.filter((requirement) => requirement.test(password)).length;
}

interface PasswordStrengthMeterProps {
  password: string;
  className?: string;
}

export function PasswordStrengthMeter({ password, className }: PasswordStrengthMeterProps) {
  const score = getPasswordStrength(password);
  const tierIndex = password.length === 0 ? -1 : Math.max(0, score - 1);
  const tier = tierIndex >= 0 ? TIERS[tierIndex] : null;

  return (
    <div className={cn("space-y-2.5", className)}>
      <div className="flex gap-1">
        {TIERS.map((tierOption, index) => (
          <div
            key={tierOption.label}
            className={cn(
              "h-1.5 flex-1 rounded-full bg-slate-200 transition-colors",
              index <= tierIndex && tier ? tier.className : undefined
            )}
          />
        ))}
      </div>
      {tier && (
        <p className={cn("text-[11px] font-semibold", tierIndex === 3 ? "text-emerald-600" : "text-slate-500")}>
          Password strength: {tier.label}
        </p>
      )}
      <ul className="space-y-1">
        {REQUIREMENTS.map((requirement) => {
          const met = requirement.test(password);
          return (
            <li
              key={requirement.label}
              className={cn(
                "flex items-center gap-1.5 text-[11px]",
                met ? "text-emerald-600" : "text-slate-400"
              )}
            >
              {met ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              {requirement.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
