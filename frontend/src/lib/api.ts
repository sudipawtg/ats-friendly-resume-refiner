import { API_BASE_URL } from "@/constants";
import { buildTenantHeaders } from "@/lib/tenant";

export interface CVProject {
  id: string;
  name: string;
  master_file: string;
  sections: string[];
  locked_files: string[];
  source_type: string;
  template_id: string | null;
  created_at: string;
}

export interface CVTemplateSummary {
  id: string;
  name: string;
  description: string;
  preview_color: string;
  category: string;
  section_order: string[];
  preview_url: string;
}

export interface MasterSectionRefineResponse {
  section_path: string;
  content: string;
  reason: string;
}

export type CoachPriority = "high" | "medium" | "low";

export interface CVCoachSectionSuggestion {
  section_path: string;
  score: number;
  priority: CoachPriority;
  issues: string[];
  suggested_instruction: string;
}

export interface CVCoachReviewResponse {
  overall_score: number;
  summary: string;
  strengths: string[];
  top_improvements: string[];
  section_suggestions: CVCoachSectionSuggestion[];
}

export interface CVCoachReviewRequest {
  target_role?: string;
  focus?: string;
}

export interface CoachChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CoachChatResponse {
  reply: string;
  suggested_section_path: string | null;
  suggested_instruction: string | null;
}

export interface TailoringPreferences {
  global_instruction: string;
  section_instructions: Record<string, string>;
  active_profile_id: string | null;
}

export interface SectionVersionSummary {
  version_id: string;
  section_path: string;
  source: string;
  created_at: string;
  preview: string;
}

export interface JobDescriptionExtract {
  company: string;
  title: string;
  location: string;
  working_model: string;
  salary: string;
  responsibilities: string[];
  required_skills: string[];
  preferred_skills: string[];
  technologies: string[];
  seniority: string;
  industry_keywords: string[];
  visa_requirements: string;
  raw_text: string;
  extraction_confidence: number;
}

export interface FitAnalysis {
  overall_fit: number;
  strong_matches: string[];
  recommended_emphasis: string[];
  potential_gaps: string[];
}

export interface ATSAnalysis {
  overall_score: number;
  keyword_coverage: string[];
  missing_keywords: string[];
  formatting_notes: string[];
  improvements: string[];
  gaps: string[];
  star_assessment: string[];
}

export interface SectionChange {
  id: string;
  section_path: string;
  original_text: string;
  proposed_text: string;
  reason: string;
  job_requirement: string;
  evidence_used: string;
  status: string;
}

export interface TailorResponse {
  job_id: string;
  fit_analysis: FitAnalysis;
  ats_analysis: ATSAnalysis;
  changes: SectionChange[];
  refined_instructions: string;
  status: string;
}

export interface TailorPreviewResponse {
  job_id?: string | null;
  fit_analysis: FitAnalysis;
  ats_analysis: ATSAnalysis;
  changes: SectionChange[];
  refined_instructions: string;
  status: string;
}

export interface AnalyzeResponse {
  job_id?: string | null;
  fit_analysis: FitAnalysis;
  ats_analysis: ATSAnalysis;
  job_description: JobDescriptionExtract;
  refined_instructions: string;
  status: string;
}

export interface SectionRefineResponse {
  job_id: string;
  change: SectionChange;
  changes: SectionChange[];
  status: string;
}

export interface SectionContent {
  section_path: string;
  content: string;
}

export interface MasterSectionsResponse {
  sections: SectionContent[];
}

export interface TailorRequestPayload {
  cv_project_id: string;
  job_url: string | null;
  job_description: string | null;
  editable_sections: string[];
  global_instruction: string;
  instruction_profile_id: string | null;
  refine_prompt: boolean;
}

export interface BatchJobStatus {
  id: string;
  url: string | null;
  company: string;
  title: string;
  location: string;
  status: string;
  fit_score: number | null;
  key_skills: string[];
  tailoring_status: string;
  warnings: string[];
}

export interface BatchResponse {
  id: string;
  name: string;
  status: string;
  cv_project_id: string;
  total_jobs: number;
  completed: number;
  processing: number;
  needs_manual: number;
  failed: number;
  jobs: BatchJobStatus[];
  created_at: string;
}

export interface PromptRefineResponse {
  refined_instruction: string;
  methodology_applied: string;
  suggestions: string[];
}

export interface JobListingResult {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
  source_label: string;
  posted_date: string;
  posted_days_ago: number | null;
  snippet: string;
}

export interface JobSearchResponse {
  query: string;
  location: string;
  max_days_old: number;
  total_results: number;
  results: JobListingResult[];
  sources_searched: string[];
  warnings: string[];
}

export interface JobSearchRequest {
  job_title: string;
  location?: string;
  max_days_old?: number;
  sources?: string[];
  max_results_per_source?: number;
}

export interface SavedJob {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  fit_score: number | null;
  notes: string;
  job_description?: JobDescriptionExtract | null;
}

