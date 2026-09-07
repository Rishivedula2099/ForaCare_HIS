"use client";

import * as React from "react";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Eye, EyeOff, ShieldCheck, Building2 } from "lucide-react";
import { Logo } from "@/components/common/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { DEMO_PRESETS, MOCK_FACILITIES } from "@/lib/auth-mock";
import { ROLE_METADATA_MAP } from "@/types/auth";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required."),
  password: z.string().min(1, "Password is required."),
  facility_id: z.string().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const FACILITY_OPTIONS = MOCK_FACILITIES.map((facility) => ({
  value: facility.id,
  label: `${facility.name} (${facility.facility_code})`,
}));

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") || "/";

  const [showPassword, setShowPassword] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "", facility_id: FACILITY_OPTIONS[0]?.value },
  });

  const applyPreset = (username: string, password: string) => {
    form.setValue("username", username);
    form.setValue("password", password);
    setFormError(null);
  };

  const onSubmit = async (values: LoginFormValues) => {
    setIsSubmitting(true);
    setFormError(null);
    try {
      await login(values);
      router.push(redirectTo);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to sign in. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-slate-50">
      {/* Left brand showcase */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-[#04222b] text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 [background-image:radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] [background-size:24px_24px]" />
        <div className="relative z-10">
          <Logo variant="icon" size="lg" className="mb-10" />
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
            NABH / ISO 27001 / ABDM Ready
          </div>
          <p className="text-slate-500">&copy; {new Date().getFullYear()} ForaSoftware. All rights reserved.</p>
        </div>
      </div>

      {/* Right access portal */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden">
            <Logo variant="full" size="md" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Sign in to your workspace</h2>
            <p className="text-sm text-slate-500 mt-1">Enter your staff credentials to continue.</p>
          </div>

          {formError && (
            <Alert variant="destructive">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="facility_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="flex items-center gap-1.5">
                      <Building2 className="h-3.5 w-3.5" /> Hospital / Facility
                    </FormLabel>
                    <FormControl>
                      <Select
                        options={FACILITY_OPTIONS}
                        value={field.value}
                        onChange={field.onChange}
                        placeholder="Select a facility"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username or Email</FormLabel>
                    <FormControl>
                      <Input autoComplete="username" placeholder="e.g. dr.priya" {...field} />
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
                      <FormLabel>Password</FormLabel>
                      <Link href="/forgot-password" className="text-[11px] font-medium text-primary hover:underline">
                        Forgot password?
                      </Link>
                    </div>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          className="pr-9"
                          {...field}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword((prev) => !prev)}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                          tabIndex={-1}
                        >
                          {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          </Form>

          <div className="pt-4 border-t border-slate-200">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Quick Demo Role Switcher
            </p>
            <div className="flex flex-wrap gap-1.5">
              {DEMO_PRESETS.map((preset) => (
                <button
                  key={preset.username}
                  type="button"
                  onClick={() => applyPreset(preset.username, preset.password)}
                  className="text-[11px] font-medium px-2.5 py-1 rounded-full border border-slate-200 bg-white text-slate-600 hover:border-primary hover:text-primary transition-colors"
                >
                  {ROLE_METADATA_MAP[preset.role].label}
                </button>
              ))}
            </div>
          </div>
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
