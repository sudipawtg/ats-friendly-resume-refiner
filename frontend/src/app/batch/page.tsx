import { Suspense } from "react";
import BatchPageContent from "./BatchPageContent";

export default function BatchPage() {
  return (
    <Suspense fallback={<div className="text-apple-subheadline text-apple-label-secondary">Loading campaign…</div>}>
      <BatchPageContent />
    </Suspense>
  );
}
