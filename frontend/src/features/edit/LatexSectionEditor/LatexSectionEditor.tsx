"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, RotateCcw, Save } from "lucide-react";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import {
  fetchMasterSection,
  fetchSectionHistory,
  restoreSectionVersion,
  saveSectionContent,
  type SectionVersionSummary,
} from "@/lib/api";

interface LatexSectionEditorProps {
  projectId: string;
  sectionPath: string;
  onSectionUpdated: () => void;
  onPdfRefresh: () => void;
}

export function LatexSectionEditor({
  projectId,
  sectionPath,
  onSectionUpdated,
  onPdfRefresh,
}: LatexSectionEditorProps) {
  const [editorContent, setEditorContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const {
    data: sectionData,
    isLoading,
    refetch: refetchSection,
  } = useQuery({
    queryKey: ["master-section", projectId, sectionPath],
    queryFn: () => fetchMasterSection(projectId, sectionPath),
    enabled: Boolean(projectId && sectionPath),
  });

  const {
    data: history = [],
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["section-history", projectId, sectionPath],
    queryFn: () => fetchSectionHistory(projectId, sectionPath),
    enabled: Boolean(projectId && sectionPath),
  });

  useEffect(() => {
    if (sectionData?.content !== undefined) {
      setEditorContent(sectionData.content);
    }
  }, [sectionData?.content]);

  const handleContentChange = useCallback((event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditorContent(event.target.value);
    setSuccessMessage("");
  }, []);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      await saveSectionContent(projectId, sectionPath, editorContent);
      setSuccessMessage("Saved");
      onSectionUpdated();
      onPdfRefresh();
      await refetchHistory();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }, [editorContent, onPdfRefresh, onSectionUpdated, projectId, refetchHistory, sectionPath]);

  const handleSaveClick = useCallback(() => {
    void handleSave();
  }, [handleSave]);

  const handleRestore = useCallback(
    async (version: SectionVersionSummary) => {
      setIsRestoring(true);
      setErrorMessage("");
      setSuccessMessage("");
      try {
        const restored = await restoreSectionVersion(projectId, sectionPath, version.version_id);
        setEditorContent(restored.content);
        setSuccessMessage("Restored previous version");
        onSectionUpdated();
        onPdfRefresh();
        await refetchSection();
        await refetchHistory();
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Restore failed");
      } finally {
        setIsRestoring(false);
      }
    },
    [onPdfRefresh, onSectionUpdated, projectId, refetchHistory, refetchSection, sectionPath]
  );

  const handleRestoreClick = useCallback(
    (version: SectionVersionSummary) => {
      void handleRestore(version);
    },
    [handleRestore]
  );

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-apple-blue" />
      </div>
    );
  }

  return (
    <div
      className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/40 p-3"
      data-testid={`latex-editor-${sectionPath}`}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="glass-badge-blue">{sectionDisplayName(sectionPath)}</span>
        <button
          type="button"
          onClick={handleSaveClick}
          disabled={isSaving}
          className="glass-button-primary text-sm"
          data-testid={`latex-save-${sectionPath}`}
        >
          {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save LaTeX
        </button>
      </div>

      <textarea
        value={editorContent}
        onChange={handleContentChange}
        rows={10}
        className="glass-input mb-2 font-mono text-xs"
        spellCheck={false}
        data-testid={`latex-textarea-${sectionPath}`}
      />

      {successMessage ? (
        <p className="mb-2 text-apple-caption text-apple-green">{successMessage}</p>
      ) : null}
      {errorMessage ? (
        <p className="mb-2 text-apple-caption text-apple-pink">{errorMessage}</p>
      ) : null}

      {history.length > 0 ? (
        <div data-testid={`latex-history-${sectionPath}`}>
          <p className="mb-2 text-apple-caption font-medium text-apple-label-secondary">Version history</p>
          <div className="space-y-1">
            {history.slice(0, 5).map((version) => (
              <div
                key={version.version_id}
                className="flex items-center justify-between gap-2 rounded-apple bg-white/40 px-2 py-1.5 dark:bg-white/5"
              >
                <div className="min-w-0">
                  <p className="truncate text-apple-caption text-apple-label">{version.source}</p>
                  <p className="truncate text-apple-caption text-apple-label-secondary">{version.preview}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleRestoreClick(version)}
                  disabled={isRestoring}
                  className="glass-button shrink-0 text-xs"
                  data-testid={`latex-restore-${version.version_id}`}
                >
                  <RotateCcw size={12} />
                  Undo
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
