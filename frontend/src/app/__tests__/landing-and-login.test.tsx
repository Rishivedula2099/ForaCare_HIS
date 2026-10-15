import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AuthError } from "@/types/auth";

const replace = vi.fn();
const search = vi.hoisted(() => ({ value: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search.value),
}));

const auth = vi.hoisted(() => ({
  state: {
    isAuthenticated: false,
    isLoading: false,
    user: null as null | { permissions: string[] },
    login: vi.fn(),
  },
}));
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => auth.state }));

import LandingPage from "@/app/page";
import LoginPage from "@/app/login/page";

function signedOut() {
  auth.state.isAuthenticated = false;
  auth.state.isLoading = false;
  auth.state.user = null;
}

describe("public landing page", () => {
  beforeEach(signedOut);

  it("offers sign in, onboarding and product information", () => {
    render(<LandingPage />);
    expect(screen.getAllByRole("link", { name: /^sign in$/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /request onboarding/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /explore the product/i })).toHaveAttribute("href", "#modules");
  });

  it("renders no app shell, sidebar or patient data", () => {
    const { container } = render(<LandingPage />);
    expect(container.querySelector("aside")).toBeNull();
    expect(screen.queryByText(/FC01-\d+/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^patients/i })).not.toBeInTheDocument();
  });

  it("points a signed-in visitor to their dashboard instead of sign in", () => {
    auth.state.isAuthenticated = true;
    render(<LandingPage />);
    const links = screen.getAllByRole("link", { name: /open dashboard/i });
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => expect(link).toHaveAttribute("href", "/dashboard"));
    expect(screen.queryByRole("link", { name: /^sign in$/i })).not.toBeInTheDocument();
  });
});

describe("login page", () => {
  beforeEach(() => {
    signedOut();
    search.value = "";
    replace.mockReset();
    auth.state.login.mockReset();
  });

  function submit(username = "dr.who", password = "pw") {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText(/username or email/i), { target: { value: username } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: password } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
  }

  it("has no demo credentials, role switcher or facility picker", () => {
    render(<LoginPage />);
    expect(screen.queryByText(/demo/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/hospital \/ facility/i)).not.toBeInTheDocument();
  });

  it("routes by effective permissions after sign-in", async () => {
    auth.state.login.mockResolvedValue({ permissions: ["lab.view"] });
    submit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("returns to a permitted deep link", async () => {
    search.value = "redirect=/laboratory";
    auth.state.login.mockResolvedValue({ permissions: ["lab.view"] });
    submit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/laboratory"));
  });

  it("sends a user with no module access to the restricted page", async () => {
    auth.state.login.mockResolvedValue({ permissions: [] });
    submit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/forbidden"));
  });

  it("shows the invalid-credentials state without navigating", async () => {
    auth.state.login.mockRejectedValue(new AuthError("Invalid username or password.", "INVALID_CREDENTIALS"));
    submit();
    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows a distinct disabled-account state", async () => {
    auth.state.login.mockRejectedValue(new AuthError("x", "ACCOUNT_DISABLED"));
    submit();
    expect(await screen.findByText(/account disabled/i)).toBeInTheDocument();
  });

  it("shows the no-facility state", async () => {
    auth.state.login.mockRejectedValue(new AuthError("x", "NO_FACILITY_ACCESS"));
    submit();
    expect(await screen.findByText(/no facility access/i)).toBeInTheDocument();
  });

  it("shows the server-unreachable state", async () => {
    auth.state.login.mockRejectedValue(new AuthError("Unable to reach the server.", "NETWORK_ERROR"));
    submit();
    expect(await screen.findByText(/cannot reach the server/i)).toBeInTheDocument();
  });

  it("tells the user their session expired", () => {
    search.value = "reason=expired";
    render(<LoginPage />);
    expect(screen.getByText(/session has expired/i)).toBeInTheDocument();
  });

  it("explains an idle sign-out", () => {
    search.value = "reason=idle";
    render(<LoginPage />);
    expect(screen.getByText(/inactivity/i)).toBeInTheDocument();
  });

  it("disables the form while the existing session is being checked", () => {
    auth.state.isLoading = true;
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /checking session/i })).toBeDisabled();
  });

  it("continues straight to the workspace if already signed in", async () => {
    auth.state.isAuthenticated = true;
    auth.state.user = { permissions: ["patients.view"] };
    render(<LoginPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });
});
