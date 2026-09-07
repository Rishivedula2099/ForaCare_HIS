"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/states/error-state";

export default function GlobalErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center">
      <ErrorState
        title="Something went wrong"
        description="An unexpected error occurred while rendering this page. If this keeps happening, contact your system administrator."
        correlationId={error.digest}
        onRetry={reset}
      />
    </div>
  );
}
