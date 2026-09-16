"use client";

import React from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Users,
  CalendarClock,
  BedDouble,
  Receipt,
  FlaskConical,
  UserPlus,
  Ticket,
  PlusCircle,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

// Mock operational summary for baseline presentation
const STATS = [
  {
    title: "OPD Today",
    value: "148",
    detail: "12 in consultation",
    icon: CalendarClock,
    color: "text-teal-700 bg-teal-50",
  },
  {
    title: "IPD Occupancy",
    value: "42 / 60",
    detail: "70% bed utilization",
    icon: BedDouble,
    color: "text-blue-700 bg-blue-50",
  },
  {
    title: "Pending Lab Orders",
    value: "19",
    detail: "6 awaiting pathologist approval",
    icon: FlaskConical,
    color: "text-amber-700 bg-amber-50",
  },
  {
    title: "Today's Collections",
    value: formatCurrency(184200),
    detail: "Cashier Shift #1 Open",
    icon: Receipt,
    color: "text-emerald-700 bg-emerald-50",
  },
];

const RECENT_QUEUE = [
  {
    token: "CAR-014",
    patientName: "Sunita Verma",
    uid: "FC01-202609-000102",
    doctor: "Dr. Priya Raman",
    department: "Cardiology",
    time: "10:15 AM",
    status: "active",
    statusLabel: "In Consultation",
  },
  {
    token: "CAR-015",
    patientName: "Rajesh Kumar",
    uid: "FC01-202609-000105",
    doctor: "Dr. Priya Raman",
    department: "Cardiology",
    time: "10:30 AM",
    status: "waiting",
    statusLabel: "Waiting",
  },
  {
    token: "GEN-022",
    patientName: "Ananya Sharma",
    uid: "FC01-202609-000098",
    doctor: "Dr. Vikram Seth",
    department: "General Medicine",
    time: "10:20 AM",
    status: "completed",
    statusLabel: "Completed",
  },
  {
    token: "PED-008",
    patientName: "Master Aarav Patel",
    uid: "FC01-202609-000109",
    doctor: "Dr. Meenakshi Iyer",
    department: "Pediatrics",
    time: "10:45 AM",
    status: "waiting",
    statusLabel: "Waiting",
  },
];

const ALERTS = [
  {
    count: 6,
    title: "Lab orders awaiting approval",
    subtitle: "Pathologist review required",
    dotColor: "bg-rose-500",
  },
  {
    count: 3,
    title: "Patients awaiting admission",
    subtitle: "Bed assignment required",
    dotColor: "bg-orange-500",
  },
  {
    count: 8,
    title: "Pending discharge summaries",
    subtitle: "Doctor action required",
    dotColor: "bg-amber-500",
  },
  {
    count: 2,
    title: "Low-stock medical items",
    subtitle: "Pharmacy inventory",
    dotColor: "bg-blue-500",
  },
];

export default function HomePage() {
  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Top Operational Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Hospital Operations Overview
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Live operational telemetry for ForaCare City Hospital (Main Branch)
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Link href="/patients/new">
              <Button size="sm" className="gap-1.5 shadow-xs bg-primary text-white hover:bg-primary/90">
                <UserPlus className="w-3.5 h-3.5" />
                Register Patient
              </Button>
            </Link>
            <Button variant="outline" size="sm" className="gap-1.5 bg-white">
              <Ticket className="w-3.5 h-3.5 text-primary" />
              New OPD Token
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 bg-white">
              <PlusCircle className="w-3.5 h-3.5 text-primary" />
              Admit to IPD
            </Button>
          </div>
        </div>

        {/* Telemetry Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.title} className="shadow-xs border-slate-200">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-slate-500">
                      {stat.title}
                    </p>
                    <div className="text-xl font-bold text-slate-900 tracking-tight">
                      {stat.value}
                    </div>
                    <p className="text-[11px] text-slate-500">{stat.detail}</p>
                  </div>
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${stat.color}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Operational Modules Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* OPD Live Queue Table (2 Columns) */}
          <Card className="lg:col-span-2 shadow-xs border-slate-200">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base">Live OPD Consultation Queue</CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Real-time outpatient tokens for active consulting rooms
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" className="text-xs h-8">
                View Full Queue
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Token</TableHead>
                    <TableHead>Patient Details</TableHead>
                    <TableHead>Physician</TableHead>
                    <TableHead>Time</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {RECENT_QUEUE.map((row) => (
                    <TableRow key={row.token}>
                      <TableCell className="font-mono font-bold text-slate-900">
                        {row.token}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-900 leading-tight">
                          {row.patientName}
                        </div>
                        <div className="text-[11px] font-mono text-slate-400">
                          {row.uid}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs text-slate-800 font-medium">
                          {row.doctor}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {row.department}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {row.time}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant={
                            row.status as "active" | "waiting" | "completed"
                          }
                        >
                          {row.statusLabel}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Quick Tasks & Ward Status (1 Column) */}
          <div className="space-y-4">
            <Card className="shadow-xs border-slate-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Ward Occupancy</CardTitle>
                <CardDescription className="text-xs">
                  Inpatient bed availability by department
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div>
                  <div className="flex justify-between font-medium mb-1 text-slate-700">
                    <span>ICU (Intensive Care)</span>
                    <span className="font-semibold text-rose-600">9 / 10 Beds</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-rose-500 rounded-full w-[90%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between font-medium mb-1 text-slate-700">
                    <span>General Medical Ward</span>
                    <span className="font-semibold text-slate-900">22 / 30 Beds</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-600 rounded-full w-[73%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between font-medium mb-1 text-slate-700">
                    <span>Maternity & Neonatal</span>
                    <span className="font-semibold text-slate-900">11 / 20 Beds</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full w-[55%]" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-xs border-slate-200">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-base">Alerts & Pending Actions</CardTitle>
                  <CardDescription className="text-xs">
                    Items requiring attention
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" className="text-xs h-8">
                  View All
                </Button>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {ALERTS.map((alert) => (
                  <div
                    key={alert.title}
                    className="flex items-start gap-2.5 pb-2.5 border-b border-slate-100 last:border-0 last:pb-0"
                  >
                    <span
                      className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${alert.dotColor}`}
                    />
                    <div className="space-y-0.5 min-w-0 flex-1">
                      <div className="font-medium text-slate-800 leading-tight">
                        <span className="font-semibold text-slate-900">
                          {alert.count}
                        </span>
                        {" — "}
                        {alert.title}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {alert.subtitle}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
