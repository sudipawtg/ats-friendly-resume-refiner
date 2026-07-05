"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ChevronDown,
  Download,
  Eye,
  FileDown,
  Loader2,
  Search,
  Sparkles,
  Wand2,
} from "lucide-react";
import clsx from "clsx";
import { Collapsible } from "@/components/Collapsible";
import { PageHeader } from "@/components/PageHeader";
import { StepWizard } from "@/components/StepWizard";
import { PdfPreviewPanel } from "@/features/playground/PdfPreviewPanel";
import { SectionEditorPanel } from "@/features/playground/SectionEditorPanel";
import {
  buildTailorPayload,
  canLoadJob,
  canRunTailoring,
  RECOMMENDED_JOB_CHARS,
  resolveDefaultEditableSections,
  type PlaygroundStep,
} from "@/features/playground/playground.logic";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import { DEFAULT_SECTIONS, INSTRUCTION_PROFILE_LABELS } from "@/constants";
import {
  analyzeCV,
  crawlJob,
  downloadHtmlReport,
  fetchCVProjects,
  fetchInstructionProfiles,
  fetchTailoringPreferences,
  getDownloadUrl,
  getDocxUrl,
  getMasterPdfUrl,
  getPdfUrl,
  previewTailorCV,
  refinePreviewSection,
  refinePrompt,
  tailorCV,
  type AnalyzeResponse,
  type JobDescriptionExtract,
  type SectionChange,
  type TailorPreviewResponse,
  type TailorResponse,
} from "@/lib/api";
import {
  resolveQueuedAnalyzeResponse,
  resolveQueuedPreviewResponse,
  resolveQueuedTailorResponse,
} from "@/lib/jobPolling";

type ActiveAnalysis = AnalyzeResponse | TailorPreviewResponse | TailorResponse;

function isAppliedTailorResponse(value: ActiveAnalysis): value is TailorResponse {
  return value.status === "completed" && "job_id" in value && Boolean(value.job_id);
}

const WIZARD_STEPS = [
  { id: "setup", label: "Setup" },
  { id: "job_loaded", label: "Job" },
  { id: "analyzed", label: "Analyze" },
  { id: "previewed", label: "Preview" },
  { id: "applied", label: "Export" },
] as const;

function InsightList({ items, limit = 3 }: { items: string[]; limit?: number }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? items : items.slice(0, limit);
  const hasMore = items.length > limit;

  const handleToggle = useCallback(() => {
    setExpanded((previous) => !previous);
  }, []);

  return (
    <ul className="space-y-1.5 text-apple-footnote text-apple-label-secondary">
      {visible.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="text-apple-label-tertiary">•</span>
          <span>{item}</span>
        </li>
      ))}
      {hasMore ? (
        <li>
          <button type="button" onClick={handleToggle} className="text-apple-footnote font-medium text-apple-blue">
            {expanded ? "Show less" : `+${items.length - limit} more`}
          </button>
        </li>
      ) : null}
    </ul>
  );
}

