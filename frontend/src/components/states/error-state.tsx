import React from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  /** Correlation ID surfaced by the API client, useful for support/audit lookups. */
  correlationId?: string;
  className?: string;
}

/** Reusable inline/section error pattern for failed queries and mutations. */
export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  onRetry,
  correlationId,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center gap-3 py-14 px-6",
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center">
        <AlertTriangle className="w-5 h-5 text-rose-500" />
      </div>
      <div className="space-y-1 max-w-sm">
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        <p className="text-xs text-slate-500">{description}</p>
        {correlationId && (
          <p className="text-[10px] font-mono text-slate-400 pt-1">
            Reference: {correlationId}
          </p>
        )}
      </div>
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry} className="gap-1.5 bg-white">
          <RefreshCcw className="w-3.5 h-3.5" />
          Try Again
        </Button>
      )}
    </div>
  );
}

/** Specialized error state for network/API connectivity failures. */
export function NetworkErrorState({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorState
      title="Unable to reach the HIS server"
      description="Check your network connection or verify the API service is running."
      onRetry={onRetry}
    />
  );
}
