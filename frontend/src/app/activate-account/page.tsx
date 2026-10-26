"use client";

import { Suspense } from "react";
import { SetPasswordForm } from "@/components/auth/set-password-form";

export default function ActivateAccountPage() {
  return (
    <Suspense fallback={null}>
      <SetPasswordForm
        title="Activate your account"
        description="Welcome to ForaCare HIS. Choose a password to finish setting up your account."
        endpoint="/auth/activate"
        successReason="activated"
        newLinkHref="/forgot-password"
        newLinkLabel="Request a new link"
      />
    </Suspense>
  );
}
