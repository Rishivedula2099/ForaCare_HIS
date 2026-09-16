import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// Render AppShell as a passthrough so we don't have to stand up the full
// sidebar/header/auth-guard chrome for this smoke test.
vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/patient-api", () => ({
  listPatients: vi.fn().mockResolvedValue([]),
  fromBackendListItem: vi.fn(),
}));

const { hasPermissionMock } = vi.hoisted(() => ({ hasPermissionMock: vi.fn() }));
vi.mock("@/providers/auth-provider", () => ({
  useAuthContext: () => ({ hasPermission: hasPermissionMock }),
}));

import PatientsDirectoryPage from "@/app/patients/page";

describe("PatientsDirectoryPage permission gating", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
  });

  it("hides the 'Register New Patient' link when the user lacks patients.manage", async () => {
    hasPermissionMock.mockReturnValue(false);
    render(<PatientsDirectoryPage />);

    await waitFor(() => {
      expect(screen.queryByRole("link", { name: /register new patient/i })).not.toBeInTheDocument();
    });
    // A disabled button placeholder should still be visible instead.
    expect(screen.getByRole("button", { name: /register new patient/i })).toBeDisabled();
  });

  it("shows an enabled 'Register New Patient' link when the user has patients.manage", async () => {
    hasPermissionMock.mockReturnValue(true);
    render(<PatientsDirectoryPage />);

    // The empty-results state also renders a "Register New Patient" link
    // when the user can manage patients, so there may be more than one -
    // just assert at least one is present.
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /register new patient/i }).length).toBeGreaterThan(0);
    });
  });
});
