import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const { createPatientMock, checkDuplicatesMock, uploadPatientPhotoMock } = vi.hoisted(() => ({
  createPatientMock: vi.fn(),
  checkDuplicatesMock: vi.fn().mockResolvedValue([]),
  uploadPatientPhotoMock: vi.fn(),
}));

vi.mock("@/lib/patient-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/patient-api")>("@/lib/patient-api");
  return {
    ...actual,
    createPatient: createPatientMock,
    checkDuplicates: checkDuplicatesMock,
    uploadPatientPhoto: uploadPatientPhotoMock,
  };
});

const { hasPermissionMock } = vi.hoisted(() => ({
  hasPermissionMock: vi.fn().mockReturnValue(true),
}));
vi.mock("@/providers/auth-provider", () => ({
  useAuthContext: () => ({ hasPermission: hasPermissionMock }),
}));

import PatientRegistrationPage from "@/app/patients/new/page";

const backendPatientResponse = {
  id: "22222222-2222-2222-2222-222222222222",
  uid: "FC01-202609-000300",
  mrn: "MRN-2026-000300",
  title: "Mr.",
  first_name: "Ramesh",
  middle_name: null,
  last_name: "Sharma",
  gender: "MALE",
  dob: "1990-01-01",
  blood_group: "UNKNOWN",
  marital_status: "SINGLE",
  occupation: null,
  preferred_language: "English",
  is_minor: false,
  guardian_name: null,
  guardian_relationship: null,
  guardian_phone: null,
  guardian_address: null,
  status: "ACTIVE",
  created_at: "2026-09-16T00:00:00Z",
  address: {
    address_type: "PERMANENT",
    street: "123 MG Road",
    city: "Bengaluru",
    state: "Karnataka",
    pincode: "560001",
    country: "India",
  },
  contacts: [{ contact_type: "MOBILE", value: "9876543210", is_primary: true }],
  photos: [],
  identifiers: [{ identity_type: "AADHAAR", id_number: "567812349012", is_verified: false }],
  identity_links: [],
};

describe("PatientRegistrationPage", () => {
  beforeEach(() => {
    createPatientMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
  });

  it("shows the access-restricted state when the user lacks patients.manage", () => {
    hasPermissionMock.mockReturnValue(false);
    render(<PatientRegistrationPage />);
    expect(screen.getByText(/access restricted/i)).toBeInTheDocument();
    expect(screen.queryByText(/complete registration/i)).not.toBeInTheDocument();
  });

  it("calls createPatient with the mapped payload on submit", async () => {
    createPatientMock.mockResolvedValue(backendPatientResponse);
    render(<PatientRegistrationPage />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Ramesh"), { target: { value: "Ramesh" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. Sharma"), { target: { value: "Sharma" } });

    const dobInput = document.querySelector('input[type="date"]') as HTMLInputElement;
    fireEvent.change(dobInput, { target: { value: "1990-01-01" } });

    fireEvent.change(screen.getByPlaceholderText("98765 43210"), { target: { value: "9876543210" } });
    fireEvent.change(
      screen.getByPlaceholderText("e.g. Flat 301, Lakeview Residency, 5th Cross Road"),
      { target: { value: "123 MG Road" } }
    );
    fireEvent.change(screen.getByPlaceholderText("560001"), { target: { value: "560001" } });
    fireEvent.change(screen.getByPlaceholderText("12-digit Aadhaar Number"), {
      target: { value: "567812349012" },
    });

    fireEvent.click(screen.getByRole("button", { name: /complete registration/i }));

    await waitFor(() => {
      expect(createPatientMock).toHaveBeenCalledTimes(1);
    });

    const payload = createPatientMock.mock.calls[0][0];
    expect(payload.first_name).toBe("Ramesh");
    expect(payload.last_name).toBe("Sharma");
    expect(payload.address.street).toBe("123 MG Road");
    expect(payload.contacts).toEqual(
      expect.arrayContaining([{ contact_type: "MOBILE", value: "9876543210", is_primary: true }])
    );

    await waitFor(() => {
      expect(screen.getByText(/patient registered successfully/i)).toBeInTheDocument();
    });
  });
});
