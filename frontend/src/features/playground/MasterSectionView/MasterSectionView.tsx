"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, RotateCcw } from "lucide-react";
import { fetchMasterSections } from "@/lib/api";
import { latexToReadable, sectionDisplayName } from "@/features/playground/latexPreview";

interface MasterSectionViewProps {
  projectId: string;
  sectionPaths: string[];
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Unknown error while loading CV sections.";
}

export function MasterSectionView({ projectId, sectionPaths }: MasterSectionViewProps) {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["master-sections", projectId],
    queryFn: () => fetchMasterSections(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });

  const handleRetryLoad = () => {
    void refetch();
  };

  const orderedSections = useMemo(() => {
    if (!data?.sections.length) {
      return [];
    }

    const contentByPath = new Map(
      data.sections.map((section) => [section.section_path, section.content])
    );
    const displayPaths =
      sectionPaths.length > 0 ? sectionPaths : data.sections.map((section) => section.section_path);

    return displayPaths.map((sectionPath) => ({
      section_path: sectionPath,
      content: contentByPath.get(sectionPath) ?? "",
    }));
  }, [data, sectionPaths]);

  if (!projectId) {
    return (
      <p className="text-apple-subheadline text-apple-label-secondary" data-testid="master-section-empty">
        Select a CV to preview original sections.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center" data-testid="master-section-loading">
        <Loader2 size={24} className="animate-spin text-apple-blue" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-apple-lg border border-apple-pink/30 bg-pink-500/5 p-4" data-testid="master-section-error">
        <p className="flex items-center gap-2 text-apple-subheadline text-apple-pink">
          <AlertCircle size={16} />
          Could not load CV sections.
        </p>
        <p className="mt-2 text-apple-footnote text-apple-label-secondary">{resolveErrorMessage(error)}</p>
        <button
          type="button"
          onClick={handleRetryLoad}
          disabled={isFetching}
          className="glass-button mt-3 text-sm"
          data-testid="master-section-retry-btn"
        >
          {isFetching ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
          Retry
        </button>
      </div>
    );
  }

  if (orderedSections.length === 0) {
    return (
      <p className="text-apple-subheadline text-apple-label-secondary" data-testid="master-section-empty">
        No sections found for this CV.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="master-section-list">
      {orderedSections.map((section) => (
        <div
          key={section.section_path}
          className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/50"
          data-testid={`master-section-${section.section_path}`}
        >
          <div className="border-b border-apple-separator/40 px-4 py-3">
            <span className="glass-badge-blue">{sectionDisplayName(section.section_path)}</span>
          </div>
          <div className="max-h-72 overflow-y-auto px-4 py-3">
            <p className="whitespace-pre-wrap text-apple-footnote leading-relaxed text-apple-label">
              {latexToReadable(section.content) || "Empty section"}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
