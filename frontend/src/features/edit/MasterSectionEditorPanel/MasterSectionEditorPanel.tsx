"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import { refineMasterSection } from "@/lib/api";

interface MasterSectionEditorPanelProps {
  projectId: string;
  sections: string[];
  globalInstruction?: string;
  onSectionUpdated: () => void;
  onPdfRefresh: () => void;
  prefilledInstructions?: Record<string, string>;
}

export function MasterSectionEditorPanel({
  projectId,
  sections,
  globalInstruction = "",
  onSectionUpdated,
  onPdfRefresh,
  prefilledInstructions = {},
}: MasterSectionEditorPanelProps) {
  const [instructions, setInstructions] = useState<Record<string, string>>({});
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successSection, setSuccessSection] = useState<string | null>(null);

  useEffect(() => {
    if (Object.keys(prefilledInstructions).length === 0) {
      return;
    }
    setInstructions((previous) => ({ ...previous, ...prefilledInstructions }));
  }, [prefilledInstructions]);

  const handleInstructionChange = useCallback((sectionPath: string, value: string) => {
    setInstructions((previous) => ({ ...previous, [sectionPath]: value }));
  }, []);

  const handleRegenerateSection = useCallback(
    async (sectionPath: string) => {
      setActiveSection(sectionPath);
      setErrorMessage("");
      setSuccessSection(null);
      try {
        await refineMasterSection({
          projectId,
          sectionPath,
          instruction: instructions[sectionPath] ?? "",
          globalInstruction,
        });
        setSuccessSection(sectionPath);
        onSectionUpdated();
        onPdfRefresh();
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Section update failed");
      } finally {
        setActiveSection(null);
      }
    },
    [globalInstruction, instructions, projectId, onSectionUpdated, onPdfRefresh]
  );

  const handleRegenerateClick = useCallback(
    (sectionPath: string) => {
      void handleRegenerateSection(sectionPath);
    },
    [handleRegenerateSection]
  );

  if (sections.length === 0) {
    return (
      <p className="text-apple-subheadline text-apple-label-secondary" data-testid="master-editor-empty">
        No editable sections found.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="master-section-editor">
      <p className="text-apple-footnote font-medium text-apple-label-secondary">
        Edit each section with AI — no job required. Changes save to your master CV.
      </p>

      {sections.map((sectionPath) => {
        const isRegenerating = activeSection === sectionPath;
        const didSucceed = successSection === sectionPath;

        return (
          <div
            key={sectionPath}
            className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/40 p-3"
            data-testid={`master-editor-${sectionPath}`}
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <span className="glass-badge-blue">{sectionDisplayName(sectionPath)}</span>
              {didSucceed ? (
                <span className="text-apple-caption text-apple-green">Updated</span>
              ) : null}
            </div>
            <textarea
              value={instructions[sectionPath] ?? ""}
              onChange={(event) => handleInstructionChange(sectionPath, event.target.value)}
              rows={3}
              placeholder="e.g. Make bullets more concise and add stronger action verbs"
              className="glass-input mb-2 resize-none text-sm"
              data-testid={`master-instruction-${sectionPath}`}
            />
            <button
              type="button"
              onClick={() => handleRegenerateClick(sectionPath)}
              disabled={isRegenerating || Boolean(activeSection)}
              className="glass-button text-sm"
              data-testid={`master-regenerate-${sectionPath}`}
            >
              {isRegenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {isRegenerating ? "Updating…" : "Update with AI"}
            </button>
          </div>
        );
      })}

      {errorMessage ? (
        <p className="text-apple-footnote text-apple-pink" data-testid="master-editor-error">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
