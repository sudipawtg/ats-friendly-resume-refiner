"use client";

import { useEffect } from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import Link from "next/link";

interface OutputsErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function OutputsError({ error, reset }: OutputsErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const handleRetry = () => {
    reset();
  };

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center px-4 text-center" data-testid="outputs-error">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10">
        <AlertCircle size={28} className="text-apple-red" />
      </div>
      <h1 className="text-apple-title-2 text-apple-label">Could not load downloads</h1>
      <p className="mt-2 max-w-md text-apple-subheadline text-apple-label-secondary">
        {error.message.includes("Cannot reach")
          ? "The API is unavailable. Start the backend, then retry."
          : "Something failed while loading your files."}
      </p>
      <div className="mt-6 flex gap-3">
        <button type="button" onClick={handleRetry} className="glass-button-primary">
          <RotateCcw size={16} />
          Retry
        </button>
        <Link href="/playground" className="glass-button">
          Go to Tailor
        </Link>
      </div>
    </div>
  );
}
