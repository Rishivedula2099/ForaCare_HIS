"use client";

import React, { useState, useEffect, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  UserPlus,
  ArrowLeft,
  User,
  Phone,
  MapPin,
  Shield,
  CreditCard,
  Save,
  RotateCcw,
  Sparkles,
  AlertCircle,
  Calendar,
  Baby,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";

import {
  patientRegistrationFormSchema,
  PatientRegistrationFormData,
  TITLES,
  GENDERS,
  BLOOD_GROUPS,
  MARITAL_STATUSES,
  GUARDIAN_RELATIONSHIPS,
  IDENTITY_TYPES,
  INDIAN_STATES_AND_UTS,
  Patient,
} from "@/types/patient";
import { calculateAgeFromDob, calculateDobFromAge } from "@/lib/patient-store";
import {
  checkDuplicates as apiCheckDuplicates,
  createPatient,
  toCreatePayload,
  toDuplicateCheckPayload,
  toPatient,
  uploadPatientPhoto,
} from "@/lib/patient-api";
import { ApiError } from "@/types/api";
import { PhotoCapture } from "@/components/patients/photo-capture";
import { AbhaCard } from "@/components/patients/abha-card";
import { DuplicateAlert } from "@/components/patients/duplicate-alert";
import { RegistrationSuccessDialog } from "@/components/patients/registration-success-dialog";
import { useAuthContext } from "@/providers/auth-provider";
import { ShieldAlert } from "lucide-react";

export default function PatientRegistrationPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { hasPermission } = useAuthContext();
  const [isPending, startTransition] = useTransition();

  const [duplicates, setDuplicates] = useState<Patient[]>([]);
  const [registeredPatient, setRegisteredPatient] = useState<Patient | null>(null);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);

  // Form Setup with default values
  const form = useForm({
    resolver: zodResolver(patientRegistrationFormSchema),
    defaultValues: {
      title: "Mr.",
      firstName: "",
      middleName: "",
      lastName: "",
      gender: "MALE",
      dob: "",
      ageYears: 0,
      ageMonths: 0,
      ageDays: 0,
      bloodGroup: "UNKNOWN",
      maritalStatus: "SINGLE",
      occupation: "",
      preferredLanguage: "English",
      mobile: "",
      secondaryPhone: "",
      email: "",
      street: "",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "",
      country: "India",
      guardianName: "",
      guardianRelationship: "FATHER",
      guardianPhone: "",
      guardianAddressSameAsPatient: true,
      guardianAddress: "",
      identityType: "AADHAAR",
      identityNumber: "",
      photoUrl: "",
      abhaNumber: "",
      abhaAddress: "",
      abhaStatus: "UNVERIFIED",
    },
    mode: "onBlur",
  });

  const { watch, setValue, getValues, reset } = form;

  const watchedDob = watch("dob");
  const watchedAgeYears = watch("ageYears");
  const watchedMobile = watch("mobile");
  const watchedIdentityNumber = watch("identityNumber");
  const watchedFirstName = watch("firstName");
  const watchedLastName = watch("lastName");
  const watchedPhotoUrl = watch("photoUrl");
  const watchedAbhaNumber = watch("abhaNumber");
  const watchedAbhaAddress = watch("abhaAddress");
  const watchedAbhaStatus = watch("abhaStatus");

  const isMinor = (watchedAgeYears || 0) < 18;

  // Sync Age whenever DOB changes
  const handleDobChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDob = e.target.value;
    setValue("dob", newDob, { shouldValidate: true });
    if (newDob) {
      const { years, months, days } = calculateAgeFromDob(newDob);
      setValue("ageYears", years, { shouldValidate: true });
      setValue("ageMonths", months);
      setValue("ageDays", days);
    }
  };

  // Sync approximate DOB whenever Age changes
  const handleAgeYearsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    const years = isNaN(val) ? 0 : val;
    setValue("ageYears", years, { shouldValidate: true });
    if (!watchedDob || years > 0) {
      const approxDob = calculateDobFromAge(years);
      setValue("dob", approxDob, { shouldValidate: true });
    }
  };

  // Real-time Deduplication Check - debounced call to the backend
  // `check-duplicates` endpoint instead of scanning localStorage.
  useEffect(() => {
    if (!hasPermission("patients.manage")) return;

    const hasEnoughSignal =
      (watchedMobile && watchedMobile.length >= 10) ||
      (watchedIdentityNumber && watchedIdentityNumber.length >= 4) ||
      (watchedFirstName && watchedLastName && watchedDob);

    if (!hasEnoughSignal) {
      setDuplicates([]);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const matches = await apiCheckDuplicates(
          toDuplicateCheckPayload({
            mobile: watchedMobile,
            identityNumber: watchedIdentityNumber,
            firstName: watchedFirstName,
            lastName: watchedLastName,
            dob: watchedDob,
          })
        );
        if (!cancelled) {
          setDuplicates(matches.map(toPatient));
        }
      } catch (err) {
        console.warn("Duplicate check failed", err);
        if (!cancelled) setDuplicates([]);
      }
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [watchedMobile, watchedIdentityNumber, watchedFirstName, watchedLastName, watchedDob, hasPermission]);

  // Form Submission
  const onSubmit = (data: PatientRegistrationFormData) => {
    startTransition(async () => {
      try {
        const backendPatient = await createPatient(toCreatePayload(data));
        const createdPatient = toPatient(backendPatient);

        setRegisteredPatient(createdPatient);
        setShowSuccessDialog(true);
        toast({
          title: "Registration Complete",
          description: `Patient ${createdPatient.fullName} assigned UID: ${createdPatient.uid}`,
        });

        // Fire-and-forget photo upload - don't block the success dialog on it.
        if (data.photoUrl) {
          fetch(data.photoUrl)
            .then((res) => res.blob())
            .then((blob) => uploadPatientPhoto(createdPatient.id, blob))
            .catch((err) => {
              console.error("Photo upload failed:", err);
              toast({
                title: "Photo Upload Failed",
                description: "The patient record was saved, but the photo could not be uploaded. You can retry from the patient profile.",
                variant: "destructive",
              });
            });
        }
      } catch (err) {
        const apiErr = err as ApiError;
        if (apiErr?.status_code === 409) {
          // Backend detected a duplicate on create but doesn't return the
          // matches in the 409 body - fetch them separately to show in the
          // DuplicateAlert.
          try {
            const matches = await apiCheckDuplicates(
              toDuplicateCheckPayload({
                mobile: data.mobile,
                identityNumber: data.identityNumber,
                firstName: data.firstName,
                lastName: data.lastName,
                dob: data.dob,
              })
            );
            setDuplicates(matches.map(toPatient));
          } catch (dupErr) {
            console.warn("Failed to fetch duplicates after 409", dupErr);
          }
          toast({
            title: "Possible Duplicate Patient",
            description: "A matching patient record already exists. Review the duplicates below before proceeding.",
            variant: "destructive",
          });
          return;
        }

        console.error("Registration error:", err);
        toast({
          title: "Registration Failed",
          description: apiErr?.message || "An error occurred while saving patient record. Please try again.",
          variant: "destructive",
        });
      }
    });
  };

  const handleRegisterAnother = () => {
    setShowSuccessDialog(false);
    setRegisteredPatient(null);
    setDuplicates([]);
    reset();
  };

  if (!hasPermission("patients.manage")) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto pb-12">
          <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
            <CardContent className="p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center mx-auto">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-800">Access Restricted</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  You don&apos;t have permission to register patients. Contact your facility administrator if you
                  believe this is a mistake.
                </p>
              </div>
              <div className="pt-2">
                <Link href="/patients">
                  <Button size="sm" variant="outline" className="gap-1.5 text-xs">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Back to Patient Directory
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto pb-12">
        {/* Page Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Link
                href="/patients"
                className="text-xs font-semibold text-slate-500 hover:text-primary inline-flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Patient Directory
              </Link>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-primary" />
              New Patient Registration (P2-F01)
            </h1>
            <p className="text-xs text-slate-500">
              Create master demographic profile, assign permanent Hospital Patient UID, and link ABHA.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => reset()}
              className="gap-1.5 text-xs bg-white shadow-2xs"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              Reset Form
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={form.handleSubmit(onSubmit)}
              disabled={isPending}
              className="gap-1.5 text-xs bg-primary text-white shadow-xs hover:bg-primary/90"
            >
              <Save className="w-3.5 h-3.5" />
              {isPending ? "Generating UID..." : "Save & Register Patient"}
            </Button>
          </div>
        </div>

        {/* Real-time Deduplication Alert */}
        <DuplicateAlert
          duplicates={duplicates}
          onDismiss={() => setDuplicates([])}
        />

        {/* Form Container */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Section 1: Patient Photo & Basic Demographics */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3 border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm font-bold text-slate-900">
                      1. Patient Photograph &amp; Demographics
                    </CardTitle>
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium">* Required fields</span>
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {/* Photo Capture UI */}
                <PhotoCapture
                  value={watchedPhotoUrl}
                  onChange={(photo) => setValue("photoUrl", photo)}
                  patientName={`${watchedFirstName || ""} ${watchedLastName || ""}`.trim() || "Patient"}
                />

                {/* Name Fields Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                  <div className="sm:col-span-2">
                    <FormField
                      control={form.control}
                      name="title"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Title *</FormLabel>
                          <FormControl>
                            <Select
                              options={TITLES.map((t) => ({ value: t.value, label: t.label }))}
                              value={field.value}
                              onChange={field.onChange}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="sm:col-span-4">
                    <FormField
                      control={form.control}
                      name="firstName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>First Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Ramesh" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="sm:col-span-3">
                    <FormField
                      control={form.control}
                      name="middleName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Middle Name</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Kumar" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="sm:col-span-3">
                    <FormField
                      control={form.control}
                      name="lastName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Last Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Sharma" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                {/* DOB & Age Interactive 2-Way Sync Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-start p-3.5 rounded-lg bg-slate-50 border border-slate-200/80">
                  <div className="sm:col-span-4">
                    <FormField
                      control={form.control}
                      name="dob"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-primary" />
                            Date of Birth (DOB) *
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="date"
                              value={field.value}
                              onChange={handleDobChange}
                              max={new Date().toISOString().split("T")[0]}
                              className="bg-white"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <FormField
                      control={form.control}
                      name="ageYears"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Age (Years) *</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={0}
                              max={130}
                              value={field.value || 0}
                              onChange={handleAgeYearsChange}
                              className="bg-white text-center font-bold"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <FormItem>
                      <FormLabel className="text-slate-500">Months</FormLabel>
                      <Input
                        type="number"
                        disabled
                        value={form.watch("ageMonths") || 0}
                        className="bg-slate-100/80 text-center text-slate-600"
                      />
                    </FormItem>
                  </div>

                  <div className="sm:col-span-2">
                    <FormItem>
                      <FormLabel className="text-slate-500">Days</FormLabel>
                      <Input
                        type="number"
                        disabled
                        value={form.watch("ageDays") || 0}
                        className="bg-slate-100/80 text-center text-slate-600"
                      />
                    </FormItem>
                  </div>

                  <div className="sm:col-span-2 pt-6 flex items-center">
                    {isMinor ? (
                      <Badge className="bg-amber-100 text-amber-800 border-amber-300 gap-1 text-[10px]">
                        <Baby className="w-3 h-3 text-amber-600" />
                        Minor Patient
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] text-slate-600 bg-white">
                        Adult Patient
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Gender, Blood Group, Marital Status */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <FormField
                    control={form.control}
                    name="gender"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Gender *</FormLabel>
                        <FormControl>
                          <Select
                            options={GENDERS.map((g) => ({ value: g.value, label: g.label }))}
                            value={field.value}
                            onChange={field.onChange}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="bloodGroup"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Blood Group</FormLabel>
                        <FormControl>
                          <Select
                            options={BLOOD_GROUPS.map((b) => ({ value: b.value, label: b.label }))}
                            value={field.value}
                            onChange={field.onChange}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="maritalStatus"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Marital Status</FormLabel>
                        <FormControl>
                          <Select
                            options={MARITAL_STATUSES.map((m) => ({ value: m.value, label: m.label }))}
                            value={field.value}
                            onChange={field.onChange}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="preferredLanguage"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Preferred Language</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Kannada, Hindi, English" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 2: Contact & Address Information */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-primary" />
                  <CardTitle className="text-sm font-bold text-slate-900">
                    2. Contact Numbers &amp; Residential Address
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {/* Contact numbers */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <FormField
                    control={form.control}
                    name="mobile"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Primary Mobile Number *</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <span className="absolute left-3 top-2 text-xs font-semibold text-slate-500">
                              +91
                            </span>
                            <Input
                              placeholder="98765 43210"
                              className="pl-11 font-mono"
                              maxLength={10}
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="secondaryPhone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Secondary / Alternate Phone</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <span className="absolute left-3 top-2 text-xs font-semibold text-slate-500">
                              +91
                            </span>
                            <Input
                              placeholder="Alternate number"
                              className="pl-11 font-mono"
                              maxLength={10}
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email Address</FormLabel>
                        <FormControl>
                          <Input placeholder="patient@example.com" type="email" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Address */}
                <div className="space-y-3 pt-2 border-t border-slate-100">
                  <FormField
                    control={form.control}
                    name="street"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Street Address / House No / Locality *</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Flat 301, Lakeview Residency, 5th Cross Road" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <FormField
                      control={form.control}
                      name="city"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>City / District *</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Bengaluru" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="state"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>State / UT *</FormLabel>
                          <FormControl>
                            <Select
                              options={INDIAN_STATES_AND_UTS.map((st) => ({ value: st, label: st }))}
                              value={field.value}
                              onChange={field.onChange}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="pincode"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>PIN Code *</FormLabel>
                          <FormControl>
                            <Input placeholder="560001" maxLength={6} className="font-mono" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="country"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Country</FormLabel>
                          <FormControl>
                            <Input disabled value="India" className="bg-slate-50" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Section 3: Guardian & Emergency Contact */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3 border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary" />
                    <CardTitle className="text-sm font-bold text-slate-900">
                      3. Guardian &amp; Emergency Contact Details
                    </CardTitle>
                  </div>
                  {isMinor && (
                    <Badge className="bg-amber-500 text-white text-[10px]">
                      Mandatory for Minors
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-xs">
                  Mandatory for minor patients (&lt; 18 years); recommended for senior citizens and emergency contact.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <FormField
                    control={form.control}
                    name="guardianName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Guardian / Contact Name {isMinor ? "*" : ""}
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Vikram Patel" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="guardianRelationship"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Relationship {isMinor ? "*" : ""}
                        </FormLabel>
                        <FormControl>
                          <Select
                            options={GUARDIAN_RELATIONSHIPS.map((r) => ({ value: r.value, label: r.label }))}
                            value={field.value}
                            onChange={field.onChange}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="guardianPhone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Guardian Mobile / Phone</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <span className="absolute left-3 top-2 text-xs font-semibold text-slate-500">
                              +91
                            </span>
                            <Input
                              placeholder="Guardian Phone"
                              className="pl-11 font-mono"
                              maxLength={10}
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 4: Approved Identity References & Government ID */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-primary" />
                  <CardTitle className="text-sm font-bold text-slate-900">
                    4. Approved Government Identity References
                  </CardTitle>
                </div>
                <CardDescription className="text-xs">
                  Select and record official identity documents for clinical records and search indexing.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="identityType"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Primary Identity Type</FormLabel>
                        <FormControl>
                          <Select
                            options={IDENTITY_TYPES.map((id) => ({ value: id.value, label: id.label }))}
                            value={field.value}
                            onChange={field.onChange}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="identityNumber"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Identity Document Number</FormLabel>
                        <FormControl>
                          <Input
                            placeholder={
                              form.watch("identityType") === "AADHAAR"
                                ? "12-digit Aadhaar Number"
                                : form.watch("identityType") === "PAN_CARD"
                                ? "10-character PAN (e.g. ABCDE1234F)"
                                : "Document ID / Number"
                            }
                            className="font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 5: ABHA / ABDM Integration */}
            <AbhaCard
              abhaNumber={watchedAbhaNumber || ""}
              abhaAddress={watchedAbhaAddress || ""}
              status={watchedAbhaStatus || "UNVERIFIED"}
              mobile={watchedMobile || ""}
              onAbhaChange={({ abhaNumber, abhaAddress, status }) => {
                setValue("abhaNumber", abhaNumber || "");
                setValue("abhaAddress", abhaAddress || "");
                setValue("abhaStatus", status);
              }}
            />

            {/* Bottom Sticky Action Bar */}
            <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-slate-200 shadow-sm sticky bottom-4 z-10">
              <div className="text-xs text-slate-500">
                Facility: <strong>ForaCare City Hospital (FC01)</strong> • Desk: <strong>Registration</strong>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => reset()}
                  className="text-xs"
                >
                  Clear
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isPending}
                  className="bg-primary text-white gap-1.5 text-xs px-5 shadow-xs hover:bg-primary/90"
                >
                  <Save className="w-4 h-4" />
                  {isPending ? "Registering Patient..." : "Complete Registration"}
                </Button>
              </div>
            </div>
          </form>
        </Form>

        {/* Success Modal */}
        <RegistrationSuccessDialog
          patient={registeredPatient}
          open={showSuccessDialog}
          onOpenChange={setShowSuccessDialog}
          onRegisterAnother={handleRegisterAnother}
        />
      </div>
    </AppShell>
  );
}
