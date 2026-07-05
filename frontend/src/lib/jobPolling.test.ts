import { describe, expect, it, vi } from "vitest";
import { pollJobUntilComplete } from "./jobPolling";
import type { JobStatusResponse } from "./api";

describe("pollJobUntilComplete", () => {
  it("returns immediately when job is already completed", async () => {
    const completedStatus: JobStatusResponse = {
      id: "job-1",
      status: "completed",
      job_type: "tailor",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        headers: { get: () => "application/json" },
        json: async () => completedStatus,
      })
    );

    const result = await pollJobUntilComplete("job-1", { intervalMs: 10, timeoutMs: 100 });
    expect(result.status).toBe("completed");
  });
});
