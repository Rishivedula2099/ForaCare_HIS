import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const api = vi.hoisted(() => ({
  getSetupOptions: vi.fn(),
  checkAvailability: vi.fn(),
  createTenant: vi.fn(),
}));
vi.mock("@/lib/platform-api", () => api);

vi.setConfig({ testTimeout: 20000 }); // each case walks six steps

import { TenantSetupWizard } from "@/components/setup/tenant-setup-wizard";

const OPTIONS = {
  facility_types: [
    { value: "hospital", label: "Hospital" },
    { value: "clinic", label: "Clinic" },
    { value: "medical_centre", label: "Medical centre" },
  ],
  timezones: [{ value: "Asia/Kolkata", label: "India (IST, UTC+05:30)" }],
  currencies: [{ value: "INR", label: "Indian rupee (INR)" }],
  email_delivery_available: false,
  default_timezone: "Asia/Kolkata",
  default_currency: "INR",
};

const RESULT = {
  tenant_id: "t1",
  tenant_code: "GVH",
  tenant_name: "Green Valley Hospital",
  facility_id: "f1",
  facility_code: "GVH-01",
  facility_name: "Green Valley Main",
  facility_type: "hospital",
  administrator_username: "asha.rao",
  administrator_email: "asha@greenvalley.example",
  activation_link: "https://his.example.org/activate-account?token=abc123",
  activation_expires_hours: 72,
  activation_email_sent: false,
};

