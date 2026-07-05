"use client";

import { useCallback, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { SectionChange } from "@/lib/api";
import { sectionDisplayName } from "@/features/playground/latexPreview";

interface SectionEditorPanelProps {
  sections: string[];
  changes: SectionChange[];
  previewJobId: string;
  projectId: string;
  jobUrl: string;
  manualDescription: string;
  onSectionRefined: (updatedChanges: SectionChange[]) => void;
  onPdfRefresh: () => void;
  refineSection: (payload: {
    previewJobId: string;
    projectId: string;
    sectionPath: string;
    instruction: string;
    jobUrl: string;
    manualDescription: string;
  }) => Promise<SectionChange[]>;
}

export function SectionEditorPanel({
  sections,
  changes,
  previewJobId,
  projectId,
  jobUrl,
  manualDescription,
  onSectionRefined,
  onPdfRefresh,
  refineSection,
}: SectionEditorPanelProps) {
  const [instructions, setInstructions] = useState<Record<string, string>>({});
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleInstructionChange = useCallback((sectionPath: string, value: string) => {
    setInstructions((previous) => ({ ...previous, [sectionPath]: value }));
  }, []);

  const handleRegenerateSection = useCallback(
    async (sectionPath: string) => {
      setActiveSection(sectionPath);
      setErrorMessage("");
      try {
        const updatedChanges = await refineSection({
          previewJobId,
          projectId,
          sectionPath,
          instruction: instructions[sectionPath] ?? "",
          jobUrl,
          manualDescription,
        });
        onSectionRefined(updatedChanges);
        onPdfRefresh();
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Section update failed");
      } finally {
        setActiveSection(null);
      }
    },
    [
      instructions,
      previewJobId,
      projectId,
      jobUrl,
      manualDescription,
      onSectionRefined,
      onPdfRefresh,
      refineSection,
    ]
  );

  const handleRegenerateClick = useCallback(
    (sectionPath: string) => {
      void handleRegenerateSection(sectionPath);
    },
    [handleRegenerateSection]
  );

  if (sections.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-3 border-t border-apple-separator/60 pt-4" data-testid="section-editor-panel">
      <p className="text-apple-footnote font-medium text-apple-label-secondary">
        Edit sections with AI — adjust instructions and regenerate each part.
      </p>

      {sections.map((sectionPath) => {
        const change = changes.find((entry) => entry.section_path === sectionPath);
        const isRegenerating = activeSection === sectionPath;

        return (
          <div
            key={sectionPath}
            className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/40 p-3"
            data-testid={`section-editor-${sectionPath}`}
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <span className="glass-badge-blue">{sectionDisplayName(sectionPath)}</span>
              {change?.reason ? (
                <span className="text-apple-caption text-apple-label-tertiary">{change.reason}</span>
              ) : null}
            </div>
            <textarea
              value={instructions[sectionPath] ?? ""}
              onChange={(event) => handleInstructionChange(sectionPath, event.target.value)}
              rows={2}
              placeholder="Tell AI how to change this section…"
              className="glass-input mb-2 resize-none text-sm"
              data-testid={`section-instruction-${sectionPath}`}
            />
            <button
              type="button"
              onClick={() => handleRegenerateClick(sectionPath)}
              disabled={isRegenerating || Boolean(activeSection)}
              className="glass-button text-sm"
              data-testid={`section-regenerate-${sectionPath}`}
            >
              {isRegenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {isRegenerating ? "Regenerating…" : "Regenerate with AI"}
            </button>
          </div>
        );
      })}

      {errorMessage ? (
        <p className="text-apple-footnote text-apple-pink" data-testid="section-editor-error">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
