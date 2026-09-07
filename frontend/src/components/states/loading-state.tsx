import React from "react";
import { Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SpinnerProps {
  label?: string;
  className?: string;
}

/** Small inline spinner for buttons, cards, or panels awaiting data. */
export function Spinner({ label, className }: SpinnerProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 py-10 text-slate-500", className)}>
      <Loader2 className="w-5 h-5 animate-spin text-primary" />
      {label && <p className="text-xs font-medium">{label}</p>}
    </div>
  );
}

/** Full-page loading state, used by app/loading.tsx and route segments. */
export function PageLoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center">
      <Spinner label={label} />
    </div>
  );
}

/** Skeleton rows for a table awaiting data (e.g. OPD queue, patient list). */
export function TableLoadingState({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="w-full">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="flex items-center gap-4 px-4 py-3 border-b border-slate-100 last:border-0"
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-3.5 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Skeleton grid for stat/summary cards awaiting telemetry data. */
export function CardLoadingState({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-2.5 w-24" />
        </div>
      ))}
    </div>
  );
}
