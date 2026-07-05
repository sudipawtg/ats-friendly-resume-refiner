import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  testId?: string;
}

export function EmptyState({ icon: Icon, title, description, action, testId }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-apple-xl border border-dashed border-apple-separator/80 bg-apple-surface-secondary/40 px-6 py-12 text-center"
      data-testid={testId}
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-500/10">
        <Icon size={28} className="text-brand-500/80" strokeWidth={1.75} />
      </div>
      <p className="text-apple-headline text-apple-label">{title}</p>
      {description ? (
        <p className="mt-1 max-w-sm text-apple-subheadline text-apple-label-secondary">{description}</p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
