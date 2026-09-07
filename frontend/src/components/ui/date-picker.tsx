"use client";

import * as React from "react";
import { Calendar as CalendarIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DatePickerProps {
  value?: string; // YYYY-MM-DD
  onChange?: (date: string) => void;
  placeholder?: string;
  minDate?: string;
  maxDate?: string;
  disabled?: boolean;
  className?: string;
  error?: string;
  id?: string;
  showPresets?: boolean;
}

export function DatePicker({
  value = "",
  onChange,
  placeholder = "Select date...",
  minDate,
  maxDate,
  disabled = false,
  className,
  error,
  id,
  showPresets = false,
}: DatePickerProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handlePreset = (preset: "today" | "yesterday" | "last7") => {
    const d = new Date();
    if (preset === "yesterday") {
      d.setDate(d.getDate() - 1);
    } else if (preset === "last7") {
      d.setDate(d.getDate() - 7);
    }
    const formatted = d.toISOString().split("T")[0];
    onChange?.(formatted);
  };

  return (
    <div className={cn("flex flex-col gap-1 w-full", className)}>
      <div className="relative flex items-center">
        <input
          ref={inputRef}
          type="date"
          id={id}
          value={value}
          min={minDate}
          max={maxDate}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-background pl-9 pr-8 py-1 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-destructive focus-visible:ring-destructive"
          )}
        />
        <CalendarIcon className="w-4 h-4 text-slate-400 absolute left-2.5 pointer-events-none" />

        {value && !disabled && (
          <button
            type="button"
            onClick={() => onChange?.("")}
            className="absolute right-2.5 p-0.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {showPresets && !disabled && (
        <div className="flex items-center gap-1.5 mt-0.5">
          <button
            type="button"
            onClick={() => handlePreset("today")}
            className="text-[11px] text-primary hover:underline font-medium"
          >
            Today
          </button>
          <span className="text-slate-300">•</span>
          <button
            type="button"
            onClick={() => handlePreset("yesterday")}
            className="text-[11px] text-slate-500 hover:text-slate-800"
          >
            Yesterday
          </button>
          <span className="text-slate-300">•</span>
          <button
            type="button"
            onClick={() => handlePreset("last7")}
            className="text-[11px] text-slate-500 hover:text-slate-800"
          >
            7 Days Ago
          </button>
        </div>
      )}

      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  );
}
