"use client";

import React, { Fragment } from "react";
import { usePathname } from "next/navigation";
import { Home } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { MAIN_NAV_ITEMS } from "@/lib/constants";

export interface BreadcrumbSegment {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  /** Override the auto-generated trail (e.g. for dynamic patient/record names). */
  items?: BreadcrumbSegment[];
}

function humanizeSegment(segment: string): string {
  return segment
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function autoTrailFromPathname(pathname: string): BreadcrumbSegment[] {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return [];

  let acc = "";
  return segments.map((segment, index) => {
    acc += `/${segment}`;
    const navMatch = MAIN_NAV_ITEMS.find((item) => item.href === acc);
    const label = navMatch?.title || humanizeSegment(segment);
    const isLast = index === segments.length - 1;
    return { label, href: isLast ? undefined : acc };
  });
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  const pathname = usePathname();
  const trail = items ?? autoTrailFromPathname(pathname);

  if (trail.length === 0) return null;

  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink href="/dashboard" className="flex items-center gap-1">
            <Home className="w-3.5 h-3.5" />
            Home
          </BreadcrumbLink>
        </BreadcrumbItem>
        {trail.map((segment, index) => (
          <Fragment key={`${segment.label}-${index}`}>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              {segment.href ? (
                <BreadcrumbLink href={segment.href}>{segment.label}</BreadcrumbLink>
              ) : (
                <BreadcrumbPage>{segment.label}</BreadcrumbPage>
              )}
            </BreadcrumbItem>
          </Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
