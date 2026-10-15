"use client";

import Link from "next/link";
import { Button, type ButtonProps } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

/**
 * "Sign in" for visitors, "Open dashboard" for someone already signed in.
 * Renders nothing while the session is being checked, so it never flashes
 * the wrong action.
 */
export function AuthCta({ size, variant }: Pick<ButtonProps, "size" | "variant">) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  return (
    <Button asChild size={size} variant={variant}>
      {isAuthenticated ? <Link href="/dashboard">Open dashboard</Link> : <Link href="/login">Sign in</Link>}
    </Button>
  );
}
