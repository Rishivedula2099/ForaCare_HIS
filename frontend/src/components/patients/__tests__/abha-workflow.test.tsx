import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  getAbdmStatus: vi.fn(),
  getAbhaStatus: vi.fn(),
  requestAbhaOtp: vi.fn(),
  verifyAbha: vi.fn(),
  linkAbha: vi.fn(),
  unlinkAbha: vi.fn(),
  grantAbhaConsent: vi.fn(),
  revokeAbhaConsent: vi.fn(),
}));
vi.mock("@/lib/patient-api", () => api);
const perms = vi.hoisted(() => ({ granted: new Set<string>() }));
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ hasPermission: (code: string) => perms.granted.has(code) }),
}));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));

import { AbhaWorkflow, toIntegrationFailure } from "@/components/patients/abha-workflow";

const apiError = (code: string, message = "boom") => ({
  success: false as const,
  code,
  message,
  details: [],
});

function renderWorkflow() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AbhaWorkflow patientId="p1" mobile="9876543210" />
    </QueryClientProvider>
  );
}

describe("toIntegrationFailure", () => {
  it("classifies timeouts and outages as retryable and rejections as not", () => {
    expect(toIntegrationFailure(apiError("ABDM_TIMEOUT"), "x")).toMatchObject({ kind: "timeout", retryable: true });
    expect(toIntegrationFailure(apiError("ABDM_UNAVAILABLE"), "x")).toMatchObject({
      kind: "unavailable",
      retryable: true,
    });
    expect(toIntegrationFailure(apiError("ABDM_NOT_CONFIGURED"), "x")).toMatchObject({ retryable: false });
    expect(toIntegrationFailure(apiError("ABDM_UNAVAILABLE"), "x").message).not.toContain("boom");
    expect(toIntegrationFailure(apiError("ABDM_INVALID_OTP", "OTP must be 6 digits."), "x")).toEqual({
      kind: "failed",
      title: "Request failed",
      message: "OTP must be 6 digits.",
      retryable: false,
    });
  });
});

describe("safe integration errors (P8-F04)", () => {
  it("never shows raw server text for gateway, credential or internal errors", () => {
    const leaky = "client_secret=abc123 rejected by https://gateway.internal/sessions";
    for (const code of ["ABDM_AUTH_FAILED", "ABDM_REJECTED", "ABDM_NOT_CONFIGURED", "INTERNAL_SERVER_ERROR", "UNKNOWN_ERROR"]) {
      const failure = toIntegrationFailure(apiError(code, leaky), "Something went wrong.");
      expect(failure.message).not.toContain("abc123");
      expect(failure.message).not.toContain("gateway.internal");
    }
    expect(toIntegrationFailure(apiError("INTERNAL_SERVER_ERROR", leaky), "Something went wrong.").message).toBe(
      "Something went wrong."
    );
  });
});

describe("ABHA verify dialog integration states", () => {
  beforeEach(() => {
    perms.granted = new Set(["patients.link_abha", "patients.unlink_abha"]);
    Object.values(api).forEach((fn) => fn.mockReset());
    api.getAbdmStatus.mockResolvedValue({ mode: "mock", connected: true });
    api.getAbhaStatus.mockResolvedValue({ patient_id: "p1", status: "UNVERIFIED", consents: [] });
  });

  it("shows pending, then a timeout with Retry that succeeds on the second attempt", async () => {
    let resolveSecond: (v: { transaction_id: string }) => void = () => {};
    api.requestAbhaOtp
      .mockRejectedValueOnce(apiError("ABDM_TIMEOUT"))
      .mockImplementationOnce(() => new Promise((resolve) => (resolveSecond = resolve)));

    renderWorkflow();
    fireEvent.click(await screen.findByRole("button", { name: /verify abha/i }));
    fireEvent.click(await screen.findByRole("button", { name: /send otp/i }));

    expect(await screen.findByText("ABDM timed out")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findByText(/requesting otp from abdm/i)).toBeInTheDocument();
    resolveSecond({ transaction_id: "t1" });
    expect(await screen.findByPlaceholderText("000000")).toBeInTheDocument();
    expect(api.requestAbhaOtp).toHaveBeenCalledTimes(2);
  });

  it("shows a non-retryable failure without a Retry button, then success", async () => {
    api.requestAbhaOtp.mockResolvedValue({ transaction_id: "t1" });
    api.verifyAbha
      .mockRejectedValueOnce(apiError("ABDM_INVALID_OTP", "OTP is incorrect."))
      .mockResolvedValueOnce({ patient_id: "p1", status: "VERIFIED", consents: [] });

    renderWorkflow();
    fireEvent.click(await screen.findByRole("button", { name: /verify abha/i }));
    fireEvent.click(await screen.findByRole("button", { name: /send otp/i }));
    fireEvent.change(await screen.findByPlaceholderText("000000"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    expect(await screen.findByText("OTP is incorrect.")).toBeInTheDocument();
    // the spent OTP is cleared and the field is masked
    expect(screen.getByPlaceholderText("000000")).toHaveValue("");
    expect(screen.getByPlaceholderText("000000")).toHaveAttribute("type", "password");
    fireEvent.change(screen.getByPlaceholderText("000000"), { target: { value: "123456" } });
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^verify$/i }));
    await waitFor(() => expect(screen.getAllByText("ABHA verified").length).toBeGreaterThan(0));
  });

  it("offers Link but not Unlink to a user holding only patients.link_abha", async () => {
    perms.granted = new Set(["patients.link_abha"]);
    api.getAbhaStatus.mockResolvedValue({
      patient_id: "p1",
      status: "VERIFIED",
      abha_number: "91-1234-5678-9012",
      consents: [],
    });
    renderWorkflow();
    expect(await screen.findByRole("button", { name: /link abha/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /unlink/i })).not.toBeInTheDocument();
  });

  it("shows no ABHA actions to a user with neither permission", async () => {
    perms.granted = new Set();
    api.getAbhaStatus.mockResolvedValue({ patient_id: "p1", status: "VERIFIED", consents: [] });
    renderWorkflow();
    await screen.findByText("VERIFIED");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
