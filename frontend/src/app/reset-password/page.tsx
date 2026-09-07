"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { PasswordStrengthMeter, getPasswordStrength } from "@/components/auth/password-strength-meter";

/**
 * Mock-only reset flow (see forgot-password/page.tsx) - ready to be wired
 * to a real `/auth/reset-password` endpoint once OTP delivery infra exists.
 */
const resetSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .refine((value) => getPasswordStrength(value) >= 3, "Choose a stronger password."),
    confirm_password: z.string().min(1, "Please confirm your new password."),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type ResetFormValues = z.infer<typeof resetSchema>;

export default function ResetPasswordPage() {
  const [isDone, setIsDone] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const form = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  });
  const newPassword = form.watch("new_password");

  const onSubmit = async () => {
    setIsSubmitting(true);
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSubmitting(false);
    setIsDone(true);
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm space-y-6">
        <Logo variant="full" size="md" />

        {!isDone ? (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Set a new password</h2>
              <p className="text-sm text-slate-500 mt-1">Choose a strong password for your account.</p>
            </div>
            <Alert variant="info">
              <AlertDescription>Demo flow - no account is actually updated.</AlertDescription>
            </Alert>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="new_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>New Password</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <PasswordStrengthMeter password={newPassword || ""} className="pt-1" />
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="confirm_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Confirm New Password</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Updating..." : "Reset Password"}
                </Button>
              </form>
            </Form>
          </>
        ) : (
          <div className="flex flex-col items-center text-center gap-3 py-6">
            <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            </div>
            <p className="text-sm font-semibold text-slate-900">Password reset</p>
            <p className="text-xs text-slate-500 max-w-xs">
              Your password has been updated. You can now sign in with your new password.
            </p>
            <Button asChild size="sm" className="mt-2">
              <Link href="/login">Go to Sign In</Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
