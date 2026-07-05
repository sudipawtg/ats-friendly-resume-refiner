"use client";

import type { SectionChange } from "@/lib/api";
import { useCallback, useState } from "react";
import { ChevronDown } from "lucide-react";
import clsx from "clsx";
import { latexToReadable, sectionDisplayName } from "@/features/playground/latexPreview";

interface SectionDiffViewProps {
  changes: SectionChange[];
}

function DiffSection({ change }: { change: SectionChange }) {
  const [expanded, setExpanded] = useState(true);

  const handleToggle = useCallback(() => {
    setExpanded((previous) => !previous);
  }, []);

  return (
    <div
      className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/50"
      data-testid={`section-diff-${change.id}`}
    >
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="glass-badge-blue">{sectionDisplayName(change.section_path)}</span>
        <ChevronDown
          size={16}
          className={clsx("shrink-0 text-apple-label-tertiary transition-transform", expanded && "rotate-180")}
        />
      </button>

      {expanded ? (
        <div className="border-t border-apple-separator/40 px-4 pb-4">
          {change.reason ? (
            <p className="mb-3 text-apple-footnote text-apple-label-secondary">{change.reason}</p>
          ) : null}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-apple border border-apple-separator/50 bg-apple-surface p-3">
              <p className="mb-2 text-apple-caption font-semibold uppercase tracking-wide text-apple-label-tertiary">
                Before
              </p>
              <p className="max-h-72 overflow-y-auto whitespace-pre-wrap text-apple-footnote leading-relaxed text-apple-label-secondary">
                {latexToReadable(change.original_text)}
              </p>
            </div>
            <div className="rounded-apple border border-apple-green/30 bg-green-500/5 p-3">
              <p className="mb-2 text-apple-caption font-semibold uppercase tracking-wide text-apple-green">
                After
              </p>
              <p className="max-h-72 overflow-y-auto whitespace-pre-wrap text-apple-footnote leading-relaxed text-apple-label">
                {latexToReadable(change.proposed_text)}
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function SectionDiffView({ changes }: SectionDiffViewProps) {
  if (changes.length === 0) {
    return (
      <p className="text-apple-subheadline text-apple-label-secondary" data-testid="no-changes">
        No changes for this job.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="section-diff-list">
      {changes.map((change) => (
        <DiffSection key={change.id} change={change} />
      ))}
    </div>
  );
}
