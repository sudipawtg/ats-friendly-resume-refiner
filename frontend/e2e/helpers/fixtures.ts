export const sampleJobDescription = `
Senior AI Engineer at Acme Corp, London, UK (Hybrid).
We are seeking a Senior AI Engineer with strong Python, machine learning, and LLM experience.
Responsibilities include building RAG pipelines, fine-tuning models, deploying on AWS,
collaborating with product teams, and mentoring junior engineers.
Required skills: Python, PyTorch, LangChain, AWS, FastAPI, OpenAI API, 5+ years experience.
Preferred: Kubernetes, MLOps, insurance domain knowledge, stakeholder engagement.
Benefits include competitive salary, pension, and flexible working arrangements.
`.trim();

export const mockCvProject = {
  id: "e2e-project-001",
  name: "E2E Test CV",
  master_file: "Resume/resume.tex",
  sections: [
    "sections/objective.tex",
    "sections/skills.tex",
    "sections/experience.tex",
    "sections/education.tex",
  ],
  locked_files: ["Resume/resume.tex", "TLCresume.sty", "_header.tex"],
  source_type: "zip",
  template_id: null,
  created_at: "2026-01-01T00:00:00.000Z",
};

export const mockTailorResult = {
  job_id: "e2e-job-001",
  fit_analysis: {
    overall_fit: 78,
    strong_matches: ["Python", "LLM", "AWS"],
    recommended_emphasis: ["RAG pipelines", "Enterprise AI"],
    potential_gaps: ["Insurance domain"],
  },
  ats_analysis: {
    overall_score: 72,
    keyword_coverage: ["Python", "AWS"],
    missing_keywords: ["Kubernetes"],
    formatting_notes: ["LaTeX structure preserved"],
    improvements: ["Add more quantified outcomes"],
    gaps: ["Domain-specific experience"],
    star_assessment: ["Experience bullets follow STAR structure"],
  },
  changes: [],
  refined_instructions: "Emphasize Python and LLM experience with STAR methodology.",
  status: "completed",
};

export const mockJobDescriptionExtract = {
  company: "Acme Corp",
  title: "Senior AI Engineer",
  location: "London, UK",
  working_model: "Hybrid",
  salary: "",
  responsibilities: ["Build RAG pipelines", "Deploy on AWS"],
  required_skills: ["Python", "LLM", "AWS"],
  preferred_skills: ["Kubernetes"],
  technologies: ["FastAPI", "LangChain"],
  seniority: "Senior",
  industry_keywords: ["AI"],
  visa_requirements: "",
  raw_text: sampleJobDescription,
  extraction_confidence: 0.92,
};

export const mockSectionChange = {
  id: "change-001",
  section_path: "sections/skills.tex",
  original_text: "\\item Python, SQL",
  proposed_text: "\\item Python, LLM, RAG, AWS",
  reason: "Align skills with job requirements",
  job_requirement: "Python and LLM experience",
  evidence_used: "Existing Python projects",
  status: "pending",
};

export const mockPreviewResult = {
  job_id: "e2e-preview-001",
  fit_analysis: mockTailorResult.fit_analysis,
  ats_analysis: mockTailorResult.ats_analysis,
  changes: [mockSectionChange],
  refined_instructions: mockTailorResult.refined_instructions,
  status: "completed",
};

export const mockAnalyzeResult = {
  fit_analysis: mockTailorResult.fit_analysis,
  ats_analysis: mockTailorResult.ats_analysis,
  job_description: mockJobDescriptionExtract,
  refined_instructions: mockTailorResult.refined_instructions,
  status: "completed",
};

export const mockJobSearchResult = {
  query: "AI Engineer",
  location: "London, UK",
  max_days_old: 7,
  total_results: 1,
  results: [
    {
      id: "search-job-001",
      title: "Senior AI Engineer",
      company: "Acme Corp",
      location: "London, UK",
      url: "https://example.com/jobs/ai-engineer",
      source: "reed_uk",
      source_label: "Reed UK",
      posted_date: "2026-01-01",
      posted_days_ago: 2,
      snippet: "Python, LLM, and AWS experience required.",
    },
  ],
  sources_searched: ["reed_uk"],
  warnings: [],
};
