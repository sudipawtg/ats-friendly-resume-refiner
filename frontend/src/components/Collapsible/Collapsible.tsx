"use client";

import { ChevronDown } from "lucide-react";
import { useCallback, useState } from "react";
import clsx from "clsx";

interface CollapsibleProps {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  testId?: string;
}

export function Collapsible({ title, count, defaultOpen = false, children, testId }: CollapsibleProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const handleToggle = useCallback(() => {
    setIsOpen((previous) => !previous);
  }, []);

  return (
    <div className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/50" data-testid={testId}>
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
        aria-expanded={isOpen}
      >
        <span className="text-apple-subheadline font-medium text-apple-label">
          {title}
          {count !== undefined ? (
            <span className="ml-2 text-apple-footnote font-normal text-apple-label-secondary">({count})</span>
          ) : null}
        </span>
        <ChevronDown
          size={18}
          className={clsx("shrink-0 text-apple-label-tertiary transition-transform duration-200", isOpen && "rotate-180")}
        />
      </button>
      {isOpen ? <div className="border-t border-apple-separator/40 px-4 pb-4 pt-2">{children}</div> : null}
    </div>
  );
}
