"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { PasswordStrengthMeter, getPasswordStrength } from "@/components/auth/password-strength-meter";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";

const schema = z
  .object({
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .max(72, "Password must be at most 72 characters.")
      .refine((value) => getPasswordStrength(value) >= 3, "Choose a stronger password."),
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

interface SetPasswordFormProps {
  title: string;
  description: string;
  /** Backend endpoint that consumes the emailed single-use token. */
  endpoint: "/auth/password-reset/confirm" | "/auth/activate";
  /** Shown on /login after success. */
  successReason: "reset" | "activated";
  /** Where to send someone whose link is missing, used or expired. */
  newLinkHref: string;
  newLinkLabel: string;
}

/** Shared by password reset and first-time account activation. */
export function SetPasswordForm({
  title,
  description,
  endpoint,
  successReason,
  newLinkHref,
  newLinkLabel,
}: SetPasswordFormProps) {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [linkInvalid, setLinkInvalid] = React.useState(!token);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: "", confirm_password: "" },
  });
  const newPassword = form.watch("new_password");

  // The token only needs to live in the URL until it is submitted.
  React.useEffect(() => {
    if (token) window.history.replaceState(null, "", window.location.pathname);
  }, [token]);

  const onSubmit = async (values: FormValues) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await apiClient.post(endpoint, { token, new_password: values.new_password });
      router.replace(`/login?reason=${successReason}`);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.code === "INVALID_TOKEN" || apiError?.status_code === 401) {
        setLinkInvalid(true);
      } else {
        setError(apiError?.message || "Unable to set your password. Please try again.");
      }
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm space-y-6">
        <Link href="/" aria-label="ForaCare HIS home">
          <Logo variant="full" size="md" />
        </Link>

        {linkInvalid ? (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">This link can&apos;t be used</h2>
              <p className="text-sm text-slate-500 mt-1">
                It is missing, has already been used, or has expired.
              </p>
            </div>
            <Button asChild className="w-full">
              <Link href={newLinkHref}>{newLinkLabel}</Link>
            </Button>
          </>
        ) : (
          <>
            <div>
              <h2 className="text-xl font-bold text-slate-900">{title}</h2>
              <p className="text-sm text-slate-500 mt-1">{description}</p>
            </div>
            {error && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
                <FormField
                  control={form.control}
                  name="new_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel htmlFor="new-password">New password</FormLabel>
                      <FormControl>
                        <Input id="new-password" type="password" autoComplete="new-password" autoFocus {...field} />
                      </FormControl>
                      <PasswordStrengthMeter password={newPassword} />
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="confirm_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel htmlFor="confirm-password">Confirm password</FormLabel>
                      <FormControl>
                        <Input id="confirm-password" type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {isSubmitting ? "Saving..." : "Set password"}
                </Button>
              </form>
            </Form>
          </>
        )}
      </div>
    </div>
  );
}
