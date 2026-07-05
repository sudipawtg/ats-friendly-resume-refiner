"use client";

import { useEffect } from "react";
import { AlertCircle, RotateCcw } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const handleRetry = () => {
    reset();
  };

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center" data-testid="app-error">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10">
        <AlertCircle size={28} className="text-apple-red" />
      </div>
      <h1 className="text-apple-title-2 text-apple-label">Something went wrong</h1>
      <p className="mt-2 max-w-md text-apple-subheadline text-apple-label-secondary">
        {error.message || "An unexpected error occurred. Try again."}
      </p>
      <button type="button" onClick={handleRetry} className="glass-button-primary mt-6">
        <RotateCcw size={16} />
        Try again
      </button>
    </div>
  );
}
