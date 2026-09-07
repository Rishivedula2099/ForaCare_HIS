import React from "react";
import { Breadcrumbs, type BreadcrumbSegment } from "@/components/layout/breadcrumbs";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Override the auto-generated breadcrumb trail. */
  breadcrumbs?: BreadcrumbSegment[];
  /** Buttons/actions rendered on the right (e.g. "Register Patient"). */
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-2 pb-1">
      <Breadcrumbs items={breadcrumbs} />
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
          {description && (
            <p className="text-xs text-slate-500 mt-0.5">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
      </div>
    </div>
  );
}

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function PageContainer({ children, className }: PageContainerProps) {
  return <div className={`space-y-6 max-w-7xl mx-auto ${className ?? ""}`}>{children}</div>;
}
