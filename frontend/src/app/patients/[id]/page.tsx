"use client";

import React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calendar,
  Droplet,
  FileText,
  FlaskConical,
  Home,
  Image as ImageIcon,
  MapPin,
  Phone,
  ShieldCheck,
  Stethoscope,
  Ticket,
  Wallet,
  Users,
  Mail,
  BadgeCheck,
  Clock,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoadingState } from "@/components/states/loading-state";
import { useAuth } from "@/hooks/use-auth";
import {
  fromBackendPatient,
  getPatient,
  getPatientPhotoBlobUrl,
  PatientViewModel,
} from "@/lib/patient-api";
import { listInvoices } from "@/lib/billing-api";
import { INVOICE_STATUS_BADGE_CLASS, InvoiceStatus } from "@/types/billing";

function EmptyTabState({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
      <CardContent className="p-10 text-center space-y-2">
        <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center mx-auto">
          <Icon className="w-5 h-5" />
        </div>
        <p className="text-sm font-semibold text-slate-700">{title}</p>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">{description}</p>
      </CardContent>
    </Card>
  );
}

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

function PatientBillingTab({ patientId }: { patientId: string }) {
  const { hasPermission } = useAuth();
  const canView = hasPermission("billing.view");
  const canCreate = hasPermission("billing.invoice.create");

  // `enabled: canView` avoids a 403 (which would trip the API client's
  // generic redirect and yank the user off this whole patient profile
  // page) for a role that can view the patient but not the billing module.
  const invoicesQuery = useQuery({
    queryKey: ["billing-invoices", { patientId }],
    queryFn: () => listInvoices({ patient_id: patientId }),
    enabled: canView,
  });
  const invoices = invoicesQuery.data ?? [];

  if (!canView) {
    return (
      <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
        <CardContent className="p-10 text-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center mx-auto">
            <Wallet className="w-5 h-5" />
          </div>
          <p className="text-sm font-semibold text-slate-700">Billing access restricted</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            You don&apos;t have permission to view this patient&apos;s billing records.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (invoicesQuery.isLoading) {
    return <p className="text-xs text-slate-400 py-8 text-center">Loading billing records...</p>;
  }

  if (invoices.length === 0) {
    return (
      <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
        <CardContent className="p-10 text-center space-y-3">
          <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center mx-auto">
            <Wallet className="w-5 h-5" />
          </div>
          <p className="text-sm font-semibold text-slate-700">No billing records</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">No invoices have been created for this patient yet.</p>
          {canCreate && (
            <Button size="sm" className="text-xs" asChild>
              <Link href={`/billing/new?patientId=${patientId}`}>Create Invoice</Link>
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-xs border-slate-200">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Invoices</h3>
          {canCreate && (
            <Button size="sm" variant="outline" className="text-xs" asChild>
              <Link href={`/billing/new?patientId=${patientId}`}>New Invoice</Link>
            </Button>
          )}
        </div>
        <div className="divide-y divide-slate-100 border border-slate-200 rounded-md">
          {invoices.map((invoice) => (
            <Link
              key={invoice.id}
              href={`/billing/invoices/${invoice.id}`}
              className="flex items-center justify-between px-3 py-2.5 hover:bg-slate-50 transition-colors"
            >
              <div>
                <div className="text-xs font-mono font-semibold text-slate-900">{invoice.invoiceNumber}</div>
                <div className="text-[11px] text-slate-500">{new Date(invoice.invoiceDate).toLocaleDateString()}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-900">{currency(invoice.totalAmount)}</span>
                <Badge variant="outline" className={INVOICE_STATUS_BADGE_CLASS[invoice.status as InvoiceStatus]}>
                  {invoice.status.replace("_", " ")}
                </Badge>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value?: React.ReactNode }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
      <div>
        <p className="text-[11px] text-slate-500">{label}</p>
        <div className="text-sm text-slate-800 font-medium">{value}</div>
      </div>
    </div>
  );
}

async function fetchPatientViewModel(id: string): Promise<PatientViewModel> {
  // A real API failure (401/403/404/500 - anything the backend actually
  // responded with) must NOT be swallowed: let it propagate so the page's
  // `isError` state renders instead of silently pretending the patient
  // doesn't exist. We only tolerate a genuine network error (dev backend
  // not running at all) by rethrowing as-is too - there is no mock
  // fallback anymore since that could mask a real 403/404 as "not found".
  const backendPatient = await getPatient(id);
  const viewModel = fromBackendPatient(backendPatient);

  if (viewModel.primaryPhotoId) {
    try {
      viewModel.photoUrl = await getPatientPhotoBlobUrl(id, viewModel.primaryPhotoId);
    } catch (err) {
      // Non-fatal: the profile still renders without a photo.
      console.warn("Failed to load patient photo", err);
    }
  }

  return viewModel;
}

export default function PatientProfilePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;

  const { data: patient, isLoading, isError } = useQuery({
    queryKey: ["patient", patientId],
    queryFn: () => fetchPatientViewModel(patientId),
    enabled: !!patientId,
    retry: false,
  });

  if (isLoading) {
    return (
      <AppShell>
        <PageLoadingState label="Loading patient profile..." />
      </AppShell>
    );
  }

  if (isError || !patient) {
    return (
      <AppShell>
        <PageContainer>
          <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
            <CardContent className="p-12 text-center space-y-3">
              <p className="text-sm font-semibold text-slate-700">Patient not found</p>
              <p className="text-xs text-slate-500">
                We couldn&apos;t find a patient record for this ID.
              </p>
              <Button size="sm" variant="outline" onClick={() => router.push("/patients")} className="gap-1.5 text-xs">
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Patient Directory
              </Button>
            </CardContent>
          </Card>
        </PageContainer>
      </AppShell>
    );
  }

  const initials = `${patient.displayName.split(" ")[0]?.[0] ?? ""}${
    patient.displayName.split(" ").slice(-1)[0]?.[0] ?? ""
  }`.toUpperCase();

  return (
    <AppShell>
      <PageContainer>
        <PageHeader
          title="Patient 360"
          description="Complete clinical and administrative profile"
          breadcrumbs={[
            { label: "Patients", href: "/patients" },
            { label: patient.displayName },
          ]}
          actions={
            <Link href="/patients">
              <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Directory
              </Button>
            </Link>
          }
        />

        {/* Patient header band */}
        <Card className="shadow-xs border-slate-200">
          <CardContent className="p-5">
            <div className="flex flex-col md:flex-row md:items-center gap-4">
              <Avatar className="w-16 h-16 border border-slate-200">
                <AvatarImage src={patient.photoUrl || undefined} />
                <AvatarFallback className="text-base">{initials || "PT"}</AvatarFallback>
              </Avatar>

              <div className="flex-1 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-bold text-slate-900">{patient.displayName}</h2>
                  <Badge variant={patient.status === "ACTIVE" ? "active" : "outline"} className="text-[10px]">
                    {patient.status}
                  </Badge>
                  {patient.isMinor && (
                    <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-800 border-amber-200">
                      Minor
                    </Badge>
                  )}
                  {patient.abha.status === "VERIFIED" || patient.abha.status === "LINKED" ? (
                    <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-300 gap-1">
                      <ShieldCheck className="w-3 h-3" />
                      ABHA {patient.abha.status === "VERIFIED" ? "Verified" : "Linked"}
                    </Badge>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
                  <span className="font-mono font-semibold text-slate-900">{patient.uid}</span>
                  <span>MRN: {patient.mrn}</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    {patient.gender} &bull; {patient.ageYears} yrs &bull; DOB {patient.dob}
                  </span>
                  <span className="flex items-center gap-1">
                    <Droplet className="w-3.5 h-3.5 text-rose-400" />
                    {patient.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="demographics">
          <TabsList className="flex-wrap h-auto gap-1">
            <TabsTrigger value="demographics">Demographics</TabsTrigger>
            <TabsTrigger value="current-visit">Current Visit</TabsTrigger>
            <TabsTrigger value="current-admission">Current Admission</TabsTrigger>
            <TabsTrigger value="opd-history">OPD History</TabsTrigger>
            <TabsTrigger value="ipd-history">IPD History</TabsTrigger>
            <TabsTrigger value="lab-history">Lab History</TabsTrigger>
            <TabsTrigger value="billing">Billing</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="consents">Consents</TabsTrigger>
            <TabsTrigger value="abha">ABHA</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>

          <TabsContent value="demographics">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Card className="shadow-xs border-slate-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Contact</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <InfoRow icon={Phone} label="Mobile" value={patient.mobile && `+91 ${patient.mobile}`} />
                  <InfoRow icon={Phone} label="Secondary Phone" value={patient.secondaryPhone && `+91 ${patient.secondaryPhone}`} />
                  <InfoRow icon={Mail} label="Email" value={patient.email} />
                  {!patient.mobile && !patient.secondaryPhone && !patient.email && (
                    <p className="text-xs text-slate-400">No contact details on record.</p>
                  )}
                </CardContent>
              </Card>

              <Card className="shadow-xs border-slate-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Address</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {patient.address ? (
                    <InfoRow
                      icon={MapPin}
                      label="Permanent Address"
                      value={`${patient.address.street}, ${patient.address.city}, ${patient.address.state} - ${patient.address.pincode}, ${patient.address.country}`}
                    />
                  ) : (
                    <p className="text-xs text-slate-400">No address on record.</p>
                  )}
                  <InfoRow icon={Home} label="Marital Status" value={patient.maritalStatus} />
                  <InfoRow icon={Users} label="Occupation" value={patient.occupation} />
                  <InfoRow icon={Users} label="Preferred Language" value={patient.preferredLanguage} />
                </CardContent>
              </Card>

              <Card className="shadow-xs border-slate-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Guardian & Identifiers</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {patient.guardian?.name ? (
                    <InfoRow
                      icon={Users}
                      label={`Guardian (${patient.guardian.relationship ?? "Unspecified"})`}
                      value={`${patient.guardian.name}${patient.guardian.phone ? ` · +91 ${patient.guardian.phone}` : ""}`}
                    />
                  ) : (
                    <p className="text-xs text-slate-400">No guardian on record.</p>
                  )}
                  {patient.identifiers.length > 0 ? (
                    patient.identifiers.map((identifier, index) => (
                      <InfoRow
                        key={index}
                        icon={BadgeCheck}
                        label={identifier.type.replace(/_/g, " ")}
                        value={
                          <span className="flex items-center gap-1.5">
                            {identifier.idNumber}
                            {identifier.isVerified && (
                              <Badge variant="outline" className="text-[9px] bg-emerald-50 text-emerald-700 border-emerald-300">
                                Verified
                              </Badge>
                            )}
                          </span>
                        }
                      />
                    ))
                  ) : (
                    <p className="text-xs text-slate-400">No government ID on record.</p>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="current-visit">
            <EmptyTabState
              icon={Ticket}
              title="No active OPD visit"
              description="This patient has no open OPD visit right now. This tab will populate once the OPD / Token module (Phase 3) is live."
            />
          </TabsContent>

          <TabsContent value="current-admission">
            <EmptyTabState
              icon={Stethoscope}
              title="No active IPD admission"
              description="This patient is not currently admitted. This tab will populate once the IPD / bed management module (Phase 3) is live."
            />
          </TabsContent>

          <TabsContent value="opd-history">
            <EmptyTabState
              icon={Ticket}
              title="No OPD visits recorded"
              description="Past OPD visits will appear here once the OPD module (Phase 3) is live."
            />
          </TabsContent>

          <TabsContent value="ipd-history">
            <EmptyTabState
              icon={Stethoscope}
              title="No IPD admissions recorded"
              description="Past IPD admissions will appear here once the IPD module (Phase 3) is live."
            />
          </TabsContent>

          <TabsContent value="lab-history">
            <EmptyTabState
              icon={FlaskConical}
              title="No lab results recorded"
              description="Lab orders and results will appear here once the Laboratory module (Phase 4) is live."
            />
          </TabsContent>

          <TabsContent value="billing">
            <PatientBillingTab patientId={patient.id} />
          </TabsContent>

          <TabsContent value="documents">
            {patient.photoUrl ? (
              <Card className="shadow-xs border-slate-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Patient Photo</CardTitle>
                </CardHeader>
                <CardContent>
                  <img
                    src={patient.photoUrl}
                    alt={patient.displayName}
                    className="w-32 h-32 rounded-lg object-cover border border-slate-200"
                  />
                </CardContent>
              </Card>
            ) : (
              <EmptyTabState
                icon={ImageIcon}
                title="No documents uploaded"
                description="Photos, ID proofs, and generated documents (ID card, wristband) will appear here."
              />
            )}
          </TabsContent>

          <TabsContent value="consents">
            <EmptyTabState
              icon={FileText}
              title="No consent forms on record"
              description="Signed consent forms will appear here once the documents / consent workflow is live."
            />
          </TabsContent>

          <TabsContent value="abha">
            <Card className="shadow-xs border-teal-200 bg-teal-50/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  Ayushman Bharat Digital Mission (ABHA)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={
                      patient.abha.status === "VERIFIED" || patient.abha.status === "LINKED"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                        : "bg-amber-50 text-amber-800 border-amber-300"
                    }
                  >
                    {patient.abha.status}
                  </Badge>
                </div>
                <InfoRow icon={BadgeCheck} label="ABHA Number" value={patient.abha.abhaNumber} />
                <InfoRow icon={BadgeCheck} label="ABHA Address" value={patient.abha.abhaAddress} />
                <InfoRow
                  icon={Clock}
                  label="Verified / Linked At"
                  value={patient.abha.verifiedAt && new Date(patient.abha.verifiedAt).toLocaleString()}
                />
                {!patient.abha.abhaNumber && !patient.abha.abhaAddress && (
                  <p className="text-xs text-slate-500">
                    This patient hasn&apos;t linked an ABHA ID yet. The internal Patient UID above remains the
                    permanent identifier regardless of ABHA linkage status.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="timeline">
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="relative border-l border-slate-200 ml-2 space-y-6">
                  {patient.registeredAt && (
                    <li className="ml-4">
                      <div className="absolute w-2.5 h-2.5 bg-primary rounded-full -left-1.25 mt-1.5 border border-white" />
                      <p className="text-xs text-slate-500">
                        {new Date(patient.registeredAt).toLocaleString()}
                      </p>
                      <p className="text-sm font-medium text-slate-800">
                        Patient registered{patient.registeredBy ? ` by ${patient.registeredBy}` : ""}
                      </p>
                    </li>
                  )}
                  {patient.abha.verifiedAt && (
                    <li className="ml-4">
                      <div className="absolute w-2.5 h-2.5 bg-teal-500 rounded-full -left-1.25 mt-1.5 border border-white" />
                      <p className="text-xs text-slate-500">
                        {new Date(patient.abha.verifiedAt).toLocaleString()}
                      </p>
                      <p className="text-sm font-medium text-slate-800">
                        ABHA {patient.abha.status === "LINKED" ? "linked" : "verified"}
                      </p>
                    </li>
                  )}
                  {!patient.registeredAt && !patient.abha.verifiedAt && (
                    <p className="text-xs text-slate-400 ml-4">No timeline events recorded yet.</p>
                  )}
                  <li className="ml-4 opacity-50">
                    <div className="absolute w-2.5 h-2.5 bg-slate-300 rounded-full -left-1.25 mt-1.5 border border-white" />
                    <p className="text-xs text-slate-400">Upcoming</p>
                    <p className="text-sm font-medium text-slate-500">
                      OPD visits, IPD admissions, lab orders, and billing events will appear here as those
                      modules ship.
                    </p>
                  </li>
                </ol>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </PageContainer>
    </AppShell>
  );
}
