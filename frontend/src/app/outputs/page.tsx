"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Loader2 } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { fetchBatches, fetchCVProjects, fetchOutputs, getDownloadUrl, getDocxUrl, getPdfUrl } from "@/lib/api";

interface CompletedJobRow {
  id: string;
  cvProjectId: string;
  batchName: string;
  title: string;
  fitScore: number | null;
  source: "batch" | "persisted";
}

function buildCompletedJobs(
  batches: Awaited<ReturnType<typeof fetchBatches>>,
  apiOutputs: Awaited<ReturnType<typeof fetchOutputs>>
): CompletedJobRow[] {
  const batchJobs = batches.flatMap((batch) =>
    (batch.jobs ?? [])
      .filter((job) => job.status === "completed")
      .map((job) => ({
        id: job.id,
        cvProjectId: batch.cv_project_id,
        batchName: batch.name,
        title: job.title || job.company || "Tailored CV",
        fitScore: job.fit_score,
        source: "batch" as const,
      }))
  );

  const persistedOutputs = apiOutputs
    .filter((output) => output.status === "completed" && output.job_type === "tailor")
    .map((output) => ({
      id: output.job_id,
      cvProjectId: output.cv_project_id,
      batchName: "Tailor",
      title: output.url ?? "Tailored CV",
      fitScore: output.fit_score,
      source: "persisted" as const,
    }));

  const merged = new Map<string, CompletedJobRow>();
  for (const job of persistedOutputs) {
    merged.set(`${job.cvProjectId}:${job.id}`, job);
  }
  for (const job of batchJobs) {
    merged.set(`${job.cvProjectId}:${job.id}`, job);
  }
  return Array.from(merged.values());
}

export default function OutputsPage() {
  const {
    data: batches = [],
    isLoading: batchesLoading,
    isError: batchesError,
    error: batchesErrorDetail,
  } = useQuery({ queryKey: ["batches"], queryFn: fetchBatches });
  const {
    data: projects = [],
    isLoading: projectsLoading,
    isError: projectsError,
  } = useQuery({ queryKey: ["cvs"], queryFn: fetchCVProjects });
  const {
    data: apiOutputs = [],
    isLoading: outputsLoading,
    isError: outputsError,
    error: outputsErrorDetail,
  } = useQuery({ queryKey: ["outputs"], queryFn: fetchOutputs });

  const isLoading = batchesLoading || projectsLoading || outputsLoading;
  const hasError = batchesError || projectsError || outputsError;
  const errorMessage =
    (outputsErrorDetail instanceof Error && outputsErrorDetail.message) ||
    (batchesErrorDetail instanceof Error && batchesErrorDetail.message) ||
    "Could not load downloads.";

  const completedJobs = buildCompletedJobs(batches, apiOutputs);

  return (
    <div data-testid="outputs-page">
      <PageHeader title="Downloads" subtitle="Your tailored CVs and reports." />

      {hasError ? (
        <div className="alert-error" data-testid="outputs-fetch-error">
          {errorMessage}
        </div>
      ) : null}

      {isLoading ? (
        <div className="glass-card flex h-32 items-center justify-center" data-testid="outputs-loading">
          <Loader2 size={24} className="animate-spin text-apple-label-secondary" />
        </div>
      ) : hasError ? null : completedJobs.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No downloads yet"
          description="Tailor a CV first — your files will appear here."
        />
      ) : (
        <div className="space-y-2">
          {completedJobs.map((job) => {
            const project = projects.find((item) => item.id === job.cvProjectId);
            return (
              <div
                key={`${job.source}-${job.id}`}
                className="glass-card-interactive flex items-center justify-between py-3.5"
                data-testid={`output-${job.id}`}
              >
                <div className="min-w-0">
                  <p className="truncate text-apple-headline text-apple-label">{job.title}</p>
                  <p className="text-apple-footnote text-apple-label-secondary">
                    {project?.name ?? "CV"} · {job.batchName}
                  </p>
                  {job.fitScore !== null ? (
                    <span className="glass-badge-blue mt-1 inline-block">{job.fitScore}% fit</span>
                  ) : null}
                </div>
                <div className="flex shrink-0 gap-2">
                  <a
                    href={getPdfUrl(job.cvProjectId, job.id, true)}
                    className="glass-button text-sm"
                    data-testid={`pdf-${job.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    PDF
                  </a>
                  <a
                    href={getDocxUrl(job.cvProjectId, job.id)}
                    className="glass-button text-sm"
                    data-testid={`docx-${job.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    DOCX
                  </a>
                  <a
                    href={getDownloadUrl(job.cvProjectId, job.id)}
                    className="glass-button-primary text-sm"
                    data-testid={`download-${job.id}`}
                  >
                    <Download size={14} /> ZIP
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