export default function PlaygroundPageContent() {
  const searchParams = useSearchParams();
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [manualDescription, setManualDescription] = useState("");
  const [globalInstruction, setGlobalInstruction] = useState("");
  const [profileId, setProfileId] = useState("");
  const [editableSections, setEditableSections] = useState<string[]>([
    "sections/objective.tex",
    "sections/skills.tex",
    "sections/experience.tex",
  ]);
  const [jobDescription, setJobDescription] = useState<JobDescriptionExtract | null>(null);
  const [analysis, setAnalysis] = useState<ActiveAnalysis | null>(null);
  const [previewJobId, setPreviewJobId] = useState<string | null>(null);
  const [appliedJobId, setAppliedJobId] = useState<string | null>(null);
  const [step, setStep] = useState<PlaygroundStep>("setup");
  const [previewMode, setPreviewMode] = useState<"master" | "proposed">("proposed");
  const [error, setError] = useState("");
  const [refinedPreview, setRefinedPreview] = useState("");
  const [pdfCacheKey, setPdfCacheKey] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    const urlParam = searchParams.get("url");
    const cvParam = searchParams.get("cvId");
    if (urlParam) setJobUrl(urlParam);
    if (cvParam) setSelectedProjectId(cvParam);
  }, [searchParams]);

  const { data: projects = [] } = useQuery({ queryKey: ["cvs"], queryFn: fetchCVProjects });
  const { data: profiles = {} } = useQuery({ queryKey: ["profiles"], queryFn: fetchInstructionProfiles });
  const { data: tailoringPreferences } = useQuery({
    queryKey: ["tailoring-preferences"],
    queryFn: fetchTailoringPreferences,
  });

  useEffect(() => {
    if (tailoringPreferences?.global_instruction && !globalInstruction) {
      setGlobalInstruction(tailoringPreferences.global_instruction);
    }
  }, [globalInstruction, tailoringPreferences?.global_instruction]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId);

  useEffect(() => {
    if (!selectedProject) {
      return;
    }
    setEditableSections(resolveDefaultEditableSections(selectedProject.sections));
  }, [selectedProjectId, selectedProject]);

  const formState = useMemo(
    () => ({
      selectedProjectId,
      jobUrl,
      manualDescription,
      globalInstruction,
      profileId,
      editableSections,
    }),
    [selectedProjectId, jobUrl, manualDescription, globalInstruction, profileId, editableSections]
  );

  const crawlMutation = useMutation({
    mutationFn: () => crawlJob(jobUrl.trim(), manualDescription.trim() || undefined),
    onSuccess: (data) => {
      setAnalysis(null);
      setAppliedJobId(null);
      setPreviewJobId(null);
      setPreviewMode("proposed");
      setPdfCacheKey(0);
      setJobDescription(data);
      setStep("job_loaded");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const initialResponse = await analyzeCV(buildTailorPayload(formState));
      return resolveQueuedAnalyzeResponse(initialResponse);
    },
    onSuccess: (data) => {
      setAnalysis(data);
      setJobDescription(data.job_description);
      setStep("analyzed");
      setError("");
      if (data.refined_instructions) setRefinedPreview(data.refined_instructions);
    },
    onError: (err: Error) => setError(err.message),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const initialResponse = await previewTailorCV(buildTailorPayload(formState));
      return resolveQueuedPreviewResponse(initialResponse);
    },
    onSuccess: (data) => {
      setAnalysis(data);
      setPreviewJobId(data.job_id ?? null);
      setStep("previewed");
      setPreviewMode("proposed");
      setPdfCacheKey(Date.now());
      setError("");
      if (data.refined_instructions) setRefinedPreview(data.refined_instructions);
    },
    onError: (err: Error) => setError(err.message),
  });

  const applyMutation = useMutation({
    mutationFn: async () => {
      const initialResponse = await tailorCV(buildTailorPayload(formState));
      return resolveQueuedTailorResponse(initialResponse);
    },
    onSuccess: (data) => {
      setAnalysis(data);
      setAppliedJobId(data.job_id);
      setStep("applied");
      setPreviewMode("proposed");
      setPdfCacheKey(Date.now());
      setError("");
      if (data.refined_instructions) setRefinedPreview(data.refined_instructions);
    },
    onError: (err: Error) => setError(err.message),
  });

  const refineMutation = useMutation({
    mutationFn: () => refinePrompt(globalInstruction, `Job: ${jobUrl || manualDescription.slice(0, 120)}`),
    onSuccess: (data) => {
      setRefinedPreview(data.refined_instruction);
      if (data.refined_instruction) setGlobalInstruction(data.refined_instruction);
    },
  });

  const isBusy =
    crawlMutation.isPending ||
    analyzeMutation.isPending ||
    previewMutation.isPending ||
    applyMutation.isPending;

  const changes: SectionChange[] =
    analysis && "changes" in analysis ? analysis.changes : [];
  const analysisStatus = analysis?.status ?? null;
  const isNeedsManual = analysisStatus === "needs_manual";
  const fitScore = isNeedsManual ? null : (analysis?.fit_analysis.overall_fit ?? null);
  const atsScore = isNeedsManual ? null : (analysis?.ats_analysis.overall_score ?? null);

  const activeTailorJobId = appliedJobId ?? previewJobId;

  const masterPdfUrl = selectedProjectId
    ? `${getMasterPdfUrl(selectedProjectId)}?v=${pdfCacheKey}`
    : null;

  const tailoredPdfUrl =
    activeTailorJobId && selectedProjectId
      ? `${getPdfUrl(selectedProjectId, activeTailorJobId)}?v=${pdfCacheKey}`
      : null;

  const activePdfUrl = previewMode === "master" ? masterPdfUrl : tailoredPdfUrl;

  const wizardSteps = WIZARD_STEPS.map((item) => ({
    id: item.id,
    label: item.label,
    isActive: step === item.id,
    isComplete:
      (item.id === "setup" && Boolean(selectedProjectId)) ||
      (item.id === "job_loaded" && Boolean(jobDescription)) ||
      (item.id === "analyzed" && fitScore !== null) ||
      (item.id === "previewed" && Boolean(previewJobId || changes.length > 0)) ||
      (item.id === "applied" && Boolean(appliedJobId)),
  }));

  const handleToggleSection = useCallback((section: string) => {
    setEditableSections((previous) =>
      previous.includes(section) ? previous.filter((entry) => entry !== section) : [...previous, section]
    );
  }, []);

  const handleLoadJob = useCallback(() => {
    if (!canLoadJob(formState)) {
      setError("Add a job URL or paste the description.");
      return;
    }
    crawlMutation.mutate();
  }, [crawlMutation, formState]);

  const handleAnalyze = useCallback(() => {
    if (!canRunTailoring(formState)) {
      setError("Select a CV and add job details.");
      return;
    }
    analyzeMutation.mutate();
  }, [analyzeMutation, formState]);

  const handlePreview = useCallback(() => {
    if (!canRunTailoring(formState)) {
      setError("Select a CV and add job details.");
      return;
    }
    previewMutation.mutate();
  }, [previewMutation, formState]);

  const handleApply = useCallback(() => {
    if (!canRunTailoring(formState)) {
      setError("Select a CV and add job details.");
      return;
    }
    applyMutation.mutate();
  }, [applyMutation, formState]);

  const handleDownloadZip = useCallback(() => {
    if (!appliedJobId || !selectedProjectId) return;
    window.open(getDownloadUrl(selectedProjectId, appliedJobId), "_blank");
  }, [appliedJobId, selectedProjectId]);

  const handleDownloadReport = useCallback(async () => {
    if (!appliedJobId) return;
    const blob = await downloadHtmlReport({ job_id: appliedJobId });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `resumeforge_report_${appliedJobId.slice(0, 8)}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [appliedJobId]);

  const handleDownloadPdf = useCallback(() => {
    if (!selectedProjectId) return;
    if (previewMode === "master") {
      window.open(`${getMasterPdfUrl(selectedProjectId, true)}&v=${pdfCacheKey}`, "_blank");
      return;
    }
    if (!activeTailorJobId) return;
    window.open(`${getPdfUrl(selectedProjectId, activeTailorJobId, true)}&v=${pdfCacheKey}`, "_blank");
  }, [activeTailorJobId, pdfCacheKey, previewMode, selectedProjectId]);

  const handleDownloadDocx = useCallback(() => {
    if (!activeTailorJobId || !selectedProjectId) return;
    window.open(getDocxUrl(selectedProjectId, activeTailorJobId), "_blank");
  }, [activeTailorJobId, selectedProjectId]);

  const handleRefreshPdfPreview = useCallback(() => {
    setPdfCacheKey(Date.now());
  }, []);

  const handleSectionRefined = useCallback((updatedChanges: SectionChange[]) => {
    setAnalysis((previous) => {
      if (!previous || !("changes" in previous)) {
        return previous;
      }
      return { ...previous, changes: updatedChanges };
    });
  }, []);

  const handleRefineSection = useCallback(
    async (payload: {
      previewJobId: string;
      projectId: string;
      sectionPath: string;
      instruction: string;
      jobUrl: string;
      manualDescription: string;
    }) => {
      const response = await refinePreviewSection({
        previewJobId: payload.previewJobId,
        cvProjectId: payload.projectId,
        sectionPath: payload.sectionPath,
        instruction: payload.instruction,
        jobUrl: payload.jobUrl,
        manualDescription: payload.manualDescription,
      });
      return response.changes;
    },
    []
  );

  const handleSelectMasterPreview = useCallback(() => {
    setPreviewMode("master");
  }, []);

  const handleSelectProposedPreview = useCallback(() => {
    setPreviewMode("proposed");
  }, []);

  const handleToggleAdvanced = useCallback(() => {
    setShowAdvanced((previous) => !previous);
  }, []);

  return (
    <div data-testid="playground-page">
      <PageHeader title="Tailor" subtitle="Match your CV to a job in four steps." />

      <StepWizard steps={wizardSteps} testId="playground-steps" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <section className="glass-card lg:col-span-4" data-testid="playground-job-panel">
          <h2 className="section-title mb-4">1 · Choose job</h2>

          <label className="field-label">Your CV</label>
          <select
            value={selectedProjectId}
            onChange={(event) => setSelectedProjectId(event.target.value)}
            className="glass-input mb-4"
            data-testid="playground-cv-select"
          >
            <option value="">Select CV…</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>

          <label className="field-label">Job link</label>
          <input
            type="url"
            value={jobUrl}
            onChange={(event) => setJobUrl(event.target.value)}
            placeholder="https://…"
            className="glass-input mb-3"
            data-testid="playground-job-url"
          />

          <details className="mb-4">
            <summary className="cursor-pointer text-apple-footnote font-medium text-apple-blue">
              Or paste description
            </summary>
            <textarea
              value={manualDescription}
              onChange={(event) => setManualDescription(event.target.value)}
              rows={3}
              className="glass-input mt-2 resize-none"
              data-testid="playground-manual-jd"
            />
            <p className="mt-1 text-apple-caption text-apple-label-tertiary">
              Paste at least {RECOMMENDED_JOB_CHARS} characters for best results.
            </p>
          </details>

          <button
            type="button"
            onClick={handleLoadJob}
            disabled={!canLoadJob(formState) || crawlMutation.isPending}
            className="glass-button w-full"
            data-testid="playground-load-job-btn"
          >
            {crawlMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            {crawlMutation.isPending ? "Loading…" : "Load job"}
          </button>

          {jobDescription ? (
            <div className="mt-4 space-y-3 border-t border-apple-separator/60 pt-4" data-testid="playground-jd-preview">
              <div>
                <p className="text-apple-headline text-apple-label">{jobDescription.title || "Role"}</p>
                <p className="text-apple-footnote text-apple-label-secondary">
                  {[jobDescription.company, jobDescription.location].filter(Boolean).join(" · ")}
                </p>
              </div>
              {jobDescription.required_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {jobDescription.required_skills.slice(0, 8).map((skill) => (
                    <span key={skill} className="glass-badge-teal">
                      {skill}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {fitScore !== null && atsScore !== null ? (
            <div className="mt-4 flex gap-4 border-t border-apple-separator/60 pt-4" data-testid="playground-insights-panel">
              <div className="flex-1 text-center">
                <div className="score-ring mx-auto mb-1 h-16 w-16 text-apple-title-2" data-testid="playground-fit-score">
                  {fitScore}%
                </div>
                <p className="text-apple-caption text-apple-label-secondary">Fit</p>
              </div>
              <div className="flex-1 text-center">
                <div className="score-ring-secondary mx-auto mb-1 h-16 w-16 text-apple-title-2" data-testid="playground-ats-score">
                  {atsScore}
                </div>
                <p className="text-apple-caption text-apple-label-secondary">ATS</p>
              </div>
            </div>
          ) : null}

          {analysis?.fit_analysis.strong_matches.length ? (
            <div className="mt-4">
              <Collapsible title="Strong matches" count={analysis.fit_analysis.strong_matches.length} defaultOpen>
                <InsightList items={analysis.fit_analysis.strong_matches} />
              </Collapsible>
            </div>
          ) : null}

          {analysis?.ats_analysis.gaps.length ? (
            <div className="mt-2">
              <Collapsible title="Gaps to address" count={analysis.ats_analysis.gaps.length}>
                <InsightList items={analysis.ats_analysis.gaps} />
              </Collapsible>
            </div>
          ) : null}
        </section>

        <section className="glass-card lg:col-span-8" data-testid="playground-preview-panel">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">2 · Review & export</h2>
            {selectedProjectId ? (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleSelectMasterPreview}
                  className={previewMode === "master" ? "glass-button-primary text-sm" : "glass-button text-sm"}
                  data-testid="preview-master-btn"
                >
                  Original
                </button>
                <button
                  type="button"
                  onClick={handleSelectProposedPreview}
                  disabled={!previewJobId && !appliedJobId && changes.length === 0 && !isNeedsManual && step !== "previewed"}
                  className={previewMode === "proposed" ? "glass-button-primary text-sm" : "glass-button text-sm"}
                  data-testid="preview-proposed-btn"
                >
                  Tailored
                </button>
              </div>
            ) : null}
          </div>

          {previewMode === "proposed" && isNeedsManual ? (
            <div
              className="rounded-apple-lg border border-apple-orange/30 bg-orange-500/5 p-6"
              data-testid="playground-needs-manual"
            >
              <p className="text-apple-headline text-apple-label">More job detail needed</p>
              <p className="mt-2 text-apple-footnote text-apple-label-secondary">
                Paste the full job description (title, responsibilities, required skills) and run Preview again.
              </p>
              {analysis?.fit_analysis.potential_gaps.length ? (
                <ul className="mt-3 space-y-1 text-apple-footnote text-apple-label-secondary">
                  {analysis.fit_analysis.potential_gaps.map((gap) => (
                    <li key={gap} className="flex gap-2">
                      <span className="text-apple-label-tertiary">•</span>
                      <span>{gap}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <>
              <PdfPreviewPanel
                pdfUrl={activePdfUrl}
                isLoading={previewMutation.isPending}
                emptyMessage={
                  previewMode === "master"
                    ? "Select a CV to preview the original PDF."
                    : step === "applied"
                      ? "Preparing tailored PDF…"
                      : "Run Preview to generate a tailored PDF for this job."
                }
                title={previewMode === "master" ? "Original CV PDF preview" : "Tailored CV PDF preview"}
              />

              {previewMode === "proposed" && previewJobId && selectedProjectId ? (
                <SectionEditorPanel
                  sections={editableSections}
                  changes={changes}
                  previewJobId={previewJobId}
                  projectId={selectedProjectId}
                  jobUrl={jobUrl}
                  manualDescription={manualDescription}
                  onSectionRefined={handleSectionRefined}
                  onPdfRefresh={handleRefreshPdfPreview}
                  refineSection={handleRefineSection}
                />
              ) : null}
            </>
          )}

          {activeTailorJobId ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={handleDownloadPdf} className="glass-button-primary" data-testid="download-pdf-btn">
                <FileDown size={16} /> PDF
              </button>
              <button type="button" onClick={handleDownloadDocx} className="glass-button" data-testid="download-docx-btn">
                <FileDown size={16} /> DOCX
              </button>
              <button type="button" onClick={handleDownloadZip} className="glass-button">
                <Download size={16} /> ZIP
              </button>
              <button type="button" onClick={handleDownloadReport} className="glass-button" data-testid="download-report-btn">
                <FileDown size={16} /> Report
              </button>
            </div>
          ) : null}
        </section>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={handleToggleAdvanced}
          className="flex items-center gap-2 text-apple-footnote font-medium text-apple-label-secondary"
          data-testid="playground-advanced-toggle"
        >
          <ChevronDown size={16} className={clsx("transition-transform", showAdvanced && "rotate-180")} />
          Advanced options
        </button>

        {showAdvanced ? (
          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="glass-card">
              <h3 className="section-title mb-3">Instructions</h3>
              <label className="field-label">Profile</label>
              <select
                value={profileId}
                onChange={(event) => setProfileId(event.target.value)}
                className="glass-input mb-3"
                data-testid="playground-profile-select"
              >
                <option value="">Default (STAR)</option>
                {Object.keys(profiles).map((key) => (
                  <option key={key} value={key}>
                    {INSTRUCTION_PROFILE_LABELS[key] ?? key}
                  </option>
                ))}
              </select>

              <label className="field-label">Custom instructions</label>
              <textarea
                value={globalInstruction}
                onChange={(event) => setGlobalInstruction(event.target.value)}
                rows={2}
                className="glass-input mb-2 resize-none"
                placeholder="Optional — leave blank for smart defaults"
                data-testid="playground-global-instruction"
              />

              <button
                type="button"
                onClick={() => refineMutation.mutate()}
                disabled={refineMutation.isPending}
                className="glass-button text-sm"
              >
                <Wand2 size={14} />
                {refineMutation.isPending ? "Refining…" : "Refine with AI"}
              </button>

              {refinedPreview ? (
                <p className="mt-2 text-apple-footnote text-apple-label-secondary">{refinedPreview.slice(0, 120)}…</p>
              ) : null}

              <div className="mt-4 border-t border-apple-separator/60 pt-3">
                <p className="field-label">Sections to edit</p>
                <div className="flex flex-wrap gap-2">
                  {(selectedProject?.sections ?? DEFAULT_SECTIONS).map((section) => {
                    const isSelected = editableSections.includes(section);
                    return (
                      <button
                        key={section}
                        type="button"
                        onClick={() => handleToggleSection(section)}
                        className={clsx(
                          "rounded-full px-3 py-1 text-apple-caption font-medium transition-colors",
                          isSelected
                            ? "bg-apple-blue/12 text-apple-blue"
                            : "bg-apple-surface-secondary text-apple-label-secondary"
                        )}
                      >
                        {sectionDisplayName(section)}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="action-bar">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!canRunTailoring(formState) || isBusy}
              className="glass-button"
              data-testid="playground-analyze-btn"
            >
              {analyzeMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              Analyze
            </button>
            <button
              type="button"
              onClick={handlePreview}
              disabled={!canRunTailoring(formState) || isBusy}
              className="glass-button"
              data-testid="playground-preview-btn"
            >
              {previewMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
              Preview
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={!canRunTailoring(formState) || isBusy}
              className="glass-button-primary"
              data-testid="playground-apply-btn"
            >
              {applyMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Apply & export
            </button>
          </div>

          {isBusy ? (
            <p className="text-apple-footnote text-apple-blue" data-testid="playground-loading">
              Working…
            </p>
          ) : null}
        </div>

        {error ? (
          <div className="alert-error mt-3">
            <AlertCircle size={16} className="shrink-0" />
            {error}
          </div>
        ) : null}

        {appliedJobId && analysis && isAppliedTailorResponse(analysis) ? (
          <p className="mt-2 text-apple-footnote text-apple-green">Saved successfully</p>
        ) : null}
      </div>
    </div>
  );
}
