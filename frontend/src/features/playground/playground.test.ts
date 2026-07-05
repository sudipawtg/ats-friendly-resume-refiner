import { describe, expect, it } from "vitest";
import {
  buildPlaygroundUrl,
  buildTailorPayload,
  canLoadJob,
  canRunTailoring,
  hasValidJobInput,
  MIN_MANUAL_JOB_CHARS,
  resolveDefaultEditableSections,
  resolveMasterPreviewSections,
} from "@/features/playground/playground.logic";
import { latexToReadable, sectionDisplayName } from "@/features/playground/latexPreview";

describe("playground.logic", () => {
  it("builds tailor payload from form state", () => {
    const payload = buildTailorPayload({
      selectedProjectId: "cv-1",
      jobUrl: "https://example.com/job",
      manualDescription: "",
      globalInstruction: "Emphasize AI",
      profileId: "ai_engineer",
      editableSections: ["sections/skills.tex"],
    });

    expect(payload.cv_project_id).toBe("cv-1");
    expect(payload.job_url).toBe("https://example.com/job");
    expect(payload.instruction_profile_id).toBe("ai_engineer");
  });

  it("validates job and cv requirements", () => {
    const shortManual = "x".repeat(MIN_MANUAL_JOB_CHARS - 1);
    const validManual = "x".repeat(MIN_MANUAL_JOB_CHARS);

    expect(hasValidJobInput({ selectedProjectId: "", jobUrl: "https://example.com", manualDescription: "", globalInstruction: "", profileId: "", editableSections: [] })).toBe(true);
    expect(hasValidJobInput({ selectedProjectId: "", jobUrl: "", manualDescription: validManual, globalInstruction: "", profileId: "", editableSections: [] })).toBe(true);
    expect(hasValidJobInput({ selectedProjectId: "", jobUrl: "", manualDescription: shortManual, globalInstruction: "", profileId: "", editableSections: [] })).toBe(false);
    expect(canLoadJob({ selectedProjectId: "", jobUrl: "", manualDescription: validManual, globalInstruction: "", profileId: "", editableSections: [] })).toBe(true);
    expect(canRunTailoring({ selectedProjectId: "cv-1", jobUrl: "", manualDescription: validManual, globalInstruction: "", profileId: "", editableSections: [] })).toBe(true);
    expect(canRunTailoring({ selectedProjectId: "", jobUrl: "", manualDescription: validManual, globalInstruction: "", profileId: "", editableSections: [] })).toBe(false);
  });

  it("builds playground url with query params", () => {
    expect(buildPlaygroundUrl({ url: "https://jobs.test/1", cvId: "abc" })).toBe(
      "/playground?url=https%3A%2F%2Fjobs.test%2F1&cvId=abc"
    );
  });

  it("resolves editable and master preview sections from project", () => {
    const projectSections = ["sections/skills.tex", "sections/education.tex"];
    expect(resolveDefaultEditableSections(projectSections)).toEqual([
      "sections/skills.tex",
      "sections/education.tex",
    ]);
    expect(resolveMasterPreviewSections(projectSections, ["sections/skills.tex"])).toEqual(projectSections);
  });
});

describe("latexPreview", () => {
  it("strips basic latex markup", () => {
    expect(latexToReadable("\\item Python \\textbf{AWS}")).toContain("Python");
    expect(latexToReadable("\\item Python \\textbf{AWS}")).toContain("AWS");
  });

  it("formats section names", () => {
    expect(sectionDisplayName("sections/experience.tex")).toBe("experience");
  });
});
