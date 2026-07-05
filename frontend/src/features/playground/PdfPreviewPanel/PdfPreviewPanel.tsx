"use client";

import { Loader2 } from "lucide-react";

interface PdfPreviewPanelProps {
  pdfUrl: string | null;
  isLoading?: boolean;
  emptyMessage: string;
  title: string;
}

export function PdfPreviewPanel({
  pdfUrl,
  isLoading = false,
  emptyMessage,
  title,
}: PdfPreviewPanelProps) {
  if (isLoading) {
    return (
      <div
        className="flex h-[480px] flex-col items-center justify-center rounded-apple-lg border border-dashed border-apple-separator/80 bg-apple-surface-secondary/50 sm:h-[560px]"
        data-testid="playground-preview-loading"
      >
        <Loader2 size={28} className="mb-2 animate-spin text-apple-blue" />
        <p className="text-apple-subheadline text-apple-label-secondary">Building PDF preview…</p>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div
        className="flex h-[480px] flex-col items-center justify-center rounded-apple-lg border border-dashed border-apple-separator/80 bg-apple-surface-secondary/50 text-center sm:h-[560px]"
        data-testid="playground-preview-empty"
      >
        <p className="text-apple-subheadline text-apple-label-secondary">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <iframe
      title={title}
      src={pdfUrl}
      className="h-[480px] w-full rounded-apple border border-apple-separator/60 bg-white sm:h-[560px]"
      data-testid="playground-pdf-viewer"
    />
  );
}