export interface OutputSummary {
  job_id: string;
  cv_project_id: string;
  status: string;
  job_type: string;
  fit_score: number | null;
  ats_score: number | null;
  url: string | null;
  updated_at: string | null;
}

export interface JobStatusResponse {
  id: string;
  status: string;
  job_type: string;
  cv_project_id?: string;
  error_message?: string | null;
  result?: AnalyzeResponse | TailorPreviewResponse | TailorResponse;
}

function encodeSectionPath(sectionPath: string): string {
  return sectionPath.split("/").map(encodeURIComponent).join("/");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...buildTenantHeaders(),
        ...options?.headers,
      },
    });
  } catch (error) {
    const isNetworkError =
      error instanceof TypeError ||
      (error instanceof Error && error.message.toLowerCase().includes("failed to fetch"));
    const message = isNetworkError
      ? "Cannot reach the ResumeForge API. The backend may be restarting or a long Preview request was interrupted. Wait a moment, refresh the page, and try again."
      : "Network request failed";
    throw new Error(message);
  }

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `Request failed: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response as unknown as T;
}

export async function fetchCVProjects(): Promise<CVProject[]> {
  return request<CVProject[]>("/cvs");
}

export async function uploadCV(
  file: File,
  name: string,
  templateId: string = "classic_blue"
): Promise<CVProject> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("template_id", templateId);
  return request<CVProject>("/cvs/upload", { method: "POST", body: formData });
}

export async function fetchCVTemplates(): Promise<CVTemplateSummary[]> {
  return request<CVTemplateSummary[]>("/cv-templates");
}

export async function createCVFromTemplate(name: string, templateId: string): Promise<CVProject> {
  return request<CVProject>("/cvs/from-template", {
    method: "POST",
    body: JSON.stringify({ name, template_id: templateId }),
  });
}

export async function applyCVTemplate(projectId: string, templateId: string): Promise<CVProject> {
  return request<CVProject>(`/cvs/${encodeURIComponent(projectId)}/apply-template`, {
    method: "POST",
    body: JSON.stringify({ template_id: templateId }),
  });
}

export async function refineMasterSection(payload: {
  projectId: string;
  sectionPath: string;
  instruction: string;
  globalInstruction?: string;
}): Promise<MasterSectionRefineResponse> {
  return request<MasterSectionRefineResponse>(
    `/cvs/${encodeURIComponent(payload.projectId)}/sections/refine`,
    {
      method: "POST",
      body: JSON.stringify({
        section_path: payload.sectionPath,
        instruction: payload.instruction,
        global_instruction: payload.globalInstruction ?? "",
      }),
    }
  );
}

export { fetchCVCoachReview, sendCoachChatMessage } from "./cvCoachApi";

export async function fetchTailoringPreferences(): Promise<TailoringPreferences> {
  return request<TailoringPreferences>("/settings/tailoring");
}

export async function saveTailoringPreferences(
  preferences: Partial<TailoringPreferences>
): Promise<TailoringPreferences> {
  return request<TailoringPreferences>("/settings/tailoring", {
    method: "PUT",
    body: JSON.stringify(preferences),
  });
}

export async function saveSectionContent(
  projectId: string,
  sectionPath: string,
  content: string
): Promise<{ section_path: string; content: string }> {
  return request<{ section_path: string; content: string }>(
    `/cvs/${encodeURIComponent(projectId)}/sections/${encodeSectionPath(sectionPath)}`,
    {
      method: "PUT",
      body: JSON.stringify({ content }),
    }
  );
}

export async function fetchSectionHistory(
  projectId: string,
  sectionPath: string
): Promise<SectionVersionSummary[]> {
  return request<SectionVersionSummary[]>(
    `/cvs/${encodeURIComponent(projectId)}/sections/${encodeSectionPath(sectionPath)}/history`
  );
}

export async function restoreSectionVersion(
  projectId: string,
  sectionPath: string,
  versionId: string
): Promise<{ section_path: string; content: string }> {
  return request<{ section_path: string; content: string }>(
    `/cvs/${encodeURIComponent(projectId)}/sections/${encodeSectionPath(sectionPath)}/restore`,
    {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    }
  );
}

export function getTemplatePreviewUrl(templateId: string): string {
  return `${API_BASE_URL}/cv-templates/${encodeURIComponent(templateId)}/preview.svg`;
}

export async function crawlJob(url: string, manualDescription?: string): Promise<JobDescriptionExtract> {
  return request<JobDescriptionExtract>("/crawl", {
    method: "POST",
    body: JSON.stringify({ url, manual_description: manualDescription ?? null }),
  });
}

export async function tailorCV(payload: TailorRequestPayload): Promise<TailorResponse> {
  return request<TailorResponse>("/tailor", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function analyzeCV(payload: TailorRequestPayload): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/tailor/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function previewTailorCV(payload: TailorRequestPayload): Promise<TailorPreviewResponse> {
  return request<TailorPreviewResponse>("/tailor/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refinePreviewSection(payload: {
  previewJobId: string;
  cvProjectId: string;
  sectionPath: string;
  instruction: string;
  jobUrl: string;
  manualDescription: string;
}): Promise<SectionRefineResponse> {
  return request<SectionRefineResponse>(
    `/tailor/preview/${encodeURIComponent(payload.previewJobId)}/refine-section`,
    {
      method: "POST",
      body: JSON.stringify({
        cv_project_id: payload.cvProjectId,
        section_path: payload.sectionPath,
        instruction: payload.instruction,
        job_url: payload.jobUrl.trim() || null,
        job_description: payload.manualDescription.trim() || null,
      }),
    }
  );
}

export async function fetchMasterSections(projectId: string): Promise<MasterSectionsResponse> {
  return request<MasterSectionsResponse>(`/cvs/${encodeURIComponent(projectId)}/master-sections`);
}

export async function fetchMasterSection(
  projectId: string,
  sectionPath: string
): Promise<SectionContent> {
  return request<SectionContent>(
    `/cvs/${encodeURIComponent(projectId)}/sections/${encodeSectionPath(sectionPath)}`
  );
}

export async function fetchOutputSection(
  projectId: string,
  jobId: string,
  sectionPath: string
): Promise<SectionContent> {
  return request<SectionContent>(
    `/cvs/${encodeURIComponent(projectId)}/outputs/${encodeURIComponent(jobId)}/sections/${encodeSectionPath(sectionPath)}`
  );
}

export async function refinePrompt(
  rawInstruction: string,
  context?: string,
  targetSection?: string
): Promise<PromptRefineResponse> {
  return request<PromptRefineResponse>("/prompt/refine", {
    method: "POST",
    body: JSON.stringify({
      raw_instruction: rawInstruction,
      context: context ?? "",
      target_section: targetSection ?? "",
    }),
  });
}

export async function createBatch(payload: Record<string, unknown>): Promise<BatchResponse> {
  return request<BatchResponse>("/batches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchBatches(): Promise<BatchResponse[]> {
  return request<BatchResponse[]>("/batches");
}

export async function fetchBatch(batchId: string): Promise<BatchResponse> {
  return request<BatchResponse>(`/batches/${batchId}`);
}

export async function fetchInstructionProfiles(): Promise<Record<string, string>> {
  return request<Record<string, string>>("/instruction-profiles");
}

export function getPdfUrl(projectId: string, jobId: string, download = false): string {
  const base = `${API_BASE_URL}/cvs/${encodeURIComponent(projectId)}/download/${encodeURIComponent(jobId)}/pdf`;
  return download ? `${base}?download=1` : base;
}

export function getDocxUrl(projectId: string, jobId: string): string {
  return `${API_BASE_URL}/cvs/${encodeURIComponent(projectId)}/download/${encodeURIComponent(jobId)}/docx`;
}

export function getMasterDocxUrl(projectId: string): string {
  return `${API_BASE_URL}/cvs/${encodeURIComponent(projectId)}/master-docx`;
}

export function getMasterPdfUrl(projectId: string, download = false): string {
  const base = `${API_BASE_URL}/cvs/${encodeURIComponent(projectId)}/master-pdf`;
  return download ? `${base}?download=1` : base;
}

export function getDownloadUrl(projectId: string, jobId: string): string {
  return `${API_BASE_URL}/cvs/${projectId}/download/${jobId}`;
}

export function getReportDownloadUrl(jobId?: string, batchId?: string): string {
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (batchId) params.set("batch_id", batchId);
  return `${API_BASE_URL}/reports/html?${params.toString()}`;
}

export async function downloadHtmlReport(payload: {
  job_id?: string;
  batch_id?: string;
  include_ats?: boolean;
  include_fit?: boolean;
  include_changes?: boolean;
  include_gaps?: boolean;
}): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/reports/html`, {
    method: "POST",
    body: JSON.stringify({
      include_ats: true,
      include_fit: true,
      include_changes: true,
      include_gaps: true,
      ...payload,
    }),
  });
  if (!response.ok) throw new Error("Report generation failed");
  return response.blob();
}

export async function searchJobs(payload: JobSearchRequest): Promise<JobSearchResponse> {
  return request<JobSearchResponse>("/jobs/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchJobSearchSources(): Promise<Record<string, string>> {
  return request<Record<string, string>>("/jobs/search/sources");
}

export async function fetchDateFilters(): Promise<Record<string, number>> {
  return request<Record<string, number>>("/jobs/search/date-filters");
}

export async function fetchSavedJobs(): Promise<SavedJob[]> {
  return request<SavedJob[]>("/saved-jobs");
}

export async function createSavedJob(payload: {
  url: string;
  title?: string;
  company?: string;
  location?: string;
  job_description?: JobDescriptionExtract | null;
  fit_score?: number | null;
  notes?: string;
}): Promise<SavedJob> {
  return request<SavedJob>("/saved-jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteSavedJob(savedJobId: string): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/saved-jobs/${savedJobId}`, { method: "DELETE" });
}

export async function fetchOutputs(): Promise<OutputSummary[]> {
  return request<OutputSummary[]>("/outputs");
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/jobs/${jobId}/status`);
}
