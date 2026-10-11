import React from "react";
import Link from "next/link";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DOCUMENT_TYPE_INFO, DocumentType, documentViewHref } from "@/lib/documents-api";

interface PrintDocumentButtonProps {
  type: DocumentType;
  resourceId: string;
  /** Defaults to the document type's title. */
  label?: string;
  variant?: "outline" | "ghost" | "default";
  className?: string;
}

/**
 * Module-screen entry point to a generated document: opens the shared
 * preview/print page (paper size, print, PDF) in a new tab. Permission is
 * enforced by the backend when the document is generated, so a user without
 * access gets a clear "no permission" message on that page.
 */
export function PrintDocumentButton({
  type,
  resourceId,
  label,
  variant = "outline",
  className,
}: PrintDocumentButtonProps) {
  return (
    <Button variant={variant} size="sm" className={className ?? "gap-1.5 text-xs"} asChild>
      <Link href={documentViewHref(type, resourceId)} target="_blank" rel="noopener noreferrer">
        <FileText className="w-3.5 h-3.5" />
        {label ?? DOCUMENT_TYPE_INFO[type].title}
      </Link>
    </Button>
  );
}
