import JSZip from "jszip";

export async function createSampleCvZip(): Promise<Buffer> {
  const archive = new JSZip();
  archive.file(
    "Resume/resume.tex",
    "\\documentclass{article}\n\\input{_header.tex}\n\\begin{document}\n\\end{document}"
  );
  archive.file("Resume/_header.tex", "% header");
  archive.file("Resume/TLCresume.sty", "% style");
  archive.file("Resume/sections/objective.tex", "\\item Seeking AI engineering roles");
  archive.file("Resume/sections/skills.tex", "\\item Python, AWS, LLM, RAG");
  archive.file(
    "Resume/sections/experience.tex",
    "\\item Built enterprise AI systems with Python and Azure OpenAI"
  );
  archive.file("Resume/sections/education.tex", "\\item MSc Computer Science");
  archive.file("Resume/sections/activities.tex", "\\item Open source contributor");

  return archive.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}
