"use client";

import React, { useState } from "react";
import { ShieldCheck, CheckCircle2, AlertCircle, RefreshCw, KeyRound, ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ABHAVerificationStatus } from "@/types/patient";
import { simulateAbdmOtpVerification } from "@/lib/patient-store";

interface AbhaCardProps {
  abhaNumber?: string;
  abhaAddress?: string;
  status: ABHAVerificationStatus;
  mobile: string;
  onAbhaChange: (data: {
    abhaNumber?: string;
    abhaAddress?: string;
    status: ABHAVerificationStatus;
  }) => void;
  onAutoFillDemographics?: (data: {
    gender?: string;
    firstName?: string;
    lastName?: string;
    dob?: string;
    street?: string;
    city?: string;
    state?: string;
    pincode?: string;
  }) => void;
}

export function AbhaCard({
  abhaNumber = "",
  abhaAddress = "",
  status = "UNVERIFIED",
  mobile,
  onAbhaChange,
  onAutoFillDemographics,
}: AbhaCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [step, setStep] = useState<"INPUT" | "OTP" | "SUCCESS">("INPUT");
  const [authInput, setAuthInput] = useState(mobile || "");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);

  // Format 14-digit ABHA number as XX-XXXX-XXXX-XXXX
  const formatAbhaNumber = (val: string) => {
    const digits = val.replace(/\D/g, "").slice(0, 14);
    const parts = [];
    if (digits.length > 0) parts.push(digits.slice(0, 2));
    if (digits.length > 2) parts.push(digits.slice(2, 6));
    if (digits.length > 6) parts.push(digits.slice(6, 10));
    if (digits.length > 10) parts.push(digits.slice(10, 14));
    return parts.join("-");
  };

  const handleAbhaNumberInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatAbhaNumber(e.target.value);
    onAbhaChange({
      abhaNumber: formatted,
      abhaAddress,
      status: formatted.replace(/-/g, "").length === 14 ? status : "UNVERIFIED",
    });
  };

  const handleAbhaAddressInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    onAbhaChange({
      abhaNumber,
      abhaAddress: e.target.value.toLowerCase(),
      status,
    });
  };

  const handleStartVerification = () => {
    setAuthInput(mobile || "");
    setOtp("");
    setStep("INPUT");
    setIsModalOpen(true);
  };

  const handleSendOtp = () => {
    if (!authInput || authInput.trim().length < 10) {
      alert("Please enter a valid 10-digit mobile or 12-digit Aadhaar number");
      return;
    }
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setStep("OTP");
    }, 600);
  };

  const handleVerifyOtp = () => {
    if (!otp || otp.length < 4) {
      alert("Please enter the 6-digit OTP received (demo: 123456)");
      return;
    }
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      const res = simulateAbdmOtpVerification(authInput);
      onAbhaChange({
        abhaNumber: res.abhaNumber,
        abhaAddress: res.abhaAddress,
        status: "VERIFIED",
      });
      setStep("SUCCESS");
    }, 800);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setStep("INPUT");
  };

  return (
    <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-4 space-y-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-teal-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-2xs">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold tracking-tight text-teal-950 uppercase">
                Ayushman Bharat Digital Mission (ABHA / ABDM)
              </h3>
              {status === "VERIFIED" ? (
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 text-[10px] gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Verified M1
                </Badge>
              ) : status === "LINKED" ? (
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300 text-[10px]">
                  Linked
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300 text-[10px]">
                  Unlinked
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-teal-700/80">
              Link patient record to national health identifier (14-digit ABHA ID & Health Address).
            </p>
          </div>
        </div>

        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleStartVerification}
            className="text-xs gap-1.5 bg-white border-teal-300 text-teal-800 hover:bg-teal-50 shadow-2xs w-full sm:w-auto"
          >
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            {status === "VERIFIED" ? "Re-verify ABDM" : "Verify / Fetch via ABDM"}
          </Button>
        </div>
      </div>

      {/* ABHA Input fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-teal-900">
            ABHA Number <span className="font-normal text-slate-500">(14 Digits)</span>
          </label>
          <Input
            placeholder="e.g. 91-1234-5678-9012"
            value={abhaNumber}
            onChange={handleAbhaNumberInput}
            className="bg-white border-teal-200 text-xs font-mono placeholder:font-sans"
            maxLength={17}
          />
        </div>

        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-teal-900">
            ABHA Address / Health Handle
          </label>
          <Input
            placeholder="e.g. patientname@abdm"
            value={abhaAddress}
            onChange={handleAbhaAddressInput}
            className="bg-white border-teal-200 text-xs font-mono placeholder:font-sans"
          />
        </div>
      </div>

      {/* ABDM OTP Verification Dialog */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base text-teal-950">
              <ShieldCheck className="w-5 h-5 text-teal-600" />
              ABDM M1 Identity Verification
            </DialogTitle>
            <DialogDescription className="text-xs">
              Simulate Aadhaar / Mobile OTP verification against National Health Authority (NHA) ABDM Gateway.
            </DialogDescription>
          </DialogHeader>

          {step === "INPUT" && (
            <div className="space-y-3 py-2">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Aadhaar No. / Registered Mobile Number
                </label>
                <Input
                  placeholder="Enter 10-digit mobile or 12-digit Aadhaar"
                  value={authInput}
                  onChange={(e) => setAuthInput(e.target.value)}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-500">
                  An OTP will be dispatched to the beneficiary&apos;s registered phone.
                </p>
              </div>
            </div>
          )}

          {step === "OTP" && (
            <div className="space-y-3 py-2">
              <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800">
                OTP sent to registered number associated with <strong>{authInput}</strong>.
                <span className="block mt-0.5 text-amber-600">(For mock simulation, enter any 6 digits like 123456)</span>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Enter 6-Digit ABDM OTP
                </label>
                <Input
                  placeholder="• • • • • •"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="text-center font-mono tracking-widest text-base"
                  maxLength={6}
                  autoFocus
                />
              </div>
            </div>
          )}

          {step === "SUCCESS" && (
            <div className="py-4 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">ABHA Verified Successfully!</h4>
                <p className="text-xs text-slate-500 mt-1">
                  ABDM KYC token verified. ABHA ID and Health address linked to this profile.
                </p>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-left font-mono text-xs space-y-1">
                <div><span className="text-slate-500">ABHA Number:</span> <span className="font-semibold text-teal-800">{abhaNumber}</span></div>
                <div><span className="text-slate-500">ABHA Address:</span> <span className="font-semibold text-teal-800">{abhaAddress}</span></div>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            {step === "INPUT" && (
              <>
                <Button type="button" variant="outline" size="sm" onClick={handleCloseModal}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSendOtp}
                  disabled={loading}
                  className="bg-primary text-white gap-1"
                >
                  {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Send OTP
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </>
            )}

            {step === "OTP" && (
              <>
                <Button type="button" variant="outline" size="sm" onClick={() => setStep("INPUT")}>
                  Back
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleVerifyOtp}
                  disabled={loading || otp.length < 4}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
                >
                  {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Verify &amp; Link
                </Button>
              </>
            )}

            {step === "SUCCESS" && (
              <Button type="button" size="sm" onClick={handleCloseModal} className="bg-primary text-white w-full">
                Done
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
