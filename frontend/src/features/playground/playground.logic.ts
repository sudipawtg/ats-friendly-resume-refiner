import type { TailorRequestPayload } from "@/lib/api";
import { DEFAULT_SECTIONS } from "@/constants";

export type PlaygroundStep = "setup" | "job_loaded" | "analyzed" | "previewed" | "applied";

export const MIN_MANUAL_JOB_CHARS = 50;
export const RECOMMENDED_JOB_CHARS = 200;

export interface PlaygroundFormState {
  selectedProjectId: string;
  jobUrl: string;
  manualDescription: string;
  globalInstruction: string;
  profileId: string;
  editableSections: string[];
}

export function buildTailorPayload(form: PlaygroundFormState): TailorRequestPayload {
  return {
    cv_project_id: form.selectedProjectId,
    job_url: form.jobUrl.trim() || null,
    job_description: form.manualDescription.trim() || null,
    editable_sections: form.editableSections,
    global_instruction: form.globalInstruction,
    instruction_profile_id: form.profileId || null,
    refine_prompt: true,
  };
}

export function hasValidJobInput(form: PlaygroundFormState): boolean {
  if (form.jobUrl.trim()) {
    return true;
  }
  return form.manualDescription.trim().length >= MIN_MANUAL_JOB_CHARS;
}

export function canLoadJob(form: PlaygroundFormState): boolean {
  return hasValidJobInput(form);
}

export function canRunTailoring(form: PlaygroundFormState): boolean {
  return Boolean(form.selectedProjectId && hasValidJobInput(form));
}

export function buildPlaygroundUrl(params: {
  url?: string;
  cvId?: string;
  title?: string;
  company?: string;
}): string {
  const search = new URLSearchParams();
  if (params.url) search.set("url", params.url);
  if (params.cvId) search.set("cvId", params.cvId);
  if (params.title) search.set("title", params.title);
  if (params.company) search.set("company", params.company);
  const query = search.toString();
  return query ? `/playground?${query}` : "/playground";
}

export function resolveDefaultEditableSections(projectSections: string[]): string[] {
  const matchingSections = DEFAULT_SECTIONS.filter((section) => projectSections.includes(section));
  if (matchingSections.length > 0) {
    return matchingSections;
  }
  return projectSections.slice(0, Math.min(3, projectSections.length));
}

export function resolveMasterPreviewSections(
  projectSections: string[],
  editableSections: string[]
): string[] {
  if (projectSections.length > 0) {
    return projectSections;
  }
  return editableSections;
}
