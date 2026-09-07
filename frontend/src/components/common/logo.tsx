import React from "react";
import { cn } from "@/lib/utils";

interface LogoProps {
  variant?: "full" | "icon" | "compact";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Logo({
  variant = "full",
  size = "md",
  className,
}: LogoProps) {
  const iconDimensions = {
    sm: "w-7 h-7",
    md: "w-9 h-9",
    lg: "w-12 h-12",
  }[size];

  const titleSizes = {
    sm: "text-base",
    md: "text-lg",
    lg: "text-2xl",
  }[size];

  const subtitleSizes = {
    sm: "text-[9px]",
    md: "text-[11px]",
    lg: "text-xs",
  }[size];

  return (
    <div className={cn("inline-flex items-center gap-2.5 select-none", className)}>
      {/* Brand Vector Icon */}
      <svg
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn("shrink-0", iconDimensions)}
        aria-hidden="true"
      >
        {/* Medical Cross Base - Teal (#0A858F) */}
        <path
          d="M44 8H76V34H112V66H98C82 66 76 56 76 46V34H44V8Z"
          fill="#0A858F"
        />
        <path
          d="M8 44H44V76H34C24 76 16 70 16 60V44H8Z"
          fill="#0A858F"
        />
        <path
          d="M44 76V112H76V86C76 74 68 64 56 64H44V76Z"
          fill="#0A858F"
        />

        {/* Head / Healing Patient Silhouette Dot */}
        <circle cx="60" cy="38" r="8" fill="#004565" />

        {/* Healing Patient Torso / Flowing Arms - Navy (#004565) */}
        <path
          d="M60 50C48 50 36 68 36 92C44 76 54 66 68 66C82 66 88 80 88 98C88 74 76 50 60 50Z"
          fill="#004565"
        />

        {/* Organic Vitality Leaf (Top Right) - Warm Orange (#E86328 / #FD4532) */}
        <path
          d="M74 30C78 18 92 14 98 22C102 36 86 44 74 30Z"
          fill="#E86328"
        />

        {/* Dynamic Curved Healing Leaf (Center Right) - Medical Teal (#0A858F) */}
        <path
          d="M66 56C82 48 108 52 108 72C88 80 72 70 66 56Z"
          fill="#0A858F"
        />
      </svg>

      {/* Brand Typography */}
      {variant !== "icon" && (
        <div className="flex flex-col leading-tight">
          <div className={cn("font-bold tracking-tight text-[#004565]", titleSizes)}>
            ForaCare <span className="font-semibold text-slate-500">HIS</span>
          </div>
          {variant === "full" && (
            <div className={cn("font-medium text-slate-500 tracking-wide", subtitleSizes)}>
              By <span className="text-[#E86328] font-semibold">ForaSoftware</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
