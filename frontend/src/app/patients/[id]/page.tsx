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
import { apiClient } from "@/lib/api-client";
import { getPatientById, calculateAgeFromDob } from "@/lib/patient-store";
import { Patient } from "@/types/patient";

interface PatientViewModel {
  id: string;
  uid: string;
  mrn: string;
  displayName: string;
  gender: string;
  dob: string;
  ageYears: number;
  bloodGroup: string;
  maritalStatus?: string;
  occupation?: string;
  preferredLanguage?: string;
  isMinor: boolean;
  status: string;
  photoUrl?: string;
  mobile?: string;
  secondaryPhone?: string;
  email?: string;
  address?: { street: string; city: string; state: string; pincode: string; country: string };
  guardian?: { name?: string; relationship?: string; phone?: string; address?: string };
  identifiers: { type: string; idNumber: string; isVerified: boolean }[];
  abha: { abhaNumber?: string; abhaAddress?: string; status: string; verifiedAt?: string };
  registeredAt?: string;
  registeredBy?: string;
  facilityName?: string;
}

function fromMockPatient(patient: Patient): PatientViewModel {
  return {
    id: patient.id,
    uid: patient.uid,
    mrn: patient.mrn,
    displayName: patient.fullName,
    gender: patient.gender,
    dob: patient.dob,
    ageYears: patient.ageYears,
    bloodGroup: patient.bloodGroup,
    maritalStatus: patient.maritalStatus,
    occupation: patient.occupation,
    preferredLanguage: patient.preferredLanguage,
    isMinor: patient.isMinor,
    status: patient.status,
    photoUrl: patient.photoUrl,
    mobile: patient.mobile,
    secondaryPhone: patient.secondaryPhone,
    email: patient.email,
    address: patient.address,
    guardian: patient.guardian,
    identifiers: patient.primaryIdentity
      ? [
          {
            type: patient.primaryIdentity.type,
            idNumber: patient.primaryIdentity.idNumber,
            isVerified: !!patient.primaryIdentity.isVerified,
          },
        ]
      : [],
    abha: patient.abha,
    registeredAt: patient.registeredAt,
    registeredBy: patient.registeredBy,
    facilityName: patient.facilityName,
  };
}

// Backend `PatientOut` shape (snake_case, nested arrays) - see
// backend/app/modules/patients/schemas.py.
interface BackendPatientOut {
  id: string;
  uid: string;
  mrn: string;
  title: string | null;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  gender: string;
  dob: string;
  blood_group: string;
  marital_status: string | null;
  occupation: string | null;
  preferred_language: string | null;
  is_minor: boolean;
  guardian_name: string | null;
  guardian_relationship: string | null;
  guardian_phone: string | null;
  guardian_address: string | null;
  status: string;
  created_at: string;
  address: { street: string; city: string; state: string; pincode: string; country: string } | null;
  contacts: { contact_type: string; value: string; is_primary: boolean }[];
  photos: { storage_path: string; is_primary: boolean }[];
  identifiers: { identity_type: string; id_number: string; is_verified: boolean }[];
  identity_links: {
    system: string;
    external_id: string | null;
    external_address: string | null;
    status: string;
    linked_at: string | null;
  }[];
}

function fromBackendPatient(patient: BackendPatientOut): PatientViewModel {
  const mobile = patient.contacts.find((c) => c.contact_type === "MOBILE")?.value;
  const secondaryPhone = patient.contacts.find((c) => c.contact_type === "SECONDARY_PHONE")?.value;
  const email = patient.contacts.find((c) => c.contact_type === "EMAIL")?.value;
  const abhaLink = patient.identity_links.find((link) => link.system === "ABHA");
  const primaryPhoto = patient.photos.find((p) => p.is_primary) ?? patient.photos[0];

  return {
    id: patient.id,
    uid: patient.uid,
    mrn: patient.mrn,
    displayName: [patient.title, patient.first_name, patient.middle_name, patient.last_name]
      .filter(Boolean)
      .join(" "),
    gender: patient.gender,
    dob: patient.dob,
    ageYears: calculateAgeFromDob(patient.dob).years,
    bloodGroup: patient.blood_group,
    maritalStatus: patient.marital_status ?? undefined,
    occupation: patient.occupation ?? undefined,
    preferredLanguage: patient.preferred_language ?? undefined,
    isMinor: patient.is_minor,
    status: patient.status,
    photoUrl: primaryPhoto?.storage_path,
    mobile,
    secondaryPhone,
    email,
    address: patient.address ?? undefined,
    guardian: patient.guardian_name
      ? {
          name: patient.guardian_name,
          relationship: patient.guardian_relationship ?? undefined,
          phone: patient.guardian_phone ?? undefined,
          address: patient.guardian_address ?? undefined,
        }
      : undefined,
    identifiers: patient.identifiers.map((identifier) => ({
      type: identifier.identity_type,
      idNumber: identifier.id_number,
      isVerified: identifier.is_verified,
    })),
    abha: {
      abhaNumber: abhaLink?.external_id ?? undefined,
      abhaAddress: abhaLink?.external_address ?? undefined,
      status: abhaLink?.status ?? "UNVERIFIED",
      verifiedAt: abhaLink?.linked_at ?? undefined,
    },
    registeredAt: patient.created_at,
  };
}

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
  try {
    const response = await apiClient.get<BackendPatientOut>(`/patients/${id}`);
    if (response.data) {
      return fromBackendPatient(response.data);
    }
  } catch {
    // Fall through to the localStorage mock below - the registration flow
    // still writes there until it's wired to this API.
  }

  const mockPatient = getPatientById(id);
  if (mockPatient) {
    return fromMockPatient(mockPatient);
  }

  throw new Error("Patient not found");
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
            <EmptyTabState
              icon={Wallet}
              title="No billing records"
              description="Invoices and payments will appear here once the Billing module (Phase 3) is live."
            />
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
