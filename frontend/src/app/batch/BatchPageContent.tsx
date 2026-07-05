"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, FileDown, Layers, Upload } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { DEFAULT_SECTIONS } from "@/constants";
import {
  createBatch,
  downloadHtmlReport,
  fetchBatch,
  fetchBatches,
  fetchCVProjects,
  getDownloadUrl,
} from "@/lib/api";

export default function BatchPageContent() {
  const searchParams = useSearchParams();
  const batchIdParam = searchParams.get("id");
  const queryClient = useQueryClient();

  const [batchName, setBatchName] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [jobUrls, setJobUrls] = useState("");
  const [globalInstruction, setGlobalInstruction] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const storedUrls = sessionStorage.getItem("resumeforge_batch_urls");
    if (storedUrls) {
      setJobUrls(storedUrls);
      sessionStorage.removeItem("resumeforge_batch_urls");
    }
  }, []);

  const { data: projects = [] } = useQuery({ queryKey: ["cvs"], queryFn: fetchCVProjects });
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: fetchBatches,
    refetchInterval: 5000,
  });
  const { data: activeBatch } = useQuery({
    queryKey: ["batch", batchIdParam],
    queryFn: () => fetchBatch(batchIdParam!),
    enabled: !!batchIdParam,
    refetchInterval: 3000,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const urls = jobUrls
        .split("\n")
        .map((url) => url.trim())
        .filter(Boolean);
      const uniqueUrls = [...new Set(urls)];
      return createBatch({
        cv_project_id: selectedProjectId,
        name: batchName || `Campaign ${new Date().toLocaleDateString()}`,
        jobs: uniqueUrls.map((url) => ({ url, priority: 0 })),
        global_instruction: globalInstruction,
        editable_sections: DEFAULT_SECTIONS.filter((section) => section !== "sections/education.tex"),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      setJobUrls("");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleCreateBatch = useCallback(() => {
    if (!selectedProjectId) {
      setError("Select a CV.");
      return;
    }
    if (!jobUrls.trim()) {
      setError("Add at least one URL.");
      return;
    }
    createMutation.mutate();
  }, [selectedProjectId, jobUrls, createMutation]);

  const handleDownloadBatchReport = useCallback(async (batchId: string) => {
    const blob = await downloadHtmlReport({ batch_id: batchId });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `resumeforge_batch_${batchId.slice(0, 8)}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, []);

  const displayBatch = activeBatch ?? batches[0];

  return (
    <div data-testid="batch-page">
      <PageHeader title="Campaigns" subtitle="Tailor your CV for many jobs at once." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="glass-card">
          <h2 className="section-title mb-4">New campaign</h2>

          <label className="field-label">Name</label>
          <input
            type="text"
            value={batchName}
            onChange={(event) => setBatchName(event.target.value)}
            className="glass-input mb-3"
            placeholder="Q1 applications"
            data-testid="batch-name-input"
          />

          <label className="field-label">CV</label>
          <select
            value={selectedProjectId}
            onChange={(event) => setSelectedProjectId(event.target.value)}
            className="glass-input mb-3"
            data-testid="batch-cv-select"
          >
            <option value="">Select…</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>

          <label className="field-label">Job URLs (one per line)</label>
          <textarea
            value={jobUrls}
            onChange={(event) => setJobUrls(event.target.value)}
            rows={6}
            className="glass-input mb-3 resize-none font-mono text-apple-callout"
            placeholder="https://…"
            data-testid="batch-urls-input"
          />

          <details className="mb-4">
            <summary className="cursor-pointer text-apple-footnote font-medium text-apple-blue">
              Custom instructions
            </summary>
            <textarea
              value={globalInstruction}
              onChange={(event) => setGlobalInstruction(event.target.value)}
              rows={2}
              className="glass-input mt-2 resize-none"
              placeholder="Optional"
            />
          </details>

          <button
            type="button"
            onClick={handleCreateBatch}
            disabled={createMutation.isPending}
            className="glass-button-primary w-full"
            data-testid="batch-create-btn"
          >
            <Upload size={16} />
            {createMutation.isPending ? "Starting…" : "Launch"}
          </button>

          {error ? (
            <div className="alert-error mt-3">
              <AlertCircle size={16} className="shrink-0" /> {error}
            </div>
          ) : null}
        </div>

        {displayBatch ? (
          <div className="space-y-3">
            <div className="glass-card">
              <h2 className="section-title mb-4 flex items-center gap-2">
                <Layers size={18} className="text-apple-blue" />
                {displayBatch.name}
              </h2>

              <div className="mb-4 grid grid-cols-4 gap-2">
                <StatPill label="Total" value={displayBatch.total_jobs} />
                <StatPill label="Done" value={displayBatch.completed} color="green" />
                <StatPill label="Active" value={displayBatch.processing} color="blue" />
                <StatPill label="Manual" value={displayBatch.needs_manual} color="orange" />
              </div>

              <button
                type="button"
                onClick={() => handleDownloadBatchReport(displayBatch.id)}
                className="glass-button w-full text-sm"
                data-testid="batch-report-btn"
              >
                <FileDown size={14} /> Download report
              </button>
            </div>

            <div className="max-h-[480px] space-y-2 overflow-y-auto">
              {displayBatch.jobs.map((job) => (
                <div
                  key={job.id}
                  className="glass-card flex items-center justify-between py-3"
                  data-testid={`batch-job-${job.id}`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-apple-subheadline font-medium text-apple-label">
                      {job.title || job.company || "Role"}
                    </p>
                    {job.fit_score !== null ? (
                      <span className="glass-badge-blue mt-1 inline-block">{job.fit_score}%</span>
                    ) : null}
                  </div>
                  <div className="ml-3 flex flex-col items-end gap-1">
                    <StatusBadge status={job.status} />
                    {job.status === "completed" ? (
                      <a
                        href={getDownloadUrl(displayBatch.cv_project_id, job.id)}
                        className="text-apple-caption font-medium text-apple-blue hover:underline"
                      >
                        ZIP
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState icon={Layers} title="No campaigns yet" description="Create one to process multiple jobs." />
        )}
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  color = "default",
}: {
  label: string;
  value: number;
  color?: "default" | "green" | "blue" | "orange";
}) {
  const colorClass =
    color === "green"
      ? "text-apple-green"
      : color === "blue"
        ? "text-apple-blue"
        : color === "orange"
          ? "text-apple-orange"
          : "text-apple-label";

  return (
    <div className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary p-2 text-center">
      <p className={`text-apple-headline font-semibold tabular-nums ${colorClass}`}>{value}</p>
      <p className="text-apple-caption text-apple-label-secondary">{label}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: "glass-badge-green",
    failed: "glass-badge-pink",
    needs_manual: "glass-badge-orange",
    pending: "glass-badge-blue",
    crawling: "glass-badge-blue",
    tailoring: "glass-badge-purple",
  };
  return <span className={`${map[status] ?? "glass-badge-blue"} text-apple-caption`}>{status.replace("_", " ")}</span>;
}
