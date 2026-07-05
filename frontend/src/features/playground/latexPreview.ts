export function latexToReadable(content: string): string {
  let text = content.trim();
  text = text.replace(/\\item\s*/g, "• ");
  text = text.replace(/\\textbf\{([^}]*)\}/g, "$1");
  text = text.replace(/\\emph\{([^}]*)\}/g, "$1");
  text = text.replace(/\\[a-zA-Z]+\{([^}]*)\}/g, "$1");
  text = text.replace(/\\[a-zA-Z]+/g, "");
  text = text.replace(/[{}]/g, "");
  text = text.replace(/\u2014/g, "-").replace(/\u2013/g, "-").replace(/\u2022/g, "•");
  text = text.replace(/\s+/g, " ").trim();
  return text;
}

export function sectionDisplayName(sectionPath: string): string {
  const fileName = sectionPath.split("/").pop() ?? sectionPath;
  return fileName.replace(".tex", "").replace(/_/g, " ");
}
