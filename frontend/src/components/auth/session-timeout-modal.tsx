"use client";

import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useAuth } from "@/hooks/use-auth";
import { useAuthContext } from "@/providers/auth-provider";

/**
 * Warns a signed-in user 60 seconds before their session is auto-terminated
 * for inactivity - protects shared hospital workstations (nursing stations,
 * OPD rooms, billing counters) from unattended, authenticated sessions.
 */
export function SessionTimeoutModal() {
  const { logout } = useAuth();
  const { sessionTimeout, extendSession } = useAuthContext();

  return (
    <Dialog open={sessionTimeout.isWarningVisible} onOpenChange={(open) => !open && extendSession()}>
      <DialogContent size="sm" hideClose>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-amber-500" />
            <DialogTitle>Session Expiring Soon</DialogTitle>
          </div>
          <DialogDescription>
            For patient data security, you will be signed out due to inactivity in{" "}
            <span className="font-semibold text-slate-700">{sessionTimeout.secondsRemaining}s</span>.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => logout()}>
            Sign Out Now
          </Button>
          <Button onClick={extendSession}>Extend Session</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
