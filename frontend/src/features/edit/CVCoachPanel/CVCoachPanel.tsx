"use client";

import { useCallback, useState } from "react";
import clsx from "clsx";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import { fetchCVCoachReview } from "@/lib/cvCoachApi";
import {
  refineMasterSection,
  type CVCoachReviewResponse,
  type CVCoachSectionSuggestion,
} from "@/lib/api";

interface CVCoachPanelProps {
  projectId: string;
  sectionPaths: string[];
  targetRole: string;
  focus: string;
  onTargetRoleChange: (value: string) => void;
  onFocusChange: (value: string) => void;
  globalInstruction?: string;
  onSectionUpdated: () => void;
  onPdfRefresh: () => void;
  onSuggestionSelected: (sectionPath: string, instruction: string) => void;
}

const COACH_FOCUS_OPTIONS = [
  { value: "", label: "Balanced (recommended)" },
  { value: "impact and measurable outcomes", label: "Impact & metrics" },
  { value: "ATS keywords and clarity", label: "ATS readability" },
  { value: "STAR experience bullets", label: "STAR bullets" },
  { value: "concise professional tone", label: "Conciseness" },
] as const;

function priorityBadgeClass(priority: CVCoachSectionSuggestion["priority"]): string {
  if (priority === "high") {
    return "glass-badge-pink";
  }
  if (priority === "low") {
    return "glass-badge-blue opacity-80";
  }
  return "glass-badge-blue";
}

