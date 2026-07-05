"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Download,
  FileDown,
  Sparkles,
  Wand2,
} from "lucide-react";
import { DEFAULT_SECTIONS, INSTRUCTION_PROFILE_LABELS } from "@/constants";
import {
  downloadHtmlReport,
  fetchCVProjects,
  fetchInstructionProfiles,
  getDownloadUrl,
  refinePrompt,
  tailorCV,
  type TailorResponse,
} from "@/lib/api";

export default function TailorPageContent() {
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
  const [result, setResult] = useState<TailorResponse | null>(null);
  const [refinedPreview, setRefinedPreview] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const urlParam = searchParams.get("url");
    if (urlParam) {
      setJobUrl(urlParam);
    }
  }, [searchParams]);

  const { data: projects = [] } = useQuery({ queryKey: ["cvs"], queryFn: fetchCVProjects });
  const { data: profiles = {} } = useQuery({ queryKey: ["profiles"], queryFn: fetchInstructionProfiles });

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  const refineMutation = useMutation({
    mutationFn: () => refinePrompt(globalInstruction, `Job: ${jobUrl}`),
    onSuccess: (data) => {
      setRefinedPreview(data.refined_instruction);
      if (data.refined_instruction) setGlobalInstruction(data.refined_instruction);
    },
  });

  const tailorMutation = useMutation({
    mutationFn: () =>
      tailorCV({
        cv_project_id: selectedProjectId,
        job_url: jobUrl || null,
        job_description: manualDescription || null,
        editable_sections: editableSections,
        global_instruction: globalInstruction,
        instruction_profile_id: profileId || null,
        refine_prompt: true,
      }),
    onSuccess: (data) => {
      setResult(data);
      setError("");
      if (data.refined_instructions) setRefinedPreview(data.refined_instructions);
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleToggleSection = useCallback((section: string) => {
    setEditableSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section]
    );
  }, []);

  const handleDownloadReport = useCallback(async () => {
    if (!result) return;
    const blob = await downloadHtmlReport({ job_id: result.job_id });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `resumeforge_report_${result.job_id.slice(0, 8)}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [result]);

  const handleDownloadZip = useCallback(() => {
    if (!result || !selectedProjectId) return;
    window.open(getDownloadUrl(selectedProjectId, result.job_id), "_blank");
  }, [result, selectedProjectId]);

  return (
    <div data-testid="tailor-page">
      <header className="page-header">
        <p className="page-eyebrow">Precision Mode</p>
        <h1 className="page-title">Single Job Tailor</h1>
        <p className="page-subtitle">
          Tailor your CV for one role with controlled sections, STAR methodology, and ATS scoring.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <div className="glass-card">
            <h2 className="mb-4 text-apple-title-2 text-apple-label">1. Select CV</h2>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="glass-input"
              data-testid="tailor-cv-select"
            >
              <option value="">Choose a CV project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="glass-card">
            <h2 className="mb-4 text-apple-title-2 text-apple-label">2. Job Details</h2>
            <label className="mb-1.5 block text-apple-footnote font-medium text-apple-label-secondary">Job URL</label>
            <input
              type="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="https://jobs.company.com/role"
              className="glass-input mb-4"
              data-testid="tailor-job-url"
            />
            <label className="mb-1.5 block text-apple-footnote font-medium text-apple-label-secondary">
              Or paste job description manually
            </label>
            <textarea
              value={manualDescription}
              onChange={(e) => setManualDescription(e.target.value)}
              rows={5}
              className="glass-input resize-none"
              placeholder="Paste full job description if link cannot be crawled..."
              data-testid="tailor-manual-jd"
            />
          </div>

          <div className="glass-card">
            <h2 className="mb-4 text-apple-title-2 text-apple-label">3. AI Instructions</h2>
            <label className="mb-1.5 block text-apple-footnote font-medium text-apple-label-secondary">Career profile</label>
            <select
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              className="glass-input mb-4"
              data-testid="tailor-profile-select"
            >
              <option value="">No profile — use STAR methodology</option>
              {Object.entries(profiles).map(([key, _]) => (
                <option key={key} value={key}>
                  {INSTRUCTION_PROFILE_LABELS[key] ?? key}
                </option>
              ))}
            </select>

            <label className="mb-1.5 block text-apple-footnote font-medium text-apple-label-secondary">Global instructions</label>
            <textarea
              value={globalInstruction}
              onChange={(e) => setGlobalInstruction(e.target.value)}
              rows={4}
              className="glass-input mb-3 resize-none"
              placeholder="Leave empty to apply STAR methodology and ATS optimisation automatically..."
              data-testid="tailor-global-instruction"
            />

            <button
              type="button"
              onClick={() => refineMutation.mutate()}
              disabled={refineMutation.isPending}
              className="glass-button mb-3"
              data-testid="refine-prompt-btn"
            >
              <Wand2 size={16} />
              {refineMutation.isPending ? "Refining..." : "Refine Instructions"}
            </button>

            {refinedPreview && (
              <div className="info-panel-indigo text-apple-subheadline text-apple-label-secondary">
                <p className="mb-1 text-apple-footnote font-semibold text-apple-indigo">Refined</p>
                {refinedPreview}
              </div>
            )}
          </div>

          <div className="glass-card">
            <h2 className="mb-4 text-apple-title-2 text-apple-label">4. Editable Sections</h2>
            <div className="space-y-2">
              {(selectedProject?.sections ?? DEFAULT_SECTIONS).map((section) => (
                <label key={section} className="flex cursor-pointer items-center gap-3 rounded-apple p-2 hover:bg-apple-fill">
                  <input
                    type="checkbox"
                    checked={editableSections.includes(section)}
                    onChange={() => handleToggleSection(section)}
                    className="h-4 w-4 accent-apple-blue"
                  />
                  <span className="text-apple-subheadline text-apple-label">{section}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => tailorMutation.mutate()}
            disabled={!selectedProjectId || tailorMutation.isPending || (!jobUrl && !manualDescription)}
            className="glass-button-primary w-full py-3"
            data-testid="tailor-submit-btn"
          >
            <Sparkles size={18} />
            {tailorMutation.isPending ? "Tailoring CV..." : "Generate Tailored CV"}
          </button>

          {error && (
            <div className="alert-error">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}
        </div>

        <div className="space-y-6">
          {result && (
            <>
              <div className="glass-card">
                <h2 className="mb-4 text-apple-title-2 text-apple-label">Fit & ATS Analysis</h2>
                <div className="mb-6 flex gap-6">
                  <div className="text-center">
                    <div className="score-ring mx-auto mb-2">{result.fit_analysis.overall_fit}%</div>
                    <p className="text-xs text-apple-label-secondary">Fit Score</p>
                  </div>
                  <div className="text-center">
                    <div className="score-ring-secondary mx-auto mb-2">
                      {result.ats_analysis.overall_score}
                    </div>
                    <p className="text-xs text-apple-label-secondary">ATS Score</p>
                  </div>
                </div>

                {result.fit_analysis.strong_matches.length > 0 && (
                  <>
                    <p className="mb-2 text-apple-headline text-apple-label">Strong Matches</p>
                    <ul className="mb-4 space-y-1 text-sm text-apple-label-secondary">
                      {result.fit_analysis.strong_matches.map((m) => (
                        <li key={m}>• {m}</li>
                      ))}
                    </ul>
                  </>
                )}

                {result.ats_analysis.gaps.length > 0 && (
                  <>
                    <p className="mb-2 text-apple-headline text-apple-orange">Gaps to Address</p>
                    <ul className="mb-4 space-y-1 text-sm text-apple-label-secondary">
                      {result.ats_analysis.gaps.map((g) => (
                        <li key={g}>• {g}</li>
                      ))}
                    </ul>
                  </>
                )}

                {result.ats_analysis.star_assessment.length > 0 && (
                  <>
                    <p className="mb-2 text-apple-headline text-apple-indigo">STAR Assessment</p>
                    <ul className="space-y-1 text-sm text-apple-label-secondary">
                      {result.ats_analysis.star_assessment.map((s) => (
                        <li key={s}>• {s}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>

              {result.changes.length > 0 && (
                <div className="glass-card">
                  <h2 className="mb-4 text-apple-title-2 text-apple-label">
                    Proposed Changes ({result.changes.length})
                  </h2>
                  {result.changes.map((change) => (
                    <div key={change.id} className="mb-4 rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary p-4">
                      <span className="glass-badge-blue">{change.section_path}</span>
                      <p className="mt-2 text-sm text-apple-label-secondary">{change.reason}</p>
                      <p className="mt-1 text-apple-footnote text-apple-label-tertiary">Evidence: {change.evidence_used}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-3">
                <button type="button" onClick={handleDownloadZip} className="glass-button-primary flex-1">
                  <Download size={16} /> Download Overleaf ZIP
                </button>
                <button type="button" onClick={handleDownloadReport} className="glass-button flex-1" data-testid="download-report-btn">
                  <FileDown size={16} /> HTML Report
                </button>
              </div>
            </>
          )}

          {!result && !tailorMutation.isPending && (
            <div className="glass-card flex h-64 flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-apple-blue/10">
                <Sparkles size={28} className="text-apple-blue/60" strokeWidth={1.75} />
              </div>
              <p className="text-apple-subheadline text-apple-label-secondary">
                Configure your job and instructions, then generate a tailored CV.
              </p>
              <p className="mt-2 text-apple-footnote text-apple-label-tertiary">
                Empty instructions → STAR methodology + ATS analysis applied automatically.
              </p>
            </div>
          )}

          {tailorMutation.isPending && (
            <div className="glass-card p-8 text-center text-apple-subheadline text-apple-blue" data-testid="tailor-loading">
              Analysing job description, scoring fit, and tailoring sections…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
