"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FileDown, FlaskConical, Loader2 } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { CoachChatPanel } from "@/features/edit/CoachChatPanel";
import { CVCoachPanel } from "@/features/edit/CVCoachPanel";
import { LatexSectionEditor } from "@/features/edit/LatexSectionEditor";
import { MasterSectionEditorPanel } from "@/features/edit/MasterSectionEditorPanel";
import { MasterSectionView } from "@/features/playground/MasterSectionView";
import { PdfPreviewPanel } from "@/features/playground/PdfPreviewPanel";
import { fetchCVProjects, fetchTailoringPreferences, getMasterDocxUrl, getMasterPdfUrl } from "@/lib/api";

export default function EditPageContent() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [pdfCacheKey, setPdfCacheKey] = useState(0);
  const [prefilledInstructions, setPrefilledInstructions] = useState<Record<string, string>>({});
  const [activeLatexSection, setActiveLatexSection] = useState("sections/experience.tex");
  const [coachTargetRole, setCoachTargetRole] = useState("Senior AI Engineer");
  const [coachFocus, setCoachFocus] = useState("");

  useEffect(() => {
    const cvParam = searchParams.get("cvId");
    if (cvParam) {
      setSelectedProjectId(cvParam);
    }
  }, [searchParams]);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["cvs"],
    queryFn: fetchCVProjects,
  });

  const { data: tailoringPreferences } = useQuery({
    queryKey: ["tailoring-preferences"],
    queryFn: fetchTailoringPreferences,
  });

  const selectedProject = projects.find((project) => project.id === selectedProjectId);

  useEffect(() => {
    if (!selectedProject?.sections.length) return;
    if (!selectedProject.sections.includes(activeLatexSection)) {
      setActiveLatexSection(selectedProject.sections[0] ?? "sections/experience.tex");
    }
  }, [activeLatexSection, selectedProject?.sections]);

  const handleProjectChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedProjectId(event.target.value);
    setPdfCacheKey(Date.now());
  }, []);

  const handleSectionUpdated = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["master-sections", selectedProjectId] });
  }, [queryClient, selectedProjectId]);

  const handlePdfRefresh = useCallback(() => {
    setPdfCacheKey(Date.now());
  }, []);

  const handleCoachSuggestionSelected = useCallback((sectionPath: string, instruction: string) => {
    setPrefilledInstructions({ [sectionPath]: instruction });
  }, []);

  const handleLatexSectionChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    setActiveLatexSection(event.target.value);
  }, []);

  const handleCoachTargetRoleChange = useCallback((value: string) => {
    setCoachTargetRole(value);
  }, []);

  const handleCoachFocusChange = useCallback((value: string) => {
    setCoachFocus(value);
  }, []);

  const mergedPrefilledInstructions = {
    ...(tailoringPreferences?.section_instructions ?? {}),
    ...prefilledInstructions,
  };

  const globalInstruction = tailoringPreferences?.global_instruction ?? "";

  const handleDownloadPdf = useCallback(() => {
    if (!selectedProjectId) return;
    window.open(`${getMasterPdfUrl(selectedProjectId, true)}&v=${pdfCacheKey}`, "_blank");
  }, [selectedProjectId, pdfCacheKey]);

  const handleDownloadDocx = useCallback(() => {
    if (!selectedProjectId) return;
    window.open(getMasterDocxUrl(selectedProjectId), "_blank");
  }, [selectedProjectId]);

  const masterPdfUrl = selectedProjectId
    ? `${getMasterPdfUrl(selectedProjectId)}?v=${pdfCacheKey}`
    : null;

  return (
    <div data-testid="edit-page">
      <PageHeader
        title="Edit CV"
        subtitle="CV Coach analyzes your CV and co-assists section improvements — preview updates live on the right."
        action={
          selectedProjectId ? (
            <Link href={`/playground?cvId=${selectedProjectId}`} className="glass-button-primary">
              <FlaskConical size={16} />
              Tailor for job
            </Link>
          ) : null
        }
      />

      <div className="glass-card mb-6">
        <label className="field-label" htmlFor="edit-cv-select">
          CV project
        </label>
        {isLoading ? (
          <p className="text-apple-footnote text-apple-label-secondary">Loading CVs…</p>
        ) : (
          <select
            id="edit-cv-select"
            value={selectedProjectId}
            onChange={handleProjectChange}
            className="glass-input max-w-md"
            data-testid="edit-cv-select"
          >
            <option value="">Select a CV…</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {!selectedProjectId ? (
        <EmptyState
          icon={Loader2}
          title="Select a CV"
          description="Choose a project above or upload one from the CVs page."
          testId="edit-empty"
        />
      ) : (
        <>
          <CVCoachPanel
            projectId={selectedProjectId}
            sectionPaths={selectedProject?.sections ?? []}
            targetRole={coachTargetRole}
            focus={coachFocus}
            onTargetRoleChange={handleCoachTargetRoleChange}
            onFocusChange={handleCoachFocusChange}
            globalInstruction={globalInstruction}
            onSectionUpdated={handleSectionUpdated}
            onPdfRefresh={handlePdfRefresh}
            onSuggestionSelected={handleCoachSuggestionSelected}
          />
          <div className="mb-6">
            <CoachChatPanel
              projectId={selectedProjectId}
              targetRole={coachTargetRole}
              focus={coachFocus}
              globalInstruction={globalInstruction}
              onSectionUpdated={handleSectionUpdated}
              onPdfRefresh={handlePdfRefresh}
              onSuggestionSelected={handleCoachSuggestionSelected}
            />
          </div>
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <section className="glass-card">
            <h2 className="section-title mb-4">Sections</h2>
            <MasterSectionEditorPanel
              projectId={selectedProjectId}
              sections={selectedProject?.sections ?? []}
              globalInstruction={globalInstruction}
              onSectionUpdated={handleSectionUpdated}
              onPdfRefresh={handlePdfRefresh}
              prefilledInstructions={mergedPrefilledInstructions}
            />
            <div className="mt-6 border-t border-apple-separator/60 pt-4">
              <h3 className="mb-3 text-apple-subheadline font-semibold text-apple-label">LaTeX editor</h3>
              <label className="field-label mb-2 block" htmlFor="latex-section-select">
                Section to edit
              </label>
              <select
                id="latex-section-select"
                value={activeLatexSection}
                onChange={handleLatexSectionChange}
                className="glass-input mb-3 max-w-md"
                data-testid="latex-section-select"
              >
                {(selectedProject?.sections ?? []).map((sectionPath) => (
                  <option key={sectionPath} value={sectionPath}>
                    {sectionPath}
                  </option>
                ))}
              </select>
              <LatexSectionEditor
                projectId={selectedProjectId}
                sectionPath={activeLatexSection}
                onSectionUpdated={handleSectionUpdated}
                onPdfRefresh={handlePdfRefresh}
              />
            </div>
            <div className="mt-6 border-t border-apple-separator/60 pt-4">
              <h3 className="mb-3 text-apple-subheadline font-semibold text-apple-label">Current content</h3>
              <MasterSectionView
                projectId={selectedProjectId}
                sectionPaths={selectedProject?.sections ?? []}
              />
            </div>
          </section>

          <section className="glass-card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="section-title">Preview</h2>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="glass-button-primary text-sm"
                  data-testid="edit-download-pdf-btn"
                >
                  <FileDown size={14} /> PDF
                </button>
                <button
                  type="button"
                  onClick={handleDownloadDocx}
                  className="glass-button text-sm"
                  data-testid="edit-download-docx-btn"
                >
                  <FileDown size={14} /> DOCX
                </button>
              </div>
            </div>
            <PdfPreviewPanel
              pdfUrl={masterPdfUrl}
              emptyMessage="Preview will appear once the PDF is generated."
              title="Master CV preview"
            />
          </section>
        </div>
        </>
      )}
    </div>
  );
}