export function CVCoachPanel({
  projectId,
  sectionPaths,
  targetRole,
  focus,
  onTargetRoleChange,
  onFocusChange,
  globalInstruction = "",
  onSectionUpdated,
  onPdfRefresh,
  onSuggestionSelected,
}: CVCoachPanelProps) {
  const [review, setReview] = useState<CVCoachReviewResponse | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [applyingSection, setApplyingSection] = useState<string | null>(null);
  const [isApplyingAll, setIsApplyingAll] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleTargetRoleChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onTargetRoleChange(event.target.value);
    },
    [onTargetRoleChange]
  );

  const handleFocusChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      onFocusChange(event.target.value);
    },
    [onFocusChange]
  );

  const handleAnalyzeCv = useCallback(async () => {
    setIsReviewing(true);
    setErrorMessage("");
    try {
      const result = await fetchCVCoachReview(projectId, {
        target_role: targetRole,
        focus,
      });
      setReview(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "CV review failed");
    } finally {
      setIsReviewing(false);
    }
  }, [focus, projectId, targetRole]);

  const handleAnalyzeClick = useCallback(() => {
    void handleAnalyzeCv();
  }, [handleAnalyzeCv]);

  const handleApplySuggestion = useCallback(
    async (suggestion: CVCoachSectionSuggestion) => {
      setApplyingSection(suggestion.section_path);
      setErrorMessage("");
      try {
        await refineMasterSection({
          projectId,
          sectionPath: suggestion.section_path,
          instruction: suggestion.suggested_instruction,
          globalInstruction:
            globalInstruction || (targetRole.trim() ? `Optimize for target role: ${targetRole.trim()}` : ""),
        });
        onSectionUpdated();
        onPdfRefresh();
        onSuggestionSelected(suggestion.section_path, suggestion.suggested_instruction);
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Could not apply suggestion");
      } finally {
        setApplyingSection(null);
      }
    },
    [globalInstruction, onPdfRefresh, onSectionUpdated, onSuggestionSelected, projectId, targetRole]
  );

  const handleApplySuggestionClick = useCallback(
    (suggestion: CVCoachSectionSuggestion) => {
      void handleApplySuggestion(suggestion);
    },
    [handleApplySuggestion]
  );

  const handleUseSuggestion = useCallback(
    (suggestion: CVCoachSectionSuggestion) => {
      onSuggestionSelected(suggestion.section_path, suggestion.suggested_instruction);
    },
    [onSuggestionSelected]
  );

  const handleApplyAllHighPriority = useCallback(async () => {
    if (!review) return;
    const highPriority = review.section_suggestions.filter(
      (suggestion) => suggestion.priority === "high"
    );
    if (highPriority.length === 0) return;

    setIsApplyingAll(true);
    setErrorMessage("");
    try {
      for (const suggestion of highPriority) {
        setApplyingSection(suggestion.section_path);
        await refineMasterSection({
          projectId,
          sectionPath: suggestion.section_path,
          instruction: suggestion.suggested_instruction,
          globalInstruction:
            globalInstruction || (targetRole.trim() ? `Optimize for target role: ${targetRole.trim()}` : ""),
        });
      }
      onSectionUpdated();
      onPdfRefresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not apply all suggestions");
    } finally {
      setApplyingSection(null);
      setIsApplyingAll(false);
    }
  }, [onPdfRefresh, onSectionUpdated, projectId, review, targetRole]);

  const handleApplyAllClick = useCallback(() => {
    void handleApplyAllHighPriority();
  }, [handleApplyAllHighPriority]);

  const highPriorityCount =
    review?.section_suggestions.filter((suggestion) => suggestion.priority === "high").length ?? 0;

  if (sectionPaths.length === 0) {
    return null;
  }

  return (
    <section className="glass-card mb-6" data-testid="cv-coach-panel">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="section-title flex items-center gap-2">
            <Sparkles size={18} className="text-brand-500" />
            CV Coach
          </h2>
          <p className="mt-1 text-apple-footnote text-apple-label-secondary">
            AI co-assist reviews your CV and suggests one-click improvements section by section.
          </p>
        </div>
        <button
          type="button"
          onClick={handleAnalyzeClick}
          disabled={isReviewing || isApplyingAll}
          className="glass-button-primary text-sm"
          data-testid="cv-coach-analyze-btn"
        >
          {isReviewing ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
          {isReviewing ? "Analyzing…" : "Analyze my CV"}
        </button>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="cv-coach-target-role">
            Target role
          </label>
          <input
            id="cv-coach-target-role"
            value={targetRole}
            onChange={handleTargetRoleChange}
            placeholder="e.g. Senior AI Engineer"
            className="glass-input"
            data-testid="cv-coach-target-role"
          />
        </div>
        <div>
          <label className="field-label" htmlFor="cv-coach-focus">
            Focus
          </label>
          <select
            id="cv-coach-focus"
            value={focus}
            onChange={handleFocusChange}
            className="glass-input"
            data-testid="cv-coach-focus"
          >
            {COACH_FOCUS_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {errorMessage ? (
        <p className="alert-error mb-4" data-testid="cv-coach-error">
          {errorMessage}
        </p>
      ) : null}

      {review ? (
        <div className="space-y-4" data-testid="cv-coach-results">
          <div className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/40 p-4">
            <div className="mb-2 flex flex-wrap items-center gap-3">
              <span className="glass-badge-green text-base">{review.overall_score}/100</span>
              <span className="text-apple-subheadline font-semibold text-apple-label">Overall CV score</span>
            </div>
            <p className="text-apple-subheadline text-apple-label-secondary">{review.summary}</p>
            {review.top_improvements.length > 0 ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-apple-footnote text-apple-label-secondary">
                {review.top_improvements.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            {highPriorityCount > 0 ? (
              <button
                type="button"
                onClick={handleApplyAllClick}
                disabled={isApplyingAll || Boolean(applyingSection)}
                className="glass-button-primary mt-4 text-sm"
                data-testid="cv-coach-apply-all-btn"
              >
                {isApplyingAll ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                Apply all high-priority fixes ({highPriorityCount})
              </button>
            ) : null}
          </div>

          <div className="space-y-3">
            {review.section_suggestions.map((suggestion) => {
              const isApplying = applyingSection === suggestion.section_path;
              return (
                <div
                  key={suggestion.section_path}
                  className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/30 p-3"
                  data-testid={`cv-coach-section-${suggestion.section_path}`}
                >
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="glass-badge-blue">{sectionDisplayName(suggestion.section_path)}</span>
                      <span className={clsx("text-xs uppercase tracking-wider", priorityBadgeClass(suggestion.priority))}>
                        {suggestion.priority} priority
                      </span>
                      <span className="text-apple-caption text-apple-label-secondary">
                        Score: {suggestion.score}/100
                      </span>
                    </div>
                  </div>
                  {suggestion.issues.length > 0 ? (
                    <ul className="mb-2 list-disc space-y-1 pl-5 text-apple-footnote text-apple-label-secondary">
                      {suggestion.issues.map((issue) => (
                        <li key={issue}>{issue}</li>
                      ))}
                    </ul>
                  ) : null}
                  <p className="mb-3 text-apple-footnote text-apple-label">{suggestion.suggested_instruction}</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleApplySuggestionClick(suggestion)}
                      disabled={isApplying || isApplyingAll}
                      className="glass-button-primary text-sm"
                      data-testid={`cv-coach-apply-${suggestion.section_path}`}
                    >
                      {isApplying ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                      Apply fix
                    </button>
                    <button
                      type="button"
                      onClick={() => handleUseSuggestion(suggestion)}
                      className="glass-button text-sm"
                      data-testid={`cv-coach-use-${suggestion.section_path}`}
                    >
                      Edit instruction
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-apple-footnote text-apple-label-secondary" data-testid="cv-coach-empty">
          Run analysis to get personalized suggestions for each section.
        </p>
      )}
    </section>
  );
}
