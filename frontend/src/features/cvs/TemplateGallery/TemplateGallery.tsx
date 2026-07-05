"use client";

import clsx from "clsx";
import { Check, Loader2 } from "lucide-react";
import type { CVTemplateSummary } from "@/lib/api";
import { getTemplatePreviewUrl } from "@/lib/api";

interface TemplateGalleryProps {
  templates: CVTemplateSummary[];
  selectedTemplateId: string;
  onSelectTemplate: (templateId: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function TemplateGallery({
  templates,
  selectedTemplateId,
  onSelectTemplate,
  isLoading = false,
  disabled = false,
}: TemplateGalleryProps) {
  if (isLoading) {
    return (
      <p className="text-apple-footnote text-apple-label-secondary" data-testid="template-gallery-loading">
        Loading templates…
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="template-gallery">
      {templates.map((template) => {
        const isSelected = template.id === selectedTemplateId;
        const previewUrl = template.preview_url || getTemplatePreviewUrl(template.id);

        return (
          <button
            key={template.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectTemplate(template.id)}
            className={clsx(
              "glass-card relative overflow-hidden p-4 text-left transition-all",
              isSelected && "ring-2 ring-brand-500/60",
              disabled && "cursor-not-allowed opacity-60"
            )}
            data-testid={`template-card-${template.id}`}
          >
            <div className="mb-3 overflow-hidden rounded-lg border border-apple-separator/40 bg-white">
              <img
                src={previewUrl}
                alt={`${template.name} preview`}
                className="h-28 w-full object-cover object-top"
                data-testid={`template-preview-${template.id}`}
              />
            </div>

            <div className="mb-1 flex items-start justify-between gap-2">
              <h3 className="text-apple-subheadline font-semibold text-apple-label">{template.name}</h3>
              {isSelected ? (
                <span className="rounded-full bg-brand-500/15 p-1 text-brand-600">
                  <Check size={14} strokeWidth={2.5} />
                </span>
              ) : null}
            </div>

            <p className="mb-2 text-apple-caption text-apple-label-secondary">{template.description}</p>
            <span className="glass-badge-blue">{template.category}</span>
          </button>
        );
      })}

      {templates.length === 0 ? (
        <div className="col-span-full flex items-center gap-2 text-apple-footnote text-apple-label-secondary">
          <Loader2 size={16} className="animate-spin" />
          No templates available
        </div>
      ) : null}
    </div>
  );
}
