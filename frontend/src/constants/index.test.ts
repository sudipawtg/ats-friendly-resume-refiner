import { describe, expect, it } from "vitest";
import {
  API_BASE_URL,
  DEFAULT_SECTIONS,
  INSTRUCTION_PROFILE_LABELS,
  NAV_ITEMS,
} from "./index";

describe("constants", () => {
  it("API_BASE_URL defaults to same-origin proxy path", () => {
    expect(API_BASE_URL).toBe("/api");
  });

  it("NAV_ITEMS includes all main routes", () => {
    const hrefs = NAV_ITEMS.map((item) => item.href);
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/cvs");
    expect(hrefs).toContain("/edit");
    expect(hrefs).toContain("/playground");
    expect(hrefs).toContain("/discover");
    expect(hrefs).toContain("/jobs");
    expect(hrefs).toContain("/batch");
    expect(hrefs).toContain("/instructions");
    expect(hrefs).toContain("/outputs");
  });

  it("each nav item has label and icon", () => {
    for (const item of NAV_ITEMS) {
      expect(item.label.length).toBeGreaterThan(0);
      expect(item.icon.length).toBeGreaterThan(0);
    }
  });

  it("INSTRUCTION_PROFILE_LABELS maps all profile keys", () => {
    expect(INSTRUCTION_PROFILE_LABELS.ai_engineer).toBe("AI Engineer");
    expect(INSTRUCTION_PROFILE_LABELS.ai_consultant).toBe("AI Consultant");
    expect(INSTRUCTION_PROFILE_LABELS.research_academic).toBe("Research / Academic");
  });

  it("DEFAULT_SECTIONS lists five LaTeX section paths", () => {
    expect(DEFAULT_SECTIONS).toHaveLength(5);
    expect(DEFAULT_SECTIONS.every((s) => s.startsWith("sections/"))).toBe(true);
    expect(DEFAULT_SECTIONS).toContain("sections/experience.tex");
  });
});
