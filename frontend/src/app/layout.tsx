import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { ToastProvider } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toast";
import { SessionTimeoutModal } from "@/components/auth/session-timeout-modal";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ForaCare HIS | Hospital Information & Management System",
  description:
    "Modern, desktop-first hospital information system for patient registration, OPD, IPD, billing, and diagnostic laboratory operations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`} suppressHydrationWarning>
      <body
        className="min-h-screen bg-slate-50 font-sans text-slate-900"
        suppressHydrationWarning
      >
        <QueryProvider>
          <ToastProvider>
            <AuthProvider>
              {children}
              <SessionTimeoutModal />
            </AuthProvider>
            <Toaster />
          </ToastProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
