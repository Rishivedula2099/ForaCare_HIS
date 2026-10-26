import { UserRole } from "@/lib/constants";
import { getRoleMetadata } from "@/types/auth";
import { cn } from "@/lib/utils";

interface RoleBadgeProps {
  role: UserRole;
  className?: string;
}

export function RoleBadge({ role, className }: RoleBadgeProps) {
  const meta = getRoleMetadata(role);

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center text-[10px] font-semibold px-1.5 py-0.5 rounded-full border",
        meta.badgeClassName,
        className
      )}
    >
      {meta.label}
    </span>
  );
}
