import clsx from "clsx";
import { Check } from "lucide-react";

export interface WizardStep {
  id: string;
  label: string;
  isActive: boolean;
  isComplete: boolean;
}

interface StepWizardProps {
  steps: WizardStep[];
  testId?: string;
}

export function StepWizard({ steps, testId }: StepWizardProps) {
  return (
    <div className="mb-8" data-testid={testId}>
      <div className="flex items-center gap-0 overflow-x-auto pb-1">
        {steps.map((step, index) => (
          <div key={step.id} className="flex shrink-0 items-center">
            <div className="flex flex-col items-center gap-1.5 px-1">
              <div
                className={clsx(
                  "flex h-8 w-8 items-center justify-center rounded-full text-apple-caption font-semibold transition-colors",
                  step.isActive && "bg-brand-gradient text-white shadow-brand",
                  !step.isActive && step.isComplete && "bg-emerald-500/12 text-apple-green",
                  !step.isActive && !step.isComplete && "bg-apple-surface-tertiary text-apple-label-tertiary"
                )}
              >
                {step.isComplete && !step.isActive ? <Check size={14} strokeWidth={2.5} /> : index + 1}
              </div>
              <span
                className={clsx(
                  "whitespace-nowrap text-apple-caption font-medium",
                  step.isActive ? "text-brand-600" : "text-apple-label-secondary"
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 ? (
              <div
                className={clsx(
                  "mx-1 mb-5 h-0.5 w-6 shrink-0 rounded-full sm:w-10",
                  step.isComplete ? "bg-brand-400/35" : "bg-apple-separator/60"
                )}
              />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
