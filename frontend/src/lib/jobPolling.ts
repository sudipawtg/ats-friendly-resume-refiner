import type { AnalyzeResponse, JobStatusResponse, TailorPreviewResponse, TailorResponse } from "@/lib/api";
import { fetchJobStatus } from "@/lib/api";

const TERMINAL_STATUSES = new Set(["completed", "needs_manual", "failed"]);

export async function pollJobUntilComplete(
  jobId: string,
  options?: { intervalMs?: number; timeoutMs?: number }
): Promise<JobStatusResponse> {
  const intervalMs = options?.intervalMs ?? 1500;
  const timeoutMs = options?.timeoutMs ?? 300_000;
  const maxAttempts = Math.ceil(timeoutMs / intervalMs);

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const statusResponse = await fetchJobStatus(jobId);
    if (TERMINAL_STATUSES.has(statusResponse.status)) {
      return statusResponse;
    }
    await new Promise((resolve) => {
      window.setTimeout(resolve, intervalMs);
    });
  }

  throw new Error("Job timed out while waiting for completion");
}

export async function resolveQueuedAnalyzeResponse(
  initialResponse: AnalyzeResponse
): Promise<AnalyzeResponse> {
  if (initialResponse.status !== "queued" || !initialResponse.job_id) {
    return initialResponse;
  }
  const polled = await pollJobUntilComplete(initialResponse.job_id);
  if (polled.status === "failed") {
    throw new Error(polled.error_message ?? "Analysis job failed");
  }
  return (polled.result as AnalyzeResponse | undefined) ?? initialResponse;
}

export async function resolveQueuedPreviewResponse(
  initialResponse: TailorPreviewResponse
): Promise<TailorPreviewResponse> {
  if (initialResponse.status !== "queued" || !initialResponse.job_id) {
    return initialResponse;
  }
  const polled = await pollJobUntilComplete(initialResponse.job_id);
  if (polled.status === "failed") {
    throw new Error(polled.error_message ?? "Preview job failed");
  }
  return (polled.result as TailorPreviewResponse | undefined) ?? initialResponse;
}

export async function resolveQueuedTailorResponse(
  initialResponse: TailorResponse
): Promise<TailorResponse> {
  if (initialResponse.status !== "queued") {
    return initialResponse;
  }
  const polled = await pollJobUntilComplete(initialResponse.job_id);
  if (polled.status === "failed") {
    throw new Error(polled.error_message ?? "Tailoring job failed");
  }
  return (polled.result as TailorResponse | undefined) ?? initialResponse;
}
