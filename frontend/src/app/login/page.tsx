"use client";

import * as React from "react";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Eye, EyeOff, Loader2, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { IS_DEV_BUILD } from "@/lib/constants";
import { resolvePostLoginPath } from "@/lib/route-access";
import { AuthError, AuthUser } from "@/types/auth";

const loginSchema = z.object({
  username: z.string().min(1, "Username or email is required."),
  password: z.string().min(1, "Password is required."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

type AlertVariant = "info" | "success" | "warning" | "destructive";

/** Notices carried in from elsewhere via `?reason=`. */
const REASON_NOTICES: Record<string, { variant: AlertVariant; text: string }> = {
  expired: { variant: "warning", text: "Your session has expired. Please sign in again." },
  idle: { variant: "info", text: "You were signed out after a period of inactivity." },
  reset: { variant: "success", text: "Your password has been updated. Sign in with your new password." },
  activated: { variant: "success", text: "Your account is active. Sign in with the password you just chose." },
};

/** How each sign-in failure is presented. */
function describeFailure(error: unknown): { variant: AlertVariant; title: string; text: string } {
  const failure = error instanceof AuthError ? error : null;
  switch (failure?.code) {
    case "INVALID_CREDENTIALS":
      return { variant: "destructive", title: "Sign-in failed", text: "Invalid username or password." };
    case "ACCOUNT_DISABLED":
      return {
        variant: "warning",
        title: "Account disabled",
        text: "This account has been disabled. Contact your hospital administrator.",
      };
    case "NO_FACILITY_ACCESS":
    case "FACILITY_NOT_ASSIGNED":
      return {
        variant: "warning",
        title: "No facility access",
        text: "Your account is not assigned to an active facility. Contact your hospital administrator.",
      };
    case "TOO_MANY_REQUESTS":
      return { variant: "warning", title: "Too many attempts", text: failure.message };
    case "NETWORK_ERROR":
      return { variant: "destructive", title: "Cannot reach the server", text: failure.message };
    default:
      return {
        variant: "destructive",
        title: "Sign-in failed",
        text: failure?.message || "Unable to sign in. Please try again.",
      };
  }
}

function LoginForm() {
  const { login, isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedPath = searchParams.get("redirect");
  const notice = REASON_NOTICES[searchParams.get("reason") ?? ""];

  const [showPassword, setShowPassword] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [failure, setFailure] = React.useState<ReturnType<typeof describeFailure> | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const destinationFor = React.useCallback(
    (signedIn: AuthUser) =>
      resolvePostLoginPath(requestedPath, (code) => signedIn.permissions.includes(code), {
        devToolsEnabled: IS_DEV_BUILD,
      }),
    [requestedPath]
  );

  // Visiting /login while already signed in just continues to the workspace.
  React.useEffect(() => {
    if (!isLoading && isAuthenticated && user && !isSubmitting) {
      router.replace(destinationFor(user));
    }
  }, [isLoading, isAuthenticated, user, isSubmitting, router, destinationFor]);

  const onSubmit = async (values: LoginFormValues) => {
    setIsSubmitting(true);
    setFailure(null);
    try {
      const signedIn = await login({ username: values.username.trim(), password: values.password });
      router.replace(destinationFor(signedIn));
    } catch (error) {
      setFailure(describeFailure(error));
      form.setValue("password", "");
      setIsSubmitting(false);
    }
  };

  const checkingSession = isLoading;

  return (
    <div className="flex min-h-screen w-full bg-slate-50">
      {/* Left brand showcase */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-[#04222b] text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] bg-size-[24px_24px]" />
        <div className="relative z-10">
          <Link href="/" aria-label="ForaCare HIS home">
            <Logo variant="icon" size="lg" className="mb-10" />
          </Link>
          <h1 className="text-3xl font-bold tracking-tight leading-tight max-w-md">
            One Patient. One Record. Better Care.
          </h1>
          <p className="mt-4 text-sm text-slate-300 max-w-sm">
            A unified hospital information system for registration, OPD, IPD, billing, and diagnostics -
            built for multi-facility clinical operations.
          </p>
        </div>
        <div className="relative z-10 space-y-3 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            Authorised staff only. Activity is audited.
          </div>
          <p className="text-slate-500">&copy; {new Date().getFullYear()} ForaSoftware. All rights reserved.</p>
        </div>
      </div>

      {/* Right access portal */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden">
            <Link href="/" aria-label="ForaCare HIS home">
              <Logo variant="full" size="md" />
            </Link>
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Sign in to your workspace</h2>
            <p className="text-sm text-slate-500 mt-1">Enter your staff credentials to continue.</p>
          </div>

          {notice && !failure && (
            <Alert variant={notice.variant}>
              <AlertDescription>{notice.text}</AlertDescription>
            </Alert>
          )}

          {failure && (
            <Alert variant={failure.variant} role="alert">
              <AlertDescription>
                <strong className="block">{failure.title}</strong>
                {failure.text}
              </AlertDescription>
            </Alert>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="login-username">Username or Email</FormLabel>
                    <FormControl>
                      <Input id="login-username" autoComplete="username" autoFocus disabled={checkingSession} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-center justify-between">
                      <FormLabel htmlFor="login-password">Password</FormLabel>
                      <Link href="/forgot-password" className="text-[11px] font-medium text-primary hover:underline">
                        Forgot password?
                      </Link>
                    </div>
                    <div className="relative">
                      <FormControl>
                        <Input
                          id="login-password"
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          className="pr-9"
                          disabled={checkingSession}
                          {...field}
                        />
                      </FormControl>
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={isSubmitting || checkingSession}>
                {(isSubmitting || checkingSession) && <Loader2 className="h-4 w-4 animate-spin" />}
                {isSubmitting ? "Signing in..." : checkingSession ? "Checking session..." : "Sign In"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-xs text-slate-500">
            New hospital or clinic?{" "}
            <Link href="/request-onboarding" className="font-medium text-primary hover:underline">
              Request onboarding
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
