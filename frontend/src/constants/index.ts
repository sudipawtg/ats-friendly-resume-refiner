export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "/api";

export const NAV_ITEMS = [
  { href: "/", label: "Home", icon: "LayoutDashboard", group: "main" },
  { href: "/cvs", label: "CVs", icon: "FileText", group: "main" },
  { href: "/edit", label: "Edit", icon: "PenLine", group: "main" },
  { href: "/playground", label: "Tailor", icon: "FlaskConical", group: "main" },
  { href: "/discover", label: "Discover", icon: "Search", group: "jobs" },
  { href: "/jobs", label: "Saved", icon: "Inbox", group: "jobs" },
  { href: "/batch", label: "Campaigns", icon: "Layers", group: "jobs" },
  { href: "/outputs", label: "Downloads", icon: "Download", group: "more" },
  { href: "/instructions", label: "Settings", icon: "Settings2", group: "more" },
] as const;

export const NAV_GROUPS = {
  main: "Work",
  jobs: "Jobs",
  more: "More",
} as const;

export const INSTRUCTION_PROFILE_LABELS: Record<string, string> = {
  ai_engineer: "AI Engineer",
  ai_consultant: "AI Consultant",
  ai_product_manager: "AI Product Manager",
  data_analyst: "Data Analyst",
  technical_product_manager: "Technical Product Manager",
  research_academic: "Research / Academic",
};

export const DEFAULT_SECTIONS = [
  "sections/objective.tex",
  "sections/skills.tex",
  "sections/experience.tex",
  "sections/activities.tex",
  "sections/education.tex",
];
