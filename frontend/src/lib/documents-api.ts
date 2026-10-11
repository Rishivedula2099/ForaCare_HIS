import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/api";
import {
  DocumentTemplate,
  PaperSize,
  TemplateContent,
  TemplateFormData,
  TemplateVersion,
} from "@/types/documents";

/** Document types served by the backend document engine (P7-B01). */
export type DocumentType =
  | "LAB_REPORT"
  | "RECEIPT"
  | "INVOICE"
  | "IPD_CONSENT"
  | "IPD_ADMISSION_FORM"
  | "IPD_DISCHARGE_SUMMARY"
  | "OPD_TOKEN"
  | "OPD_PRESCRIPTION"
  | "PATIENT_LABEL";

/**
 * Display title and id kind for each document type. Most documents are keyed
 * by the record the module screen already has; the id kind documents that.
 */
export const DOCUMENT_TYPE_INFO: Record<DocumentType, { title: string; idKind: string }> = {
  LAB_REPORT: { title: "Laboratory Report", idKind: "lab order" },
  RECEIPT: { title: "Payment Receipt", idKind: "receipt" },
  INVOICE: { title: "Invoice", idKind: "invoice" },
  IPD_CONSENT: { title: "Consent Form", idKind: "consent" },
  IPD_ADMISSION_FORM: { title: "Admission Form", idKind: "admission" },
  IPD_DISCHARGE_SUMMARY: { title: "Discharge Summary", idKind: "admission" },
  OPD_TOKEN: { title: "OPD Token", idKind: "encounter" },
  OPD_PRESCRIPTION: { title: "Prescription", idKind: "encounter" },
  PATIENT_LABEL: { title: "Patient Label", idKind: "patient" },
};

export function isDocumentType(value: string): value is DocumentType {
  return value in DOCUMENT_TYPE_INFO;
}

/** In-app route that previews/prints a document (see app/documents/view). */
export function documentViewHref(type: DocumentType, resourceId: string): string {
  return `/documents/view/${type}/${resourceId}`;
}

export interface DocumentTypeInfo {
  code: DocumentType;
  title: string;
  required_permissions: string[];
  supports_templates: boolean;
}

export async function listDocumentTypes(): Promise<DocumentTypeInfo[]> {
  const res = await apiClient.get<DocumentTypeInfo[]>("/documents/types");
  return res.data as DocumentTypeInfo[];
}

/** Error from fetching a document, with a message safe to show the user. */
export class DocumentFetchError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly requestId?: string
  ) {
    super(message);
    this.name = "DocumentFetchError";
  }
}

function describeFailure(error: unknown): DocumentFetchError {
  const apiError = error as Partial<ApiError> | undefined;
  const status = apiError?.status_code;
  const requestId = apiError?.request_id ?? undefined;
  // The error body of a blob response is unreadable by the shared client, so
  // the user-facing message is derived from the status code instead.
  if (status === 403) {
    return new DocumentFetchError("You do not have permission to view this document.", status, requestId);
  }
  if (status === 404) {
    return new DocumentFetchError("This document could not be found.", status, requestId);
  }
  if (status === 503) {
    return new DocumentFetchError("The PDF service is unavailable right now. Please try again shortly.", status, requestId);
  }
  if (status === 400 || status === 409) {
    return new DocumentFetchError("This document is not available yet.", status, requestId);
  }
  return new DocumentFetchError(
    apiError?.message || "The document could not be generated. Please try again.",
    status,
    requestId
  );
}

/** Fetches the generated PDF as a Blob (auth cookie sent by the shared client). */
export async function fetchDocumentPdf(
  type: DocumentType,
  resourceId: string,
  options: { paperSize?: PaperSize; templateVersion?: number; widthMm?: number; heightMm?: number } = {}
): Promise<Blob> {
  try {
    const res = await apiClient
      .getAxiosInstance()
      .get<Blob>(`/documents/${type}/${resourceId}`, {
        responseType: "blob",
        params: {
          paper_size: options.paperSize,
          template_version: options.templateVersion,
          width_mm: options.paperSize === "CUSTOM" ? options.widthMm : undefined,
          height_mm: options.paperSize === "CUSTOM" ? options.heightMm : undefined,
        },
        headers: { Accept: "application/pdf" },
      });
    return res.data;
  } catch (error) {
    throw describeFailure(error);
  }
}

