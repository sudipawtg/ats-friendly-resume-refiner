"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { CheckCircle, FileText, LayoutTemplate, Loader2, Upload } from "lucide-react";
import Link from "next/link";
import clsx from "clsx";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { TemplateGallery } from "@/features/cvs/TemplateGallery";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import {
  applyCVTemplate,
  createCVFromTemplate,
  fetchCVProjects,
  fetchCVTemplates,
  uploadCV,
  type CVProject,
} from "@/lib/api";

type CVCreateMode = "upload" | "template";

const DEFAULT_TEMPLATE_ID = "classic_blue";

export default function CVsPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<CVCreateMode>("upload");
  const [uploadName, setUploadName] = useState("Master CV");
  const [selectedTemplateId, setSelectedTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [applyTemplateProjectId, setApplyTemplateProjectId] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["cvs"],
    queryFn: fetchCVProjects,
  });

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ["cv-templates"],
    queryFn: fetchCVTemplates,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, name, templateId }: { file: File; name: string; templateId: string }) =>
      uploadCV(file, name, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cvs"] });
      setUploadError("");
    },
    onError: (error: Error) => setUploadError(error.message),
  });

  const createTemplateMutation = useMutation({
    mutationFn: ({ name, templateId }: { name: string; templateId: string }) =>
      createCVFromTemplate(name, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cvs"] });
      setUploadError("");
    },
    onError: (error: Error) => setUploadError(error.message),
  });

  const applyTemplateMutation = useMutation({
    mutationFn: ({ projectId, templateId }: { projectId: string; templateId: string }) =>
      applyCVTemplate(projectId, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cvs"] });
      setApplyTemplateProjectId(null);
      setUploadError("");
    },
    onError: (error: Error) => setUploadError(error.message),
  });

  const handleFileUpload = useCallback(
    (file: File) => {
      const isZip = file.name.toLowerCase().endsWith(".zip");
      const isPdf = file.name.toLowerCase().endsWith(".pdf");
      if (!isZip && !isPdf) {
        setUploadError("Upload a .zip (Overleaf) or .pdf file.");
        return;
      }
      uploadMutation.mutate({ file, name: uploadName, templateId: selectedTemplateId });
    },
    [uploadName, uploadMutation, selectedTemplateId]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragActive(false);
      const file = event.dataTransfer.files[0];
      if (file) handleFileUpload(file);
    },
    [handleFileUpload]
  );

  const handleFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) handleFileUpload(file);
    },
    [handleFileUpload]
  );

  const handleSelectUploadMode = useCallback(() => {
    setMode("upload");
    setUploadError("");
  }, []);

  const handleSelectTemplateMode = useCallback(() => {
    setMode("template");
    setUploadError("");
  }, []);

  const handleSelectTemplate = useCallback((templateId: string) => {
    setSelectedTemplateId(templateId);
  }, []);

  const handleCreateFromTemplate = useCallback(() => {
    createTemplateMutation.mutate({ name: uploadName, templateId: selectedTemplateId });
  }, [createTemplateMutation, uploadName, selectedTemplateId]);

  const handleOpenApplyTemplate = useCallback((projectId: string) => {
    setApplyTemplateProjectId(projectId);
  }, []);

  const handleCloseApplyTemplate = useCallback(() => {
    setApplyTemplateProjectId(null);
  }, []);

  const handleApplyTemplateToProject = useCallback(() => {
    if (!applyTemplateProjectId) return;
    applyTemplateMutation.mutate({
      projectId: applyTemplateProjectId,
      templateId: selectedTemplateId,
    });
  }, [applyTemplateMutation, applyTemplateProjectId, selectedTemplateId]);

  const isCreating = uploadMutation.isPending || createTemplateMutation.isPending;

  return (
    <div data-testid="cvs-page">
      <PageHeader
        title="CVs"
        subtitle="Upload your CV or start from a design, then tailor it for any job."
      />

      <div className="mb-4 flex gap-2">
        <button
          type="button"
          onClick={handleSelectUploadMode}
          className={clsx("glass-button", mode === "upload" && "ring-2 ring-brand-500/40")}
          data-testid="cvs-mode-upload"
        >
          <Upload size={16} />
          Upload CV
        </button>
        <button
          type="button"
          onClick={handleSelectTemplateMode}
          className={clsx("glass-button", mode === "template" && "ring-2 ring-brand-500/40")}
          data-testid="cvs-mode-template"
        >
          <LayoutTemplate size={16} />
          Choose design
        </button>
      </div>

      <div className="glass-card mb-6">
        <label className="field-label">Name</label>
        <input
          type="text"
          value={uploadName}
          onChange={(event) => setUploadName(event.target.value)}
          className="glass-input mb-4 max-w-sm"
          data-testid="cv-name-input"
        />

        <p className="field-label mb-2">CV design</p>
        <TemplateGallery
          templates={templates}
          selectedTemplateId={selectedTemplateId}
          onSelectTemplate={handleSelectTemplate}
          isLoading={templatesLoading}
          disabled={isCreating}
        />

        {mode === "upload" ? (
          <div
            className={`dropzone mt-4 py-10 ${dragActive ? "dropzone-active" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            data-testid="cv-upload-dropzone"
          >
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-apple-blue/10">
              <Upload className="text-apple-blue" size={24} strokeWidth={1.75} />
            </div>
            <p className="mb-1 text-apple-headline text-apple-label">Drop Overleaf ZIP or PDF</p>
            <p className="mb-4 text-apple-footnote text-apple-label-secondary">
              PDF imports use the selected design. ZIP keeps your existing LaTeX project.
            </p>
            <label className="glass-button-primary cursor-pointer">
              Choose file
              <input
                type="file"
                accept=".zip,.pdf"
                className="hidden"
                onChange={handleFileInputChange}
                data-testid="cv-file-input"
              />
            </label>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={handleCreateFromTemplate}
              disabled={isCreating || templates.length === 0}
              className="glass-button-primary"
              data-testid="create-from-template-btn"
            >
              {createTemplateMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <FileText size={16} />
              )}
              Start with this design
            </button>
            <p className="text-apple-footnote text-apple-label-secondary">
              Creates a blank CV you can edit section by section in the playground.
            </p>
          </div>
        )}

        {isCreating ? (
          <p className="mt-3 text-apple-footnote text-apple-blue" data-testid="upload-loading">
            {uploadMutation.isPending ? "Uploading and parsing…" : "Creating CV…"}
          </p>
        ) : null}
        {uploadError ? (
          <p className="alert-error mt-3" data-testid="upload-error">
            {uploadError}
          </p>
        ) : null}
      </div>

      {applyTemplateProjectId ? (
        <div className="glass-card mb-6" data-testid="apply-template-panel">
          <h2 className="section-title mb-2">Change design</h2>
          <p className="mb-4 text-apple-footnote text-apple-label-secondary">
            Pick a new layout — your section content stays the same.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApplyTemplateToProject}
              disabled={applyTemplateMutation.isPending}
              className="glass-button-primary"
              data-testid="apply-template-confirm-btn"
            >
              {applyTemplateMutation.isPending ? "Applying…" : "Apply design"}
            </button>
            <button type="button" onClick={handleCloseApplyTemplate} className="glass-button">
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <h2 className="section-title mb-3">Your projects</h2>
      {isLoading ? <p className="text-apple-subheadline text-apple-label-secondary">Loading…</p> : null}
      {!isLoading && projects.length === 0 ? (
        <EmptyState
          icon={Upload}
          title="No CVs yet"
          description="Upload a CV or pick a design to start tailoring."
          testId="empty-cvs"
        />
      ) : null}
      <div className="space-y-2">
        {projects.map((project: CVProject) => (
          <ProjectCard
            key={project.id}
            project={project}
            onChangeDesign={handleOpenApplyTemplate}
          />
        ))}
      </div>
    </div>
  );
}

interface ProjectCardProps {
  project: CVProject;
  onChangeDesign: (projectId: string) => void;
}

function ProjectCard({ project, onChangeDesign }: ProjectCardProps) {
  const handleChangeDesignClick = useCallback(() => {
    onChangeDesign(project.id);
  }, [onChangeDesign, project.id]);

  const sourceLabel =
    project.source_type === "pdf"
      ? "PDF import"
      : project.source_type === "template"
        ? "From design"
        : "LaTeX ZIP";

  return (
    <div
      className="glass-card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      data-testid={`cv-project-${project.id}`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-apple-headline text-apple-label">{project.name}</h3>
          <CheckCircle className="shrink-0 text-apple-green" size={18} strokeWidth={2} />
        </div>
        <p className="text-apple-footnote text-apple-label-tertiary">
          {new Date(project.created_at).toLocaleDateString()} · {project.sections.length} sections ·{" "}
          {sourceLabel}
          {project.template_id ? ` · ${project.template_id.replace(/_/g, " ")}` : ""}
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {project.sections.map((section) => (
            <span key={section} className="glass-badge-blue">
              {sectionDisplayName(section)}
            </span>
          ))}
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <button type="button" onClick={handleChangeDesignClick} className="glass-button">
          Change design
        </button>
        <Link href={`/edit?cvId=${project.id}`} className="glass-button">
          Edit
        </Link>
        <Link href={`/playground?cvId=${project.id}`} className="glass-button-primary">
          Tailor
        </Link>
      </div>
    </div>
  );
}
