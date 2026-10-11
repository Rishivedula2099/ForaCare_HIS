export type PaperSize = "A4" | "A5" | "A6" | "THERMAL_58" | "THERMAL_80" | "CUSTOM";

export const PAPER_SIZE_LABELS: Record<PaperSize, string> = {
  A4: "A4",
  A5: "A5",
  A6: "A6",
  THERMAL_58: "Thermal 58mm",
  THERMAL_80: "Thermal 80mm",
  CUSTOM: "Custom label",
};

export interface TemplateContent {
  header_note: string | null;
  footer_text: string | null;
  show_facility_contact: boolean;
  signature_labels: string[] | null;
  /** Page size in mm; only for the CUSTOM paper size. */
  custom_width_mm?: number | null;
  custom_height_mm?: number | null;
}

/** Limits enforced by the backend for CUSTOM paper sizes. */
export const CUSTOM_PAPER_MIN_MM = 20;
export const CUSTOM_PAPER_MAX_MM = 300;

export interface TemplateVersion {
  versionNumber: number;
  paperSize: PaperSize;
  content: TemplateContent;
  changeNote: string | null;
  createdAt: string;
}

export interface DocumentTemplate {
  id: string;
  facilityId: string;
  documentType: string;
  name: string;
  isActive: boolean;
  activeVersionNumber: number;
  latestVersionNumber: number;
  paperSize: PaperSize;
  updatedAt: string;
  /** Present on detail responses only. */
  versions?: TemplateVersion[];
}

/** Editable layout fields shared by "create template" and "new version". */
export interface TemplateFormData {
  documentType: string;
  name: string;
  paperSize: PaperSize;
  headerNote: string;
  footerText: string;
  showFacilityContact: boolean;
  /** Comma-separated; empty = keep the document's default signature lines. */
  signatureLabels: string;
  /** Only used when paperSize is CUSTOM (millimetres, as typed). */
  customWidthMm: string;
  customHeightMm: string;
  changeNote: string;
}