const type = (label: RegExp | string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
const next = async () => {
  fireEvent.click(screen.getByRole("button", { name: /continue/i }));
};

async function fillToReview() {
  await screen.findByLabelText("Organisation name");
  type("Organisation name", "Green Valley Hospital");
  await next();
  await screen.findByLabelText("Facility name");
  type("Facility name", "Green Valley Main");
  await next();
  await screen.findByLabelText("Phone");
  type("Phone", "+91 98765 43210");
  type("Contact email", "info@greenvalley.example");
  type("Address line 1", "12 Lake Road");
  type("City", "Bengaluru");
  type("State / province", "Karnataka");
  type("Postal / PIN code", "560038");
  await next();
  await screen.findByLabelText("Time zone");
  await next();
  await screen.findByLabelText("Full name");
  type("Full name", "Asha Rao");
  type("Username", "asha.rao");
  type("Email", "asha@greenvalley.example");
  await next();
  await screen.findByText("Review & create", { selector: "h2" });
}

describe("TenantSetupWizard", () => {
  beforeEach(() => {
    Object.values(api).forEach((m) => m.mockReset());
    api.getSetupOptions.mockResolvedValue(OPTIONS);
    api.checkAvailability.mockResolvedValue({ organization_code: true, facility_code: true, username: true, email: true });
  });

  it("shows validation errors and does not advance with required fields empty", async () => {
    render(<TenantSetupWizard />);
    await screen.findByLabelText("Organisation name");
    await next();
    expect(await screen.findByText("Organisation name is required.")).toBeInTheDocument();
    expect(screen.getByText("Organisation code is required.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Organisation" })).toBeInTheDocument();
    expect(api.checkAvailability).not.toHaveBeenCalled();
  });

  it("suggests codes from the names until the operator edits them", async () => {
    render(<TenantSetupWizard />);
    await screen.findByLabelText("Organisation name");
    type("Organisation name", "Green Valley Hospital");
    expect(screen.getByLabelText("Organisation code")).toHaveValue("GVH");
    type("Organisation code", "VALLEY");
    type("Organisation name", "Green Valley Hospital Group");
    expect(screen.getByLabelText("Organisation code")).toHaveValue("VALLEY"); // hand-edited: left alone
  });

  it("will not advance when the code is already taken", async () => {
    api.checkAvailability.mockResolvedValue({ organization_code: false, facility_code: null, username: null, email: null });
    render(<TenantSetupWizard />);
    await screen.findByLabelText("Organisation name");
    type("Organisation name", "Green Valley Hospital");
    await next();
    expect(await screen.findByText("An organisation with this code already exists.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Organisation" })).toBeInTheDocument();
  });

  it("walks through every step, then creates and shows the one-time link once", async () => {
    api.createTenant.mockResolvedValue(RESULT);
    render(<TenantSetupWizard />);
    await fillToReview();
    expect(screen.getByText(/Green Valley Hospital \(GVH\)/)).toBeInTheDocument();
    expect(screen.getByText(/12 Lake Road, Bengaluru, Karnataka 560038/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    expect(await screen.findByText("Green Valley Hospital is set up")).toBeInTheDocument();
    expect(screen.getByLabelText("Activation link")).toHaveValue(RESULT.activation_link);
    expect(screen.getByText(/Shown only once/i)).toBeInTheDocument();
    expect(api.createTenant).toHaveBeenCalledTimes(1);
    const sent = api.createTenant.mock.calls[0][0];
    expect(sent.organization).toEqual({ name: "Green Valley Hospital", code: "GVH" });
    expect(sent.facility).toMatchObject({ facility_type: "hospital", timezone: "Asia/Kolkata", currency: "INR", postal_code: "560038" });
    expect(sent.administrator.username).toBe("asha.rao");
    expect(JSON.stringify(sent)).not.toMatch(/password/i);
  });

  it("sends a single request even if Create is clicked twice quickly", async () => {
    let resolve!: (v: typeof RESULT) => void;
    api.createTenant.mockReturnValue(new Promise((r) => (resolve = r)));
    render(<TenantSetupWizard />);
    await fillToReview();
    const button = screen.getByRole("button", { name: /create hospital/i });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(api.createTenant).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: /creating/i })).toBeDisabled();
    resolve(RESULT);
    await screen.findByText("Green Valley Hospital is set up");
    expect(api.createTenant).toHaveBeenCalledTimes(1);
  });

  it("clears the form after success so nothing can be resubmitted", async () => {
    api.createTenant.mockResolvedValue(RESULT);
    render(<TenantSetupWizard />);
    await fillToReview();
    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    await screen.findByText("Green Valley Hospital is set up");
    expect(screen.queryByRole("button", { name: /create hospital/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /set up another/i }));
    expect(await screen.findByLabelText("Organisation name")).toHaveValue("");
    expect(screen.queryByLabelText("Activation link")).not.toBeInTheDocument();
  });

  it("maps a duplicate response back to the step and field that caused it", async () => {
    api.createTenant.mockRejectedValue({
      code: "DUPLICATE",
      status_code: 409,
      message: "Some of these details are already in use.",
      details: [{ field: "administrator.username", message: "This username is already taken." }],
    });
    render(<TenantSetupWizard />);
    await fillToReview();
    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    expect(await screen.findByText("This username is already taken.")).toBeInTheDocument();
    expect(screen.getByText(/Nothing was created/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hospital administrator" })).toBeInTheDocument();
    expect(screen.queryByText("Green Valley Hospital is set up")).not.toBeInTheDocument();
  });

  it("maps server validation errors (422) onto fields", async () => {
    api.createTenant.mockRejectedValue({
      code: "VALIDATION_ERROR",
      status_code: 422,
      message: "Request validation failed.",
      details: [{ field: "body.facility.postal_code", message: "Enter a valid postal / PIN code." }],
    });
    render(<TenantSetupWizard />);
    await fillToReview();
    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    expect(await screen.findByText("Enter a valid postal / PIN code.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Contact & address" })).toBeInTheDocument();
  });

  it("explains that retrying is safe when the connection drops mid-create", async () => {
    api.createTenant.mockRejectedValue({ code: "NETWORK_ERROR", message: "Network error" });
    render(<TenantSetupWizard />);
    await fillToReview();
    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    expect(await screen.findByText(/safe to press Create again/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create hospital/i })).toBeEnabled();
  });

  it("tells a non-operator that they cannot create hospitals", async () => {
    api.createTenant.mockRejectedValue({ code: "FORBIDDEN", status_code: 403, message: "Only a platform operator can do this." });
    render(<TenantSetupWizard />);
    await fillToReview();
    fireEvent.click(screen.getByRole("button", { name: /create hospital/i }));
    expect(await screen.findByText(/only a platform operator/i)).toBeInTheDocument();
  });

  it("reports an options-loading failure instead of an empty form", async () => {
    api.getSetupOptions.mockRejectedValue({ message: "Only a platform operator can do this." });
    render(<TenantSetupWizard />);
    expect(await screen.findByText(/only a platform operator/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Organisation name")).not.toBeInTheDocument();
  });
});
