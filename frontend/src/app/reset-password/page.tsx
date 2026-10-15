"use client";

import { Suspense } from "react";
import { SetPasswordForm } from "@/components/auth/set-password-form";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <SetPasswordForm
        title="Set a new password"
        description="Choose a strong password. You will be signed out everywhere and asked to sign in again."
        endpoint="/auth/password-reset/confirm"
        successReason="reset"
        newLinkHref="/forgot-password"
        newLinkLabel="Request a new reset link"
      />
    </Suspense>
  );
}
