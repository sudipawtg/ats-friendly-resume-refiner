"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { Save, Wand2 } from "lucide-react";
import { Collapsible } from "@/components/Collapsible";
import { PageHeader } from "@/components/PageHeader";
import { sectionDisplayName } from "@/features/playground/latexPreview";
import { DEFAULT_SECTIONS, INSTRUCTION_PROFILE_LABELS } from "@/constants";
import { fetchInstructionProfiles, fetchTailoringPreferences, refinePrompt, saveTailoringPreferences } from "@/lib/api";

const DEFAULT_GLOBAL = `Professional, concise tone. No invented experience. UK English.`;

const SECTION_HINTS: Record<string, string> = {
  "sections/objective.tex": "Tailor to role — 3–4 lines",
  "sections/skills.tex": "Reorder by relevance",
  "sections/experience.tex": "Emphasise measurable outcomes",
  "sections/activities.tex": "Highlight relevant activities",
  "sections/education.tex": "Keep qualifications unchanged",
};

export default function InstructionsPage() {
  const [globalInstruction, setGlobalInstruction] = useState(DEFAULT_GLOBAL);
  const [sectionInstructions, setSectionInstructions] = useState<Record<string, string>>({});
  const [refinedOutput, setRefinedOutput] = useState("");
  const [activeSection, setActiveSection] = useState("sections/experience.tex");
  const [saveMessage, setSaveMessage] = useState("");

  const { data: profiles = {} } = useQuery({
    queryKey: ["profiles"],
    queryFn: fetchInstructionProfiles,
  });

  const { data: savedPreferences, refetch: refetchPreferences } = useQuery({
    queryKey: ["tailoring-preferences"],
    queryFn: fetchTailoringPreferences,
  });

  useEffect(() => {
    if (!savedPreferences) return;
    if (savedPreferences.global_instruction) {
      setGlobalInstruction(savedPreferences.global_instruction);
    }
    if (Object.keys(savedPreferences.section_instructions).length > 0) {
      setSectionInstructions(savedPreferences.section_instructions);
    }
  }, [savedPreferences]);

  const refineMutation = useMutation({
    mutationFn: () =>
      refinePrompt(
        sectionInstructions[activeSection] ?? globalInstruction,
        "Instruction Studio",
        activeSection
      ),
    onSuccess: (data) => {
      setRefinedOutput(data.refined_instruction);
      if (activeSection && sectionInstructions[activeSection] !== undefined) {
        setSectionInstructions((prev) => ({
          ...prev,
          [activeSection]: data.refined_instruction,
        }));
      } else {
        setGlobalInstruction(data.refined_instruction);
      }
    },
  });

  const handleApplyProfile = useCallback(
    (profileKey: string) => {
      const profileText = profiles[profileKey];
      if (profileText) {
        setGlobalInstruction(`${profileText}\n\n${DEFAULT_GLOBAL}`);
      }
    },
    [profiles]
  );

  const handleSectionChange = useCallback((section: string, value: string) => {
    setSectionInstructions((prev) => ({ ...prev, [section]: value }));
  }, []);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveTailoringPreferences({
        global_instruction: globalInstruction,
        section_instructions: sectionInstructions,
      }),
    onSuccess: async () => {
      setSaveMessage("Settings saved — Edit and Tailor will use these instructions.");
      await refetchPreferences();
    },
    onError: () => {
      setSaveMessage("Could not save settings.");
    },
  });

  const handleSaveSettings = useCallback(() => {
    setSaveMessage("");
    saveMutation.mutate();
  }, [saveMutation]);

  return (
    <div data-testid="instructions-page">
      <PageHeader title="Settings" subtitle="Guide how AI tailors your CV." />

      <div className="mb-4 flex flex-wrap gap-2">
        {Object.entries(profiles).map(([key]) => (
          <button
            key={key}
            type="button"
            onClick={() => handleApplyProfile(key)}
            className="glass-button text-sm"
            data-testid={`profile-${key}`}
          >
            {INSTRUCTION_PROFILE_LABELS[key] ?? key}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="glass-card">
          <h2 className="section-title mb-3">Global</h2>
          <textarea
            value={globalInstruction}
            onChange={(event) => setGlobalInstruction(event.target.value)}
            rows={5}
            className="glass-input resize-none"
            data-testid="global-instruction"
          />
        </div>

        <div className="glass-card">
          <h2 className="section-title mb-3">By section</h2>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {DEFAULT_SECTIONS.map((section) => (
              <button
                key={section}
                type="button"
                onClick={() => setActiveSection(section)}
                className={`rounded-full px-3 py-1 text-apple-caption font-medium transition-colors ${
                  activeSection === section
                    ? "bg-apple-blue/12 text-apple-blue"
                    : "bg-apple-surface-secondary text-apple-label-secondary"
                }`}
              >
                {sectionDisplayName(section)}
              </button>
            ))}
          </div>

          <textarea
            value={sectionInstructions[activeSection] ?? ""}
            onChange={(event) => handleSectionChange(activeSection, event.target.value)}
            rows={4}
            className="glass-input mb-3 resize-none"
            placeholder={SECTION_HINTS[activeSection]}
            data-testid="section-instruction"
          />

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => refineMutation.mutate()}
              disabled={refineMutation.isPending}
              className="glass-button text-sm"
              data-testid="refine-section-btn"
            >
              <Wand2 size={14} />
              {refineMutation.isPending ? "Refining…" : "Refine"}
            </button>
            <button
              type="button"
              onClick={handleSaveSettings}
              disabled={saveMutation.isPending}
              className="glass-button-primary text-sm"
              data-testid="save-instructions-btn"
            >
              <Save size={14} /> {saveMutation.isPending ? "Saving…" : "Save"}
            </button>
          </div>

          {saveMessage ? (
            <p className="mt-3 text-apple-footnote text-apple-label-secondary" data-testid="save-instructions-message">
              {saveMessage}
            </p>
          ) : null}

          {refinedOutput ? (
            <p className="mt-3 text-apple-footnote text-apple-label-secondary">{refinedOutput.slice(0, 200)}…</p>
          ) : null}
        </div>
      </div>

      <div className="mt-4">
        <Collapsible title="How defaults work">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="info-panel-blue">
              <p className="text-apple-subheadline font-medium text-apple-blue">STAR method</p>
              <p className="mt-1 text-apple-footnote text-apple-label-secondary">
                Experience bullets use Situation, Task, Action, Result — grounded in your CV.
              </p>
            </div>
            <div className="info-panel-indigo">
              <p className="text-apple-subheadline font-medium text-apple-indigo">ATS scoring</p>
              <p className="mt-1 text-apple-footnote text-apple-label-secondary">
                Every session includes keyword coverage and gap analysis.
              </p>
            </div>
          </div>
        </Collapsible>
      </div>
    </div>
  );
}