// ---------------------------------------------------------------------------
// Template management (P7-F02 <-> P7-B02)
// ---------------------------------------------------------------------------

interface BackendTemplateVersion {
  version_number: number;
  paper_size: PaperSize;
  content: TemplateContent;
  change_note: string | null;
  created_at: string;
}

interface BackendTemplate {
  id: string;
  facility_id: string;
  document_type: string;
  name: string;
  is_active: boolean;
  active_version_number: number;
  latest_version_number: number;
  paper_size: PaperSize;
  updated_at: string;
  versions?: BackendTemplateVersion[];
}

function fromBackendVersion(v: BackendTemplateVersion): TemplateVersion {
  return {
    versionNumber: v.version_number,
    paperSize: v.paper_size,
    content: v.content,
    changeNote: v.change_note,
    createdAt: v.created_at,
  };
}

function fromBackendTemplate(t: BackendTemplate): DocumentTemplate {
  return {
    id: t.id,
    facilityId: t.facility_id,
    documentType: t.document_type,
    name: t.name,
    isActive: t.is_active,
    activeVersionNumber: t.active_version_number,
    latestVersionNumber: t.latest_version_number,
    paperSize: t.paper_size,
    updatedAt: t.updated_at,
    versions: t.versions?.map(fromBackendVersion),
  };
}

export function toTemplateContent(form: TemplateFormData): TemplateContent {
  const custom = form.paperSize === "CUSTOM";
  const labels = form.signatureLabels
    .split(",")
    .map((label) => label.trim())
    .filter(Boolean);
  return {
    header_note: form.headerNote.trim() || null,
    footer_text: form.footerText.trim() || null,
    show_facility_contact: form.showFacilityContact,
    signature_labels: labels.length > 0 ? labels : null,
    custom_width_mm: custom ? Number(form.customWidthMm) : null,
    custom_height_mm: custom ? Number(form.customHeightMm) : null,
  };
}

export async function listTemplates(): Promise<DocumentTemplate[]> {
  const res = await apiClient.get<BackendTemplate[]>("/documents/templates");
  return (res.data as BackendTemplate[]).map(fromBackendTemplate);
}

export async function getTemplate(id: string): Promise<DocumentTemplate> {
  const res = await apiClient.get<BackendTemplate>(`/documents/templates/${id}`);
  return fromBackendTemplate(res.data as BackendTemplate);
}

export async function createTemplate(form: TemplateFormData): Promise<DocumentTemplate> {
  const res = await apiClient.post<BackendTemplate>("/documents/templates", {
    document_type: form.documentType,
    name: form.name.trim(),
    paper_size: form.paperSize,
    content: toTemplateContent(form),
    change_note: form.changeNote.trim() || null,
  });
  return fromBackendTemplate(res.data as BackendTemplate);
}

export async function createTemplateVersion(id: string, form: TemplateFormData): Promise<DocumentTemplate> {
  const res = await apiClient.post<BackendTemplate>(`/documents/templates/${id}/versions`, {
    paper_size: form.paperSize,
    content: toTemplateContent(form),
    change_note: form.changeNote.trim() || null,
  });
  return fromBackendTemplate(res.data as BackendTemplate);
}

export async function activateTemplateVersion(id: string, versionNumber: number): Promise<DocumentTemplate> {
  const res = await apiClient.post<BackendTemplate>(
    `/documents/templates/${id}/versions/${versionNumber}/activate`
  );
  return fromBackendTemplate(res.data as BackendTemplate);
}

export async function setTemplateActive(id: string, isActive: boolean): Promise<DocumentTemplate> {
  const res = await apiClient.patch<BackendTemplate>(`/documents/templates/${id}`, { is_active: isActive });
  return fromBackendTemplate(res.data as BackendTemplate);
}
