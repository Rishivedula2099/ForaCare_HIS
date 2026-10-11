"use client";

import React from "react";
import { useParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { DocumentPreview } from "@/components/documents/document-preview";
import { ErrorState } from "@/components/states/error-state";
import { DOCUMENT_TYPE_INFO, isDocumentType } from "@/lib/documents-api";

/**
 * Shared preview/print screen for every module's documents (P7-F04). Module
 * pages link here with `documentViewHref(type, id)`.
 */
function DocumentViewContent() {
  const params = useParams<{ type: string; id: string }>();
  const type = params.type;

  if (!isDocumentType(type)) {
    return (
      <PageContainer>
        <ErrorState title="Unknown document" description="This document type does not exist." />
      </PageContainer>
    );
  }

  const info = DOCUMENT_TYPE_INFO[type];
  return (
    <PageContainer>
      <PageHeader title={info.title} description={`Preview, print or save this ${info.idKind} document as PDF.`} />
      <DocumentPreview type={type} resourceId={params.id} fileName={`${type.toLowerCase()}-${params.id.slice(0, 8)}`} />
    </PageContainer>
  );
}

export default function DocumentViewPage() {
  return (
    <AppShell>
      <DocumentViewContent />
    </AppShell>
  );
}
