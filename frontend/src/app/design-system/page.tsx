"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AppShell } from "@/components/layout/app-shell";
import { Logo } from "@/components/common/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Drawer, DrawerHeader, DrawerBody, DrawerFooter } from "@/components/ui/drawer";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Pagination } from "@/components/ui/pagination";
import { SearchInput } from "@/components/ui/search-input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useToast } from "@/hooks/use-toast";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form";
import {
  CheckCircle2,
  Trash2,
  Calendar,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";

// Form validation schema
const patientFormSchema = z.object({
  fullName: z.string().min(3, "Patient name must be at least 3 characters"),
  gender: z.string().min(1, "Please select gender"),
  birthDate: z.string().min(1, "Date of birth is required"),
  phone: z.string().regex(/^[6-9]\d{9}$/, "Please enter a valid 10-digit Indian mobile number"),
});

type PatientFormValues = z.infer<typeof patientFormSchema>;

export default function DesignSystemPage() {
  const { toast } = useToast();

  // State for interactive widgets
  const [selectedGender, setSelectedGender] = useState("");
  const [selectedDate, setSelectedDate] = useState("2026-09-07");
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Form setup
  const form = useForm<PatientFormValues>({
    resolver: zodResolver(patientFormSchema),
    defaultValues: {
      fullName: "",
      gender: "",
      birthDate: "",
      phone: "",
    },
  });

  const onSubmitForm = (data: PatientFormValues) => {
    toast({
      title: "Patient Form Validated",
      description: `Registered: ${data.fullName} (${data.gender}), Phone: ${data.phone}`,
      variant: "success",
    });
  };

  return (
    <AppShell>
      <div className="space-y-8 max-w-7xl mx-auto pb-16">
        {/* Page Header */}
        <div className="border-b border-slate-200 pb-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            Design System & Component Library (P1-F03)
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            ForaCare HIS UI Kit
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Comprehensive reusable components built with modern, minimalistic clinical aesthetics matching brand identity.
          </p>
        </div>

        {/* SECTION 1: BRAND IDENTITY & COLOR PALETTE */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            1. Brand Identity & Color Tokens
          </h2>

          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-6 space-y-6">
              {/* Logo Presentation */}
              <div className="p-6 rounded-lg bg-slate-50/70 border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Official Horizontal Vector Logo
                  </span>
                  <div>
                    <Logo variant="full" size="lg" />
                  </div>
                  <p className="text-xs text-slate-500 italic mt-1">
                    "One Patient. One Record. Better Care."
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="p-3 bg-white rounded-lg border border-slate-200 text-center space-y-1 shadow-xs">
                    <span className="text-[10px] text-slate-400 font-semibold block">Icon Only</span>
                    <Logo variant="icon" size="md" />
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200 text-center space-y-1 shadow-xs">
                    <span className="text-[10px] text-slate-400 font-semibold block">Compact Header</span>
                    <Logo variant="compact" size="sm" />
                  </div>
                </div>
              </div>

              {/* Color Swatches */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg border border-slate-200 flex items-center gap-3 bg-white shadow-xs">
                  <div className="w-10 h-10 rounded-lg bg-[#0A858F] shadow-sm shrink-0" />
                  <div>
                    <div className="font-bold text-xs text-slate-900">Medical Teal (Primary)</div>
                    <div className="font-mono text-[11px] text-slate-500">#0A858F</div>
                    <div className="text-[10px] text-slate-400">Emblem cross, active buttons</div>
                  </div>
                </div>

                <div className="p-4 rounded-lg border border-slate-200 flex items-center gap-3 bg-white shadow-xs">
                  <div className="w-10 h-10 rounded-lg bg-[#004565] shadow-sm shrink-0" />
                  <div>
                    <div className="font-bold text-xs text-slate-900">Hospital Navy (Brand)</div>
                    <div className="font-mono text-[11px] text-slate-500">#004565</div>
                    <div className="text-[10px] text-slate-400">Typography, patient silhouette</div>
                  </div>
                </div>

                <div className="p-4 rounded-lg border border-slate-200 flex items-center gap-3 bg-white shadow-xs">
                  <div className="w-10 h-10 rounded-lg bg-[#E86328] shadow-sm shrink-0" />
                  <div>
                    <div className="font-bold text-xs text-slate-900">Vitality Orange (Accent)</div>
                    <div className="font-mono text-[11px] text-slate-500">#E86328</div>
                    <div className="text-[10px] text-slate-400">Healing leaf, sub-branding</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* SECTION 2: BUTTONS & STATUS CHIPS */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            2. Buttons & Clinical Status Chips
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Buttons */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Button Variants & Sizes</CardTitle>
                <CardDescription className="text-xs">
                  Unified styling with keyboard focus rings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="default">Primary Default</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="outline">Outline</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button variant="destructive">Destructive</Button>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                  <Button size="sm">Small (h-8)</Button>
                  <Button size="default">Default (h-9)</Button>
                  <Button size="lg">Large (h-10)</Button>
                </div>
              </CardContent>
            </Card>

            {/* Badges / Chips */}
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Clinical Status Badges</CardTitle>
                <CardDescription className="text-xs">
                  Semantic colors for patient queue, lab, and bed states
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant="waiting">WAITING (Amber)</Badge>
                  <Badge variant="active">IN CONSULTATION (Blue)</Badge>
                  <Badge variant="completed">COMPLETED (Emerald)</Badge>
                  <Badge variant="alert">CRITICAL ALERT (Rose)</Badge>
                  <Badge variant="outline">DISCHARGED (Neutral)</Badge>
                </div>

                <p className="text-xs text-slate-500 pt-2 border-t border-slate-100">
                  Used across OPD Queue, IPD Bed Board, and Laboratory Accession tables.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* SECTION 3: INPUTS, SELECT, DATE PICKER & SEARCH */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            3. Form Controls & Search
          </h2>

          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Standard Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Patient Full Name</label>
                <Input placeholder="e.g. Ramesh Kumar" />
                <span className="text-[10px] text-slate-400">Standard text input</span>
              </div>

              {/* Select */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Department</label>
                <Select
                  value={selectedGender}
                  onChange={setSelectedGender}
                  placeholder="Choose Department..."
                  options={[
                    { value: "CARD", label: "Cardiology" },
                    { value: "GENMED", label: "General Medicine" },
                    { value: "ORTHO", label: "Orthopedics" },
                    { value: "PED", label: "Pediatrics" },
                    { value: "PATH", label: "Pathology Lab" },
                  ]}
                />
                <span className="text-[10px] text-slate-400">Custom accessible select</span>
              </div>

              {/* DatePicker */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Admission / Visit Date</label>
                <DatePicker
                  value={selectedDate}
                  onChange={setSelectedDate}
                  showPresets={true}
                />
                <span className="text-[10px] text-slate-400">With Today/Yesterday shortcuts</span>
              </div>

              {/* SearchInput */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Live Search</label>
                <SearchInput
                  placeholder="Type to search patients..."
                  shortcutBadge="/"
                  onSearchChange={setSearchQuery}
                />
                <span className="text-[10px] text-slate-400">
                  {searchQuery ? `Query: "${searchQuery}"` : "Debounced 300ms"}
                </span>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* SECTION 4: FORM WITH VALIDATION (REACT HOOK FORM + ZOD) */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            4. Form Components (React Hook Form + Zod)
          </h2>

          <Card className="shadow-xs border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Patient Quick Registration Schema</CardTitle>
              <CardDescription className="text-xs">
                Real-time validation with error messages and accessible ARIA attributes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit(onSubmitForm)}
                  className="grid grid-cols-1 md:grid-cols-4 gap-4"
                >
                  <FormField
                    control={form.control}
                    name="fullName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full Legal Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter patient name..." {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="gender"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Gender</FormLabel>
                        <FormControl>
                          <Select
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="Select gender..."
                            options={[
                              { value: "MALE", label: "Male" },
                              { value: "FEMALE", label: "Female" },
                              { value: "OTHER", label: "Other" },
                            ]}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="birthDate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Date of Birth</FormLabel>
                        <FormControl>
                          <DatePicker
                            value={field.value}
                            onChange={field.onChange}
                            maxDate="2026-09-07"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>10-Digit Mobile</FormLabel>
                        <FormControl>
                          <Input placeholder="9876543210" maxLength={10} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="md:col-span-4 flex justify-end gap-2 pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => form.reset()}
                    >
                      Reset Form
                    </Button>
                    <Button type="submit" size="sm">
                      Validate & Submit
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </section>

        {/* SECTION 5: MODALS, DRAWERS, TOASTS & CONFIRM DIALOG */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            5. Modals, Drawers, Toasts & Confirmation Dialogs
          </h2>

          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-6">
              <div className="flex flex-wrap items-center gap-3">
                {/* Modal Dialog Trigger */}
                <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
                  Open Modal Dialog
                </Button>

                {/* Slide-over Drawer Trigger */}
                <Button variant="outline" size="sm" onClick={() => setDrawerOpen(true)}>
                  Open Slide Drawer
                </Button>

                {/* Confirm Dialog Trigger */}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmOpen(true)}
                  className="gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Cancel Token (Confirm)
                </Button>

                {/* Toast Triggers */}
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() =>
                    toast({
                      title: "Prescription Saved",
                      description: "Prescription generated and signed for Patient FC01-202609-000102.",
                      variant: "success",
                    })
                  }
                >
                  Trigger Success Toast
                </Button>

                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() =>
                    toast({
                      title: "Bed Allocation Failed",
                      description: "Bed ICU-02 was locked by another nursing station.",
                      variant: "destructive",
                    })
                  }
                >
                  Trigger Error Toast
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* SECTION 6: ALERTS */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            6. Alert Banners
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Alert variant="info">
              <AlertTitle>ABDM Integration Sandbox Active</AlertTitle>
              <AlertDescription>
                System running against local Mock ABDM Adapter. Live ABHA linking available for sandbox testing.
              </AlertDescription>
            </Alert>

            <Alert variant="success">
              <AlertTitle>Shift Settlement Completed</AlertTitle>
              <AlertDescription>
                Cashier shift #1 closed successfully. Net collections: ₹1,84,200 reconciled.
              </AlertDescription>
            </Alert>

            <Alert variant="warning">
              <AlertTitle>Ward Capacity Warning</AlertTitle>
              <AlertDescription>
                ICU occupancy has reached 90% (9 of 10 beds occupied).
              </AlertDescription>
            </Alert>

            <Alert variant="destructive">
              <AlertTitle>Critical Laboratory Result</AlertTitle>
              <AlertDescription>
                Hemoglobin value 6.2 g/dL flagged below critical limit for Patient FC01-202609-000105.
              </AlertDescription>
            </Alert>
          </div>
        </section>

        {/* SECTION 7: TABLE & PAGINATION */}
        <section className="space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            7. Data Grid & Pagination
          </h2>

          <Card className="shadow-xs border-slate-200">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">Token</TableHead>
                    <TableHead>Patient UID & Name</TableHead>
                    <TableHead>Department</TableHead>
                    <TableHead>Attending Doctor</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-mono font-bold text-slate-900">CAR-014</TableCell>
                    <TableCell>
                      <span className="font-semibold text-slate-900 block">Sunita Verma</span>
                      <span className="font-mono text-[10px] text-slate-400">FC01-202609-000102</span>
                    </TableCell>
                    <TableCell className="text-xs">Cardiology</TableCell>
                    <TableCell className="text-xs">Dr. Priya Raman</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="active">In Consultation</Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-mono font-bold text-slate-900">GEN-022</TableCell>
                    <TableCell>
                      <span className="font-semibold text-slate-900 block">Rajesh Kumar</span>
                      <span className="font-mono text-[10px] text-slate-400">FC01-202609-000105</span>
                    </TableCell>
                    <TableCell className="text-xs">General Medicine</TableCell>
                    <TableCell className="text-xs">Dr. Vikram Seth</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="waiting">Waiting</Badge>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>

              <Pagination
                currentPage={currentPage}
                totalPages={5}
                totalItems={48}
                pageSize={pageSize}
                onPageChange={setCurrentPage}
                onPageSizeChange={setPageSize}
              />
            </CardContent>
          </Card>
        </section>

        {/* INTERACTIVE DIALOG */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent size="md">
            <DialogHeader>
              <DialogTitle>Patient Vitals Entry</DialogTitle>
              <DialogDescription>
                Record baseline triage parameters for consultation.
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-2 gap-4 py-2">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Blood Pressure (mmHg)</label>
                <Input placeholder="120/80" defaultValue="120/80" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Pulse (bpm)</label>
                <Input placeholder="72" defaultValue="72" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">SpO2 (%)</label>
                <Input placeholder="98" defaultValue="99" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Temperature (°F)</label>
                <Input placeholder="98.6" defaultValue="98.4" />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setDialogOpen(false);
                  toast({
                    title: "Vitals Recorded",
                    description: "Triage vitals recorded successfully.",
                    variant: "success",
                  });
                }}
              >
                Save Vitals
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* INTERACTIVE DRAWER */}
        <Drawer open={drawerOpen} onOpenChange={setDrawerOpen} size="md">
          <DrawerHeader
            title="Bed Details: ICU-02"
            description="Intensive Care Unit • Monitoring Telemetry"
            onClose={() => setDrawerOpen(false)}
          />
          <DrawerBody className="text-xs space-y-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Occupant:</span>
                <span className="font-semibold text-slate-900">Ananya Sharma (F, 42)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Patient UID:</span>
                <span className="font-mono text-slate-900">FC01-202609-000098</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Admitted Date:</span>
                <span className="text-slate-900">05-Sep-2026 14:30</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Attending Consultant:</span>
                <span className="text-slate-900">Dr. Priya Raman</span>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-semibold text-slate-900">Care Directives</h4>
              <p className="text-slate-600 leading-relaxed text-xs">
                Continuous ECG monitoring active. Oxygen therapy @ 4L/min via nasal cannula. Fluid intake/output charted hourly.
              </p>
            </div>
          </DrawerBody>
          <DrawerFooter>
            <Button variant="outline" size="sm" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setDrawerOpen(false);
                toast({
                  title: "Bed Transfer Initiated",
                  description: "Transfer requisition sent to nursing station.",
                  variant: "info",
                });
              }}
            >
              Initiate Bed Transfer
            </Button>
          </DrawerFooter>
        </Drawer>

        {/* CONFIRMATION DIALOG */}
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Cancel OPD Token?"
          description="Are you sure you want to cancel Token #CAR-014 for patient Sunita Verma? This action will remove the patient from the doctor queue and cannot be undone."
          confirmLabel="Yes, Cancel Token"
          cancelLabel="Keep Token"
          variant="destructive"
          onConfirm={() => {
            setConfirmOpen(false);
            toast({
              title: "Token Cancelled",
              description: "OPD Token CAR-014 has been cancelled.",
              variant: "destructive",
            });
          }}
        />
      </div>
    </AppShell>
  );
}
