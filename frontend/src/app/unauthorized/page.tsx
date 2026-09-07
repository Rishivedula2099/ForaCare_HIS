"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { LockKeyhole } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/states/empty-state";

function UnauthorizedContent() {
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect");
  const requestId = searchParams.get("request_id");

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <EmptyState
        icon={LockKeyhole}
        title="Session required"
        description="Your session has expired or you haven't signed in yet. Please sign in to continue accessing ForaCare HIS."
        action={
          <div className="flex flex-col items-center gap-3">
            <Button asChild size="sm">
              <Link href={`/login${redirect ? `?redirect=${encodeURIComponent(redirect)}` : ""}`}>
                Sign In to ForaCare HIS
              </Link>
            </Button>
            <Button asChild size="sm" variant="ghost">
              <Link href="/">Return to Home</Link>
            </Button>
            {requestId && (
              <p className="text-[10px] font-mono text-slate-400 pt-2">Reference: {requestId}</p>
            )}
          </div>
        }
      />
    </div>
  );
}

export default function UnauthorizedPage() {
  return (
    <Suspense fallback={null}>
      <UnauthorizedContent />
    </Suspense>
  );
}
