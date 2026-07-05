import { Suspense } from "react";
import EditPageContent from "./EditPageContent";

export default function EditPage() {
  return (
    <Suspense fallback={<div className="text-apple-subheadline text-apple-label-secondary">Loading…</div>}>
      <EditPageContent />
    </Suspense>
  );
}
