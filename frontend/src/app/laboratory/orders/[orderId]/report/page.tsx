"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/constants";
import { getLabReport, getLabReportPdfUrl } from "@/lib/lab-api";
import { ResultFlag } from "@/types/lab";

function flagTone(flag: ResultFlag): string {
  if (flag === "CRITICAL") return "bg-rose-100 text-rose-800 border border-rose-400 font-bold";
  if (flag === "HIGH" || flag === "LOW") return "bg-amber-50 text-amber-700 border border-amber-300";
  if (flag === "NORMAL") return "bg-emerald-50 text-emerald-700 border border-emerald-300";
  return "bg-slate-100 text-slate-500 border border-slate-300";
}

function referenceRangeLabel(row: { normalMin?: number; normalMax?: number }): string {
  if (row.normalMin === undefined || row.normalMax === undefined) return "—";
  return `${row.normalMin} – ${row.normalMax}`;
}

function formatDateTime(value?: string): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

/** Absolute backend URL - `API_BASE_URL` can be a bare path (e.g.
 * `/api/v1` behind nginx) or an absolute origin depending on
 * `NEXT_PUBLIC_API_URL`; the QR needs an absolute URL either way since it's
 * meant to be scanned off a printed page, not opened from this tab. */
function absoluteApiUrl(path: string): string {
  const base = API_BASE_URL.startsWith("http") ? API_BASE_URL : `${window.location.origin}${API_BASE_URL}`;
  return `${base}${path}`;
}

export default function LabReportPage() {
  const { orderId } = useParams<{ orderId: string }>();

  const reportQuery = useQuery({
    queryKey: ["lab-report", orderId],
    queryFn: () => getLabReport(orderId),
    enabled: !!orderId,
  });
  const report = reportQuery.data;

  const verifyUrl =
    report?.reportQrToken && typeof window !== "undefined"
      ? absoluteApiUrl(`/lab/verify-doc?id=${report.labOrderId}&sig=${report.reportQrToken}`)
      : undefined;

  if (reportQuery.isLoading) {
    return <p className="p-8 text-sm text-slate-400">Loading...</p>;
  }
  if (reportQuery.isError || !report) {
    return (
      <p className="p-8 text-sm text-destructive">
        {(reportQuery.error as Error | null)?.message || "Unable to load this report."}
      </p>
    );
  }

  const hasCritical = report.rows.some((row) => row.flag === "CRITICAL");

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="print:hidden flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h1 className="text-sm font-bold">Laboratory Investigation Report</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" asChild>
            <a href={getLabReportPdfUrl(report.labOrderId)} target="_blank" rel="noopener noreferrer">
              Download PDF
            </a>
          </Button>
          <Button size="sm" className="gap-1.5 text-xs" onClick={() => window.print()}>
            <Printer className="w-3.5 h-3.5" />
            Print
          </Button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-8 print:p-6 text-sm">
        <div className="text-center border-b-2 border-slate-900 pb-3 mb-5">
          <h2 className="text-lg font-black">{report.facilityName}</h2>
          <p className="text-xs text-slate-500">Laboratory Investigation Report</p>
          <p className="text-[11px] font-mono text-slate-400">{report.facilityCode}</p>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-2.5 mb-5">
          <div>
            <span className="text-[11px] text-slate-500 block">Patient</span>
            <span className="font-semibold">{report.patientName}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">UID / MRN</span>
            <span className="font-mono font-semibold">
              {report.patientUid} / {report.patientMrn}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Age / Gender</span>
            <span className="font-semibold">
              {report.patientAgeYears}y / {report.patientGender}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Referring Doctor</span>
            <span className="font-semibold">{report.referringDoctorName ?? "—"}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Order Number / Test</span>
            <span className="font-mono font-semibold">{report.orderNumber}</span>
            <span className="block font-semibold">{report.testName}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Accession Number</span>
            <span className="font-mono font-semibold">{report.accessionNumber ?? "—"}</span>
          </div>
          <div>
            <span className="text-[11px] text-slate-500 block">Collected / Ordered</span>
            <span className="font-semibold">{formatDateTime(report.collectedAt)}</span>
            <span className="block text-[11px] text-slate-500">Ordered {formatDateTime(report.orderedAt)}</span>
          </div>
        </div>

        {hasCritical && (
          <div className="mb-4 rounded-md border border-rose-400 bg-rose-50 px-3 py-2 text-xs text-rose-800 font-semibold">
            This report contains one or more CRITICAL values.
          </div>
        )}

        <table className="w-full border-collapse text-xs mb-6">
          <thead>
            <tr className="border-b-2 border-slate-900">
              <th className="text-left py-1.5 pr-2">Parameter</th>
              <th className="text-left py-1.5 pr-2">Value</th>
              <th className="text-left py-1.5 pr-2">Unit</th>
              <th className="text-left py-1.5 pr-2">Reference Range</th>
              <th className="text-left py-1.5">Flag</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => (
              <tr key={row.parameterId} className="border-b border-slate-200">
                <td className="py-1.5 pr-2">
                  {row.parameterName} <span className="text-slate-400 font-mono">({row.parameterCode})</span>
                  {row.isAmended && (
                    <span className="ml-1 text-[10px] text-amber-600 font-semibold" title="Amended since first entered">
                      (amended, v{row.version})
                    </span>
                  )}
                </td>
                <td className="py-1.5 pr-2 font-mono font-semibold">{row.value}</td>
                <td className="py-1.5 pr-2 text-slate-500">{row.unit ?? "—"}</td>
                <td className="py-1.5 pr-2 text-slate-500">{referenceRangeLabel(row)}</td>
                <td className="py-1.5">
                  <span className={`inline-block rounded px-1.5 py-0.5 ${flagTone(row.flag)}`}>{row.flag}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-start justify-between gap-6 mb-8">
          <div className="text-[11px] text-slate-500 space-y-1">
            <div>
              Verified by: <span className="font-semibold text-slate-800">{report.verifiedByName ?? "—"}</span>{" "}
              {report.verifiedAt && <span>({formatDateTime(report.verifiedAt)})</span>}
            </div>
            <div>
              Approved by: <span className="font-semibold text-slate-800">{report.approvedByName ?? "—"}</span>{" "}
              {report.approvedAt && <span>({formatDateTime(report.approvedAt)})</span>}
            </div>
            {report.reportChecksum && (
              <div className="font-mono text-[10px] text-slate-400 break-all">
                Checksum: {report.reportChecksum.slice(0, 24)}…
              </div>
            )}
          </div>
          {verifyUrl && (
            <div className="shrink-0 flex flex-col items-center gap-1">
              <QRCodeSVG value={verifyUrl} size={88} />
              <span className="text-[9px] text-slate-400">Scan to verify</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-8 mt-10 text-xs">
          <div>
            <div className="border-t border-slate-400 pt-1">
              Pathologist Signature {report.approvedByName ? `(${report.approvedByName})` : ""}
            </div>
          </div>
          <div>
            <div className="border-t border-slate-400 pt-1">Lab Stamp</div>
          </div>
        </div>
      </div>
    </div>
  );
}
