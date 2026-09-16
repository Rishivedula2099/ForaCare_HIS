import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const { listPatientsMock } = vi.hoisted(() => ({ listPatientsMock: vi.fn() }));
vi.mock("@/lib/patient-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/patient-api")>("@/lib/patient-api");
  return {
    ...actual,
    listPatients: listPatientsMock,
  };
});

vi.mock("@/providers/auth-provider", () => ({
  useAuthContext: () => ({ hasPermission: () => true }),
}));

import PatientsDirectoryPage from "@/app/patients/page";

describe("PatientsDirectoryPage search", () => {
  it("renders patients returned by the (mocked) patient-api module", async () => {
    listPatientsMock.mockResolvedValue([
      {
        id: "pat-1",
        uid: "FC01-202609-000200",
        mrn: "MRN-2026-000200",
        first_name: "Ramesh",
        middle_name: null,
        last_name: "Sharma",
        gender: "MALE",
        dob: "1990-01-01",
        status: "ACTIVE",
      },
    ]);

    render(<PatientsDirectoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Ramesh Sharma")).toBeInTheDocument();
    });
    expect(screen.getByText("FC01-202609-000200")).toBeInTheDocument();
    expect(listPatientsMock).toHaveBeenCalled();
  });
});
