"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FilePlus2, History, Plus } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { ErrorState } from "@/components/states/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  activateTemplateVersion,
  createTemplate,
  createTemplateVersion,
  getTemplate,
  listDocumentTypes,
  listTemplates,
  setTemplateActive,
} from "@/lib/documents-api";
import { ApiError } from "@/types/api";
import {
  CUSTOM_PAPER_MAX_MM,
  CUSTOM_PAPER_MIN_MM,
  DocumentTemplate,
  PAPER_SIZE_LABELS,
  PaperSize,
  TemplateFormData,
} from "@/types/documents";

const EMPTY_FORM: TemplateFormData = {
  documentType: "",
  name: "",
  paperSize: "A4",
  headerNote: "",
  footerText: "",
  showFacilityContact: true,
  signatureLabels: "",
  customWidthMm: "",
  customHeightMm: "",
  changeNote: "",
};

const PAPER_OPTIONS = (Object.keys(PAPER_SIZE_LABELS) as PaperSize[]).map((value) => ({
  value,
  label: PAPER_SIZE_LABELS[value],
}));

const LABEL_CLASS = "text-[11px] font-semibold text-slate-700 block mb-1";

type FormMode = { kind: "create" } | { kind: "version"; template: DocumentTemplate };

function TemplateFormDialog({
  mode,
  onClose,
}: {
  mode: FormMode | null;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = React.useState<TemplateFormData>(EMPTY_FORM);
  const [error, setError] = React.useState<string | null>(null);

  const typesQuery = useQuery({
    queryKey: ["document-types"],
    queryFn: listDocumentTypes,
    enabled: mode?.kind === "create",
  });
  const typeOptions = (typesQuery.data ?? [])
    .filter((type) => type.supports_templates)
    .map((type) => ({ value: type.code, label: type.title }));

  // A new version starts from the template's currently active content.
  const baseTemplate = mode?.kind === "version" ? mode.template : null;
  const baseQuery = useQuery({
    queryKey: ["document-template", baseTemplate?.id],
    queryFn: () => getTemplate(baseTemplate!.id),
    enabled: !!baseTemplate,
  });

  const seededFor = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (!mode) {
      seededFor.current = null;
      return;
    }
    if (mode.kind === "create") {
      if (seededFor.current !== "create") {
        seededFor.current = "create";
        setForm(EMPTY_FORM);
        setError(null);
      }
      return;
    }
    const detail = baseQuery.data;
    if (detail?.versions && seededFor.current !== detail.id) {
      seededFor.current = detail.id;
      const active = detail.versions.find((v) => v.versionNumber === detail.activeVersionNumber);
      setForm({
        documentType: detail.documentType,
        name: detail.name,
        paperSize: active?.paperSize ?? detail.paperSize,
        headerNote: active?.content.header_note ?? "",
        footerText: active?.content.footer_text ?? "",
        showFacilityContact: active?.content.show_facility_contact ?? true,
        signatureLabels: (active?.content.signature_labels ?? []).join(", "),
        customWidthMm: active?.content.custom_width_mm?.toString() ?? "",
        customHeightMm: active?.content.custom_height_mm?.toString() ?? "",
        changeNote: "",
      });
      setError(null);
    }
  }, [mode, baseQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (data: TemplateFormData) =>
      mode?.kind === "version" ? createTemplateVersion(mode.template.id, data) : createTemplate(data),
    onSuccess: (saved) => {
      toast({
        title: mode?.kind === "version" ? `Version ${saved.latestVersionNumber} published` : "Template created",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["document-templates"] });
      queryClient.invalidateQueries({ queryKey: ["document-template", saved.id] });
      onClose();
    },
    onError: (err: ApiError) => setError(err?.message || "Unable to save template."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode?.kind === "create" && (!form.documentType || !form.name.trim())) {
      setError("Document type and name are required.");
      return;
    }
    if (form.paperSize === "CUSTOM") {
      const width = Number(form.customWidthMm);
      const height = Number(form.customHeightMm);
      const valid = (n: number) => n >= CUSTOM_PAPER_MIN_MM && n <= CUSTOM_PAPER_MAX_MM;
      if (!valid(width) || !valid(height)) {
        setError(`Custom width and height must be between ${CUSTOM_PAPER_MIN_MM} and ${CUSTOM_PAPER_MAX_MM} mm.`);
        return;
      }
    }
    saveMutation.mutate(form);
  };

  const isVersion = mode?.kind === "version";
  const loadingBase = isVersion && baseQuery.isLoading;

  return (
    <Dialog open={!!mode} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isVersion ? `New version of ${baseTemplate?.name}` : "Create Template"}
          </DialogTitle>
          <DialogDescription>
            {isVersion
              ? "Saving publishes a new version immediately. Earlier versions are kept and can be re-activated."
              : "Creates version 1 of a template for this facility."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-3">
          {!isVersion && (
            <>
              <div>
                <label className={LABEL_CLASS}>Document type</label>
                <Select
                  options={typeOptions}
                  value={form.documentType}
                  onChange={(value) => setForm((f) => ({ ...f, documentType: value }))}
                  placeholder={typesQuery.isLoading ? "Loading..." : "Select a document type"}
                />
              </div>
              <div>
                <label className={LABEL_CLASS}>Template name</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Standard Receipt"
                  className="text-xs"
                />
              </div>
            </>
          )}

          <div>
            <label className={LABEL_CLASS}>Paper size</label>
            <Select
              options={PAPER_OPTIONS}
              value={form.paperSize}
              onChange={(value) => setForm((f) => ({ ...f, paperSize: value as PaperSize }))}
            />
          </div>
          {form.paperSize === "CUSTOM" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={LABEL_CLASS}>Width (mm)</label>
                <Input
                  type="number"
                  min={CUSTOM_PAPER_MIN_MM}
                  max={CUSTOM_PAPER_MAX_MM}
                  value={form.customWidthMm}
                  onChange={(e) => setForm((f) => ({ ...f, customWidthMm: e.target.value }))}
                  placeholder="e.g. 50"
                  className="text-xs"
                />
              </div>
              <div>
                <label className={LABEL_CLASS}>Height (mm)</label>
                <Input
                  type="number"
                  min={CUSTOM_PAPER_MIN_MM}
                  max={CUSTOM_PAPER_MAX_MM}
                  value={form.customHeightMm}
                  onChange={(e) => setForm((f) => ({ ...f, customHeightMm: e.target.value }))}
                  placeholder="e.g. 25"
                  className="text-xs"
                />
              </div>
            </div>
          )}
          <div>
            <label className={LABEL_CLASS}>Header note</label>
            <Input
              value={form.headerNote}
              onChange={(e) => setForm((f) => ({ ...f, headerNote: e.target.value }))}
              placeholder="e.g. Reg. No. 12345 · GSTIN ..."
              maxLength={200}
              className="text-xs"
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Footer text</label>
            <Input
              value={form.footerText}
              onChange={(e) => setForm((f) => ({ ...f, footerText: e.target.value }))}
              placeholder="e.g. This is a computer-generated document."
              maxLength={300}
              className="text-xs"
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Signature lines (comma-separated, max 4)</label>
            <Input
              value={form.signatureLabels}
              onChange={(e) => setForm((f) => ({ ...f, signatureLabels: e.target.value }))}
              placeholder="Leave blank for the document's defaults"
              className="text-xs"
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={form.showFacilityContact}
              onChange={(e) => setForm((f) => ({ ...f, showFacilityContact: e.target.checked }))}
            />
            Show facility address and phone in the letterhead
          </label>
          <div>
            <label className={LABEL_CLASS}>Change note</label>
            <Input
              value={form.changeNote}
              onChange={(e) => setForm((f) => ({ ...f, changeNote: e.target.value }))}
              placeholder="What changed and why (optional)"
              maxLength={500}
              className="text-xs"
            />
          </div>

          {error && (
            <p className="text-[11px] text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={saveMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={saveMutation.isPending || loadingBase}>
              {saveMutation.isPending ? "Saving..." : isVersion ? "Publish Version" : "Create Template"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function VersionHistoryDialog({
  template,
  canManage,
  onClose,
}: {
  template: DocumentTemplate | null;
  canManage: boolean;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const detailQuery = useQuery({
    queryKey: ["document-template", template?.id],
    queryFn: () => getTemplate(template!.id),
    enabled: !!template,
  });

  const activateMutation = useMutation({
    mutationFn: (versionNumber: number) => activateTemplateVersion(template!.id, versionNumber),
    onSuccess: (saved) => {
      toast({ title: `Version ${saved.activeVersionNumber} is now active`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["document-templates"] });
      queryClient.invalidateQueries({ queryKey: ["document-template", saved.id] });
    },
    onError: (err: ApiError) =>
      toast({ title: err?.message || "Unable to activate version", variant: "destructive" }),
  });

  const detail = detailQuery.data;

  return (
    <Dialog open={!!template} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{template?.name} — version history</DialogTitle>
          <DialogDescription>
            Versions are never edited or deleted, so a document can always be reproduced with the exact
            layout it was generated with.
          </DialogDescription>
        </DialogHeader>

        {detailQuery.isError && (
          <ErrorState description="Unable to load versions." onRetry={() => detailQuery.refetch()} />
        )}
        {detailQuery.isLoading && <p className="text-xs text-slate-400 py-6 text-center">Loading versions...</p>}

        <ul className="space-y-2 max-h-[50vh] overflow-y-auto">
          {detail?.versions?.map((version) => {
            const isActive = version.versionNumber === detail.activeVersionNumber;
            return (
              <li key={version.versionNumber} className="rounded-md border border-slate-200 p-3 text-xs space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">V{version.versionNumber}</span>
                    {isActive && (
                      <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300">
                        Active
                      </Badge>
                    )}
                    <span className="text-slate-500">{PAPER_SIZE_LABELS[version.paperSize]}</span>
                  </div>
                  {canManage && !isActive && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      disabled={activateMutation.isPending}
                      onClick={() => activateMutation.mutate(version.versionNumber)}
                    >
                      Make active
                    </Button>
                  )}
                </div>
                <p className="text-slate-500">
                  {new Date(version.createdAt).toLocaleString()}
                  {version.changeNote ? ` — ${version.changeNote}` : ""}
                </p>
              </li>
            );
          })}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

function TemplatesPageContent() {
  const { hasPermission, facility } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = hasPermission("documents.manage_templates");

  const [formMode, setFormMode] = React.useState<FormMode | null>(null);
  const [historyFor, setHistoryFor] = React.useState<DocumentTemplate | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["document-templates"],
    queryFn: listTemplates,
    enabled: canManage,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => setTemplateActive(id, isActive),
    onSuccess: () => {
      toast({ title: "Template status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["document-templates"] });
    },
    onError: () => toast({ title: "Unable to update template status", variant: "destructive" }),
  });

  const templates = templatesQuery.data ?? [];

  if (!canManage) {
    return (
      <PageContainer>
        <PageHeader title="Document Templates" description="Letterhead, paper size and layout per document type." />
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          You don&apos;t have permission to manage document templates.
        </p>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Document Templates"
        description="Letterhead, paper size and layout per document type. Every change is a new version; older versions stay reproducible."
        actions={
          <Button size="sm" className="gap-1.5 text-xs" onClick={() => setFormMode({ kind: "create" })}>
            <Plus className="w-3.5 h-3.5" />
            Add Template
          </Button>
        }
      />

      <Card className="shadow-xs border-slate-200">
        <CardContent className="p-4">
          {templatesQuery.isError ? (
            <ErrorState description="Unable to load templates." onRetry={() => templatesQuery.refetch()} />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Template</TableHead>
                    <TableHead>Document type</TableHead>
                    <TableHead>Facility</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Paper size</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {templates.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-xs text-slate-400 py-8">
                        {templatesQuery.isLoading
                          ? "Loading templates..."
                          : "No templates yet. Documents use the built-in default layout."}
                      </TableCell>
                    </TableRow>
                  ) : (
                    templates.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell className="text-xs font-semibold text-slate-900">{template.name}</TableCell>
                        <TableCell className="text-xs font-mono text-slate-700">{template.documentType}</TableCell>
                        <TableCell className="text-xs text-slate-600">{facility?.name ?? "—"}</TableCell>
                        <TableCell className="text-xs text-slate-700">
                          V{template.activeVersionNumber}
                          {template.latestVersionNumber !== template.activeVersionNumber && (
                            <span className="text-slate-400"> (latest V{template.latestVersionNumber})</span>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-slate-700">{PAPER_SIZE_LABELS[template.paperSize]}</TableCell>
                        <TableCell>
                          <button
                            type="button"
                            disabled={toggleMutation.isPending}
                            onClick={() => toggleMutation.mutate({ id: template.id, isActive: !template.isActive })}
                            title="Click to toggle status"
                          >
                            <Badge
                              variant="outline"
                              className={
                                template.isActive
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                                  : "bg-slate-100 text-slate-500 border-slate-300"
                              }
                            >
                              {template.isActive ? "Active" : "Inactive"}
                            </Badge>
                          </button>
                        </TableCell>
                        <TableCell className="text-right whitespace-nowrap">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                            title="New version"
                            onClick={() => setFormMode({ kind: "version", template })}
                          >
                            <FilePlus2 className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900"
                            title="Version history"
                            onClick={() => setHistoryFor(template)}
                          >
                            <History className="w-3.5 h-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <TemplateFormDialog mode={formMode} onClose={() => setFormMode(null)} />
      <VersionHistoryDialog template={historyFor} canManage={canManage} onClose={() => setHistoryFor(null)} />
    </PageContainer>
  );
}

export default function DocumentTemplatesPage() {
  return (
    <AppShell>
      <TemplatesPageContent />
    </AppShell>
  );
}
