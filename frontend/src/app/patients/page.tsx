"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Users,
  Search,
  UserPlus,
  Filter,
  Ticket,
  PlusCircle,
  Printer,
  Eye,
  SlidersHorizontal,
  X,
  CreditCard,
  Phone,
  ShieldCheck,
  Calendar,
  LayoutGrid,
  List,
  Copy,
  Check,
  ExternalLink,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

import {
  Patient,
  PatientSearchParams,
  GENDERS,
  BLOOD_GROUPS,
  Gender,
  BloodGroup,
} from "@/types/patient";
import { getPatients, searchPatients } from "@/lib/patient-store";

export default function PatientsDirectoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialUidQuery = searchParams.get("uid") || "";

  const [patients, setPatients] = useState<Patient[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialUidQuery);
  const [selectedGender, setSelectedGender] = useState<string>("ALL");
  const [selectedBloodGroup, setSelectedBloodGroup] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<"ALL" | "MINORS" | "ADULTS" | "ABHA_VERIFIED">("ALL");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Detail Modal state
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [copiedUid, setCopiedUid] = useState<string | null>(null);

  // Load patients from store
  const refreshPatients = () => {
    const list = getPatients();
    setPatients(list);
  };

  useEffect(() => {
    refreshPatients();
  }, []);

  // Filtered & Searched patients
  const filteredPatients = useMemo(() => {
    let result = searchPatients({
      query: searchQuery,
      gender: selectedGender !== "ALL" ? (selectedGender as Gender) : undefined,
      bloodGroup: selectedBloodGroup !== "ALL" ? (selectedBloodGroup as BloodGroup) : undefined,
    });

    if (selectedCategory === "MINORS") {
      result = result.filter((p) => p.isMinor);
    } else if (selectedCategory === "ADULTS") {
      result = result.filter((p) => !p.isMinor);
    } else if (selectedCategory === "ABHA_VERIFIED") {
      result = result.filter((p) => p.abha.status === "VERIFIED");
    }

    return result;
  }, [patients, searchQuery, selectedGender, selectedBloodGroup, selectedCategory]);

  const handleCopyUid = (uid: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    navigator.clipboard.writeText(uid);
    setCopiedUid(uid);
    setTimeout(() => setCopiedUid(null), 1800);
  };

  const handleViewPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setIsDetailOpen(true);
  };

  const resetFilters = () => {
    setSearchQuery("");
    setSelectedGender("ALL");
    setSelectedBloodGroup("ALL");
    setSelectedCategory("ALL");
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Page Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              Patient Master Directory (P2-F02)
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Comprehensive patient search across Patient UID, MRN, Name, Phone, Approved Identity IDs, and ABHA.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Link href="/patients/new">
              <Button size="sm" className="gap-1.5 bg-primary text-white shadow-xs hover:bg-primary/90 text-xs">
                <UserPlus className="w-3.5 h-3.5" />
                Register New Patient
              </Button>
            </Link>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <Card className="shadow-xs border-slate-200">
          <CardContent className="p-4 space-y-3">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {/* Universal Search Input */}
              <div className="relative flex-1 w-full">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by Patient UID, MRN, Name, Mobile (+91), Aadhaar, PAN, Passport, or ABHA..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-8 text-xs bg-slate-50/70 border-slate-200 focus:bg-white transition-colors"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* View Toggle & Filter Toggle */}
              <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className={`text-xs gap-1.5 ${
                    showAdvancedFilters || selectedGender !== "ALL" || selectedBloodGroup !== "ALL"
                      ? "bg-teal-50 border-teal-300 text-teal-800"
                      : "bg-white"
                  }`}
                >
                  <SlidersHorizontal className="w-3.5 h-3.5" />
                  Filters
                  {(selectedGender !== "ALL" || selectedBloodGroup !== "ALL" || selectedCategory !== "ALL") && (
                    <span className="w-2 h-2 rounded-full bg-teal-600" />
                  )}
                </Button>

                <div className="flex items-center border border-slate-200 rounded-md overflow-hidden bg-white p-0.5">
                  <button
                    type="button"
                    onClick={() => setViewMode("table")}
                    className={`p-1.5 rounded text-xs transition-colors ${
                      viewMode === "table" ? "bg-slate-100 text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-900"
                    }`}
                    title="Table View"
                  >
                    <List className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("grid")}
                    className={`p-1.5 rounded text-xs transition-colors ${
                      viewMode === "grid" ? "bg-slate-100 text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-900"
                    }`}
                    title="Grid Card View"
                  >
                    <LayoutGrid className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Category Quick Tabs */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              <span className="text-[11px] font-semibold text-slate-500 shrink-0">Quick View:</span>
              <button
                type="button"
                onClick={() => setSelectedCategory("ALL")}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                  selectedCategory === "ALL"
                    ? "bg-primary text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                All Patients ({patients.length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("MINORS")}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                  selectedCategory === "MINORS"
                    ? "bg-primary text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Minors / Children ({patients.filter((p) => p.isMinor).length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("ADULTS")}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                  selectedCategory === "ADULTS"
                    ? "bg-primary text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Adults ({patients.filter((p) => !p.isMinor).length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("ABHA_VERIFIED")}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                  selectedCategory === "ABHA_VERIFIED"
                    ? "bg-primary text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                ABHA Verified ({patients.filter((p) => p.abha.status === "VERIFIED").length})
              </button>
            </div>

            {/* Collapsible Advanced Filters */}
            {showAdvancedFilters && (
              <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-3 animate-in fade-in-50">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Filter by Gender
                  </label>
                  <Select
                    options={[
                      { value: "ALL", label: "All Genders" },
                      ...GENDERS.map((g) => ({ value: g.value, label: g.label })),
                    ]}
                    value={selectedGender}
                    onChange={setSelectedGender}
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Filter by Blood Group
                  </label>
                  <Select
                    options={[
                      { value: "ALL", label: "All Blood Groups" },
                      ...BLOOD_GROUPS.map((b) => ({ value: b.value, label: b.label })),
                    ]}
                    value={selectedBloodGroup}
                    onChange={setSelectedBloodGroup}
                  />
                </div>

                <div className="flex items-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="text-xs text-slate-500 hover:text-slate-800"
                  >
                    Reset All Filters
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Counter Bar */}
        <div className="flex items-center justify-between text-xs text-slate-500 px-1">
          <span>
            Showing <strong>{filteredPatients.length}</strong> of <strong>{patients.length}</strong> registered patients
          </span>
          {searchQuery && (
            <span>
              Searching for: <strong className="text-slate-800 font-mono">&quot;{searchQuery}&quot;</strong>
            </span>
          )}
        </div>

        {/* Content Display: Table or Grid View */}
        {filteredPatients.length === 0 ? (
          <Card className="border-dashed border-slate-300 shadow-none bg-slate-50/50">
            <CardContent className="p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center mx-auto">
                <Search className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-800">No matching patients found</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  No registered patient matches your search criteria. You can create a new registration or try adjusting your search terms.
                </p>
              </div>
              <div className="pt-2">
                <Link href="/patients/new">
                  <Button size="sm" className="gap-1.5 bg-primary text-white text-xs">
                    <UserPlus className="w-3.5 h-3.5" />
                    Register New Patient
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : viewMode === "table" ? (
          /* Table View Mode */
          <Card className="shadow-xs border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead className="w-45">Patient UID &amp; MRN</TableHead>
                    <TableHead>Patient Demographics</TableHead>
                    <TableHead>Contact &amp; Address</TableHead>
                    <TableHead>Identity &amp; ABHA</TableHead>
                    <TableHead>Guardian</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPatients.map((pat) => (
                    <TableRow
                      key={pat.id}
                      className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                      onClick={() => handleViewPatient(pat)}
                    >
                      {/* Patient UID */}
                      <TableCell className="font-mono text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-slate-900">
                          <span>{pat.uid}</span>
                          <button
                            type="button"
                            onClick={(e) => handleCopyUid(pat.uid, e)}
                            className="text-slate-400 hover:text-slate-700 p-0.5 rounded"
                            title="Copy UID"
                          >
                            {copiedUid === pat.uid ? (
                              <Check className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{pat.mrn}</div>
                      </TableCell>

                      {/* Name & Demographics */}
                      <TableCell>
                        <div className="flex items-center gap-2.5">
                          <Avatar className="w-8 h-8 rounded-lg border border-slate-200">
                            <AvatarImage src={pat.photoUrl || undefined} />
                            <AvatarFallback className="text-xs font-bold bg-slate-100 text-slate-700">
                              {pat.firstName[0]}
                              {pat.lastName[0]}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="text-xs font-bold text-slate-900">
                              {pat.fullName}
                            </div>
                            <div className="text-[11px] text-slate-500 flex items-center gap-1.5 mt-0.5">
                              <span>{pat.gender}</span>
                              <span>•</span>
                              <span>{pat.ageYears} yrs</span>
                              <span>•</span>
                              <Badge variant="outline" className="text-[9px] py-0 px-1 font-mono">
                                {pat.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                              </Badge>
                              {pat.isMinor && (
                                <Badge className="text-[9px] py-0 px-1 bg-amber-100 text-amber-800 border-amber-300">
                                  Minor
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </TableCell>

                      {/* Contact & City */}
                      <TableCell className="text-xs">
                        <div className="font-mono font-medium text-slate-800 flex items-center gap-1">
                          <Phone className="w-3 h-3 text-slate-400" />
                          +91 {pat.mobile}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate max-w-50 mt-0.5">
                          {pat.address.city}, {pat.address.state}
                        </div>
                      </TableCell>

                      {/* Identity Reference & ABHA */}
                      <TableCell className="text-xs space-y-1">
                        {pat.primaryIdentity ? (
                          <div className="text-[11px] text-slate-700 font-mono">
                            <span className="text-slate-500 font-sans">{pat.primaryIdentity.type}:</span>{" "}
                            {pat.primaryIdentity.idNumber}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400">No Govt ID</span>
                        )}

                        <div>
                          {pat.abha.status === "VERIFIED" ? (
                            <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-300 gap-1">
                              <ShieldCheck className="w-2.5 h-2.5" />
                              ABHA Verified
                            </Badge>
                          ) : pat.abha.status === "LINKED" ? (
                            <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-300">
                              ABHA Linked
                            </Badge>
                          ) : (
                            <span className="text-[10px] text-slate-400">ABHA Unlinked</span>
                          )}
                        </div>
                      </TableCell>

                      {/* Guardian Details */}
                      <TableCell className="text-xs">
                        {pat.guardian?.name ? (
                          <div>
                            <div className="font-medium text-slate-800">{pat.guardian.name}</div>
                            <div className="text-[10px] text-slate-500">
                              {pat.guardian.relationship} {pat.guardian.phone && `(${pat.guardian.phone})`}
                            </div>
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400">—</span>
                        )}
                      </TableCell>

                      {/* Row Quick Action Buttons */}
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewPatient(pat)}
                            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                            title="View Full Profile"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/opd?patientUid=${encodeURIComponent(pat.uid)}`)}
                            className="h-7 text-xs px-2 gap-1 bg-white border-slate-200 hover:border-teal-500 hover:text-teal-700"
                            title="Book OPD Consultation Token"
                          >
                            <Ticket className="w-3 h-3 text-teal-600" />
                            OPD
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/ipd?patientUid=${encodeURIComponent(pat.uid)}`)}
                            className="h-7 text-xs px-2 gap-1 bg-white border-slate-200 hover:border-blue-500 hover:text-blue-700"
                            title="Admit to IPD"
                          >
                            <PlusCircle className="w-3 h-3 text-blue-600" />
                            IPD
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        ) : (
          /* Grid Card View Mode */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPatients.map((pat) => (
              <Card
                key={pat.id}
                className="shadow-xs border-slate-200 hover:border-teal-500 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
                onClick={() => handleViewPatient(pat)}
              >
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-10 h-10 rounded-xl border border-slate-200 shadow-2xs">
                        <AvatarImage src={pat.photoUrl || undefined} />
                        <AvatarFallback className="font-bold bg-slate-100 text-slate-700 text-xs">
                          {pat.firstName[0]}
                          {pat.lastName[0]}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <CardTitle className="text-sm font-bold text-slate-900 leading-tight">
                          {pat.fullName}
                        </CardTitle>
                        <div className="text-[11px] text-slate-500 flex items-center gap-1.5 mt-0.5">
                          <span>{pat.gender}</span>
                          <span>•</span>
                          <span>{pat.ageYears} yrs</span>
                          <span>•</span>
                          <span className="font-semibold text-slate-700">
                            {pat.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <Badge variant="outline" className="font-mono text-[10px] bg-slate-50">
                        {pat.uid}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="p-4 pt-2 space-y-3 flex-1">
                  <div className="space-y-1 text-xs border-t border-slate-100 pt-2 text-slate-600">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Mobile:</span>
                      <span className="font-mono font-medium text-slate-800">+91 {pat.mobile}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Location:</span>
                      <span className="text-slate-700">{pat.address.city}, {pat.address.state}</span>
                    </div>
                    {pat.primaryIdentity && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">{pat.primaryIdentity.type}:</span>
                        <span className="font-mono text-slate-800">{pat.primaryIdentity.idNumber}</span>
                      </div>
                    )}
                    {pat.guardian?.name && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Guardian:</span>
                        <span className="text-slate-700">
                          {pat.guardian.name} ({pat.guardian.relationship})
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px]">
                    {pat.abha.status === "VERIFIED" ? (
                      <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 gap-1 text-[10px]">
                        <ShieldCheck className="w-3 h-3" />
                        ABHA Verified
                      </Badge>
                    ) : (
                      <span className="text-slate-400">ABHA Unverified</span>
                    )}

                    <span className="text-slate-400 font-mono text-[10px]">
                      MRN: {pat.mrn}
                    </span>
                  </div>
                </CardContent>

                {/* Card Action Footer */}
                <div
                  className="p-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewPatient(pat)}
                    className="text-xs h-7 text-slate-600 hover:text-slate-900"
                  >
                    View Details
                  </Button>

                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/opd?patientUid=${encodeURIComponent(pat.uid)}`)}
                      className="h-7 text-xs px-2 gap-1 bg-white border-slate-200 hover:border-teal-500"
                    >
                      <Ticket className="w-3 h-3 text-teal-600" />
                      OPD
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/ipd?patientUid=${encodeURIComponent(pat.uid)}`)}
                      className="h-7 text-xs px-2 gap-1 bg-white border-slate-200 hover:border-blue-500"
                    >
                      <PlusCircle className="w-3 h-3 text-blue-600" />
                      IPD
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Patient Profile Detail Modal */}
        <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
          <DialogContent className="sm:max-w-2xl">
            {selectedPatient && (
              <>
                <DialogHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-12 h-12 rounded-xl border border-slate-200">
                        <AvatarImage src={selectedPatient.photoUrl || undefined} />
                        <AvatarFallback className="font-bold bg-slate-100 text-slate-800 text-base">
                          {selectedPatient.firstName[0]}
                          {selectedPatient.lastName[0]}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <DialogTitle className="text-base font-bold text-slate-900">
                          {selectedPatient.fullName}
                        </DialogTitle>
                        <DialogDescription className="text-xs text-slate-500">
                          Registered at {selectedPatient.facilityName}
                        </DialogDescription>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="font-mono font-extrabold text-sm text-slate-900 flex items-center gap-1">
                        {selectedPatient.uid}
                        <button
                          type="button"
                          onClick={() => handleCopyUid(selectedPatient.uid)}
                          className="p-1 text-slate-400 hover:text-slate-700"
                          title="Copy UID"
                        >
                          {copiedUid === selectedPatient.uid ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        MRN: {selectedPatient.mrn}
                      </div>
                    </div>
                  </div>
                </DialogHeader>

                <div className="space-y-4 py-2 text-xs">
                  {/* Demographics Summary */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <div>
                      <span className="text-[10px] text-slate-500 block">Gender &amp; Age</span>
                      <span className="font-semibold text-slate-900">
                        {selectedPatient.gender} • {selectedPatient.ageYears} yrs
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Date of Birth</span>
                      <span className="font-semibold text-slate-900 font-mono">
                        {selectedPatient.dob}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Blood Group</span>
                      <span className="font-semibold text-slate-900">
                        {selectedPatient.bloodGroup.replace("_POSITIVE", "+").replace("_NEGATIVE", "-")}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Marital Status</span>
                      <span className="font-semibold text-slate-900">
                        {selectedPatient.maritalStatus || "Unspecified"}
                      </span>
                    </div>
                  </div>

                  {/* Contact & Address */}
                  <div className="space-y-2 border-t border-slate-100 pt-2">
                    <h4 className="text-[11px] font-bold text-slate-700 uppercase">
                      Contact &amp; Address
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
                      <div>
                        <span className="text-slate-400">Mobile: </span>
                        <span className="font-mono font-semibold">+91 {selectedPatient.mobile}</span>
                      </div>
                      {selectedPatient.secondaryPhone && (
                        <div>
                          <span className="text-slate-400">Alternate Phone: </span>
                          <span className="font-mono">+91 {selectedPatient.secondaryPhone}</span>
                        </div>
                      )}
                      {selectedPatient.email && (
                        <div>
                          <span className="text-slate-400">Email: </span>
                          <span>{selectedPatient.email}</span>
                        </div>
                      )}
                      <div className="sm:col-span-2">
                        <span className="text-slate-400">Address: </span>
                        <span>
                          {selectedPatient.address.street}, {selectedPatient.address.city},{" "}
                          {selectedPatient.address.state} - {selectedPatient.address.pincode}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Guardian / Next of Kin */}
                  {selectedPatient.guardian?.name && (
                    <div className="space-y-2 border-t border-slate-100 pt-2">
                      <h4 className="text-[11px] font-bold text-slate-700 uppercase">
                        Guardian / Emergency Contact
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
                        <div>
                          <span className="text-slate-400">Name: </span>
                          <span className="font-semibold">{selectedPatient.guardian.name}</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Relationship: </span>
                          <span>{selectedPatient.guardian.relationship}</span>
                        </div>
                        {selectedPatient.guardian.phone && (
                          <div>
                            <span className="text-slate-400">Phone: </span>
                            <span className="font-mono">+91 {selectedPatient.guardian.phone}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Identity & ABHA */}
                  <div className="space-y-2 border-t border-slate-100 pt-2">
                    <h4 className="text-[11px] font-bold text-slate-700 uppercase">
                      Official Identifiers &amp; ABHA
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
                      <div>
                        <span className="text-slate-400">Primary ID: </span>
                        <span className="font-mono font-semibold">
                          {selectedPatient.primaryIdentity
                            ? `${selectedPatient.primaryIdentity.type}: ${selectedPatient.primaryIdentity.idNumber}`
                            : "None"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">ABHA Status: </span>
                        <Badge
                          variant="outline"
                          className={
                            selectedPatient.abha.status === "VERIFIED"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-300 text-[10px]"
                              : "bg-slate-100 text-slate-600 text-[10px]"
                          }
                        >
                          {selectedPatient.abha.status}
                        </Badge>
                      </div>
                      {selectedPatient.abha.abhaNumber && (
                        <div>
                          <span className="text-slate-400">ABHA Number: </span>
                          <span className="font-mono font-semibold text-teal-800">
                            {selectedPatient.abha.abhaNumber}
                          </span>
                        </div>
                      )}
                      {selectedPatient.abha.abhaAddress && (
                        <div>
                          <span className="text-slate-400">ABHA Address: </span>
                          <span className="font-mono text-teal-800">
                            {selectedPatient.abha.abhaAddress}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Modal Footer Actions */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-2 border-t border-slate-100 pt-3">
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => window.print()}
                      className="text-xs gap-1 w-full sm:w-auto"
                    >
                      <Printer className="w-3.5 h-3.5 text-slate-600" />
                      Print ID Card
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        setIsDetailOpen(false);
                        router.push(`/patients/${selectedPatient.id}`);
                      }}
                      className="text-xs gap-1 bg-primary text-white hover:bg-primary/90 w-full sm:w-auto"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      Open Patient 360
                    </Button>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsDetailOpen(false);
                        router.push(`/opd?patientUid=${encodeURIComponent(selectedPatient.uid)}`);
                      }}
                      className="text-xs gap-1 border-teal-300 text-teal-800 hover:bg-teal-50 w-full sm:w-auto"
                    >
                      <Ticket className="w-3.5 h-3.5 text-teal-600" />
                      Book OPD Token
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsDetailOpen(false);
                        router.push(`/ipd?patientUid=${encodeURIComponent(selectedPatient.uid)}`);
                      }}
                      className="text-xs gap-1 border-blue-300 text-blue-800 hover:bg-blue-50 w-full sm:w-auto"
                    >
                      <PlusCircle className="w-3.5 h-3.5 text-blue-600" />
                      Admit to IPD
                    </Button>
                  </div>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
