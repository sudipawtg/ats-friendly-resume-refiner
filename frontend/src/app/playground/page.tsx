import { Suspense } from "react";
import PlaygroundPageContent from "./PlaygroundPageContent";

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div className="text-apple-subheadline text-apple-label-secondary">Loading…</div>}>
      <PlaygroundPageContent />
    </Suspense>
  );
}
