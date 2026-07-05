"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback, useState } from "react";
import { ExternalLink, Inbox, Loader2, Trash2 } from "lucide-react";
import { buildPlaygroundUrl } from "@/features/playground/playground.logic";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import {
  createSavedJob,
  deleteSavedJob,
  fetchSavedJobs,
  type SavedJob,
} from "@/lib/api";

export function JobsPageContent() {
  const queryClient = useQueryClient();
  const [saveUrl, setSaveUrl] = useState("");
  const [saveError, setSaveError] = useState("");

  const { data: savedJobs = [], isLoading, isError, error } = useQuery({
    queryKey: ["saved-jobs"],
    queryFn: fetchSavedJobs,
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      createSavedJob({
        url: saveUrl.trim(),
        title: "",
        company: "",
        location: "",
      }),
    onSuccess: () => {
      setSaveUrl("");
      setSaveError("");
      queryClient.invalidateQueries({ queryKey: ["saved-jobs"] });
    },
    onError: (error: Error) => setSaveError(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (savedJobId: string) => deleteSavedJob(savedJobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved-jobs"] });
    },
  });

  const handleSaveJob = useCallback(() => {
    if (!saveUrl.trim()) {
      setSaveError("Enter a URL.");
      return;
    }
    saveMutation.mutate();
  }, [saveMutation, saveUrl]);

  const handleDeleteJob = useCallback(
    (savedJobId: string) => {
      deleteMutation.mutate(savedJobId);
    },
    [deleteMutation]
  );

  return (
    <div data-testid="jobs-page">
      <PageHeader title="Saved" subtitle="Jobs you want to tailor later." />

      <section className="glass-card mb-4 p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="save-job-url"
            type="url"
            value={saveUrl}
            onChange={(event) => setSaveUrl(event.target.value)}
            placeholder="Paste job URL…"
            className="glass-input flex-1"
            data-testid="save-job-url-input"
          />
          <button
            type="button"
            className="glass-button-primary shrink-0"
            onClick={handleSaveJob}
            disabled={saveMutation.isPending}
            data-testid="save-job-button"
          >
            {saveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Inbox size={16} />}
            Save
          </button>
        </div>
        {saveError ? (
          <p className="mt-2 text-apple-footnote text-apple-red" data-testid="save-job-error">
            {saveError}
          </p>
        ) : null}
      </section>

      {isError ? (
        <div className="glass-card p-6 text-center" data-testid="jobs-error">
          <p className="text-apple-subheadline text-apple-red">
            {error instanceof Error ? error.message : "Could not load jobs."}
          </p>
        </div>
      ) : isLoading ? (
        <div className="glass-card flex h-32 items-center justify-center" data-testid="jobs-loading">
          <Loader2 size={24} className="animate-spin text-apple-label-secondary" />
        </div>
      ) : savedJobs.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Nothing saved"
          description="Save job URLs from Discover or paste one above."
          testId="jobs-empty"
        />
      ) : (
        <div className="space-y-2">
          {savedJobs.map((savedJob: SavedJob) => (
            <div
              key={savedJob.id}
              className="glass-card-interactive flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between"
              data-testid={`saved-job-${savedJob.id}`}
            >
              <div className="min-w-0">
                <p className="truncate text-apple-headline text-apple-label">
                  {savedJob.title || savedJob.company || "Saved job"}
                </p>
                <p className="truncate text-apple-footnote text-apple-label-secondary">
                  {[savedJob.company, savedJob.location].filter(Boolean).join(" · ") || savedJob.url}
                </p>
                {savedJob.fit_score !== null ? (
                  <span className="glass-badge-blue mt-1 inline-block">{savedJob.fit_score}% fit</span>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-2">
                <Link
                  href={buildPlaygroundUrl({ url: savedJob.url })}
                  className="glass-button-primary text-sm"
                  data-testid={`open-playground-${savedJob.id}`}
                >
                  Tailor
                </Link>
                <a
                  href={savedJob.url}
                  target="_blank"
                  rel="noreferrer"
                  className="glass-button p-2"
                  data-testid={`open-url-${savedJob.id}`}
                >
                  <ExternalLink size={16} />
                </a>
                <button
                  type="button"
                  className="glass-button p-2"
                  onClick={() => handleDeleteJob(savedJob.id)}
                  disabled={deleteMutation.isPending}
                  data-testid={`delete-job-${savedJob.id}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
