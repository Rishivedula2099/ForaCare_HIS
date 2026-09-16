import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DuplicateAlert } from "@/components/patients/duplicate-alert";
import { Patient } from "@/types/patient";

function makePatient(overrides: Partial<Patient> = {}): Patient {
  return {
    id: "pat-1",
    uid: "FC01-202609-000200",
    mrn: "MRN-2026-000200",
    title: "Mr.",
    firstName: "Ramesh",
    lastName: "Sharma",
    fullName: "Ramesh Sharma",
    gender: "MALE",
    dob: "1990-01-01",
    ageYears: 36,
    isMinor: false,
    bloodGroup: "O_POSITIVE",
    mobile: "9876543210",
    address: {
      street: "123 MG Road",
      city: "Bengaluru",
      state: "Karnataka",
      pincode: "560001",
      country: "India",
    },
    photoUrl: "",
    abha: { status: "UNVERIFIED" },
    tenantId: "ten-1",
    facilityId: "fac-1",
    facilityName: "Test Hospital",
    registeredAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    registeredBy: "Someone",
    status: "ACTIVE",
    ...overrides,
  };
}

describe("DuplicateAlert", () => {
  it("renders nothing when duplicates is empty", () => {
    const { container } = render(<DuplicateAlert duplicates={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders each duplicate match with name and UID", () => {
    const duplicates = [
      makePatient({ id: "pat-1", uid: "FC01-202609-000200", fullName: "Ramesh Sharma" }),
      makePatient({ id: "pat-2", uid: "FC01-202609-000201", fullName: "Suresh Sharma" }),
    ];
    render(<DuplicateAlert duplicates={duplicates} />);

    expect(screen.getByText(/2 matches/i)).toBeInTheDocument();
    expect(screen.getByText("Ramesh Sharma")).toBeInTheDocument();
    expect(screen.getByText("Suresh Sharma")).toBeInTheDocument();
    expect(screen.getByText("FC01-202609-000200")).toBeInTheDocument();
    expect(screen.getByText("FC01-202609-000201")).toBeInTheDocument();
  });

  it("calls onDismiss when the close button is clicked", async () => {
    const onDismiss = vi.fn();
    const duplicates = [makePatient()];
    const { default: userEvent } = await import("@testing-library/user-event");
    render(<DuplicateAlert duplicates={duplicates} onDismiss={onDismiss} />);

    const closeButton = screen.getByRole("button");
    await userEvent.setup().click(closeButton);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
