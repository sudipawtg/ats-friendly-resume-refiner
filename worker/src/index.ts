import express from "express";
import { Queue, Worker } from "bullmq";

const redisUrl = process.env.REDIS_URL ?? "redis://127.0.0.1:6379";
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const internalApiKey = process.env.INTERNAL_API_KEY ?? "";
const queuePort = Number(process.env.QUEUE_PORT ?? "8787");
const queueName = process.env.QUEUE_NAME ?? "tailoring";

function buildRedisConnection(redisConnectionUrl: string) {
  const parsedUrl = new URL(redisConnectionUrl);
  const databasePath = parsedUrl.pathname.replace("/", "");
  return {
    host: parsedUrl.hostname,
    port: Number(parsedUrl.port || "6379"),
    password: parsedUrl.password || undefined,
    username: parsedUrl.username || undefined,
    db: databasePath ? Number(databasePath) : 0,
    maxRetriesPerRequest: null,
  };
}

const connection = buildRedisConnection(redisUrl);
const tailoringQueue = new Queue(queueName, { connection });

interface EnqueueRequestBody {
  queue: string;
  name: string;
  jobId: string;
  tenantId: string;
  payload: Record<string, unknown>;
}

async function executeOnBackend(body: EnqueueRequestBody): Promise<void> {
  const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/internal/worker/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-API-Key": internalApiKey,
    },
    body: JSON.stringify({
      job_id: body.jobId,
      tenant_id: body.tenantId,
      job_type: body.name,
      payload: body.payload,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend worker execute failed (${response.status}): ${errorText}`);
  }
}

const worker = new Worker(
  queueName,
  async (job) => {
    const data = job.data as EnqueueRequestBody;
    await executeOnBackend(data);
  },
  {
    connection,
    concurrency: Number(process.env.WORKER_CONCURRENCY ?? "2"),
  },
);

worker.on("failed", (job, error) => {
  console.error(`Job ${job?.id} failed`, error);
});

const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_request, response) => {
  response.json({ status: "ok", queue: queueName });
});

app.post("/enqueue", async (request, response) => {
  const body = request.body as EnqueueRequestBody;
  const bullJob = await tailoringQueue.add(body.name, body, {
    jobId: body.jobId,
    removeOnComplete: 1000,
    removeOnFail: 5000,
    attempts: 3,
    backoff: {
      type: "exponential",
      delay: 3000,
    },
  });
  response.json({ queueJobId: bullJob.id, status: "queued" });
});

app.listen(queuePort, () => {
  console.log(`ResumeForge queue service listening on :${queuePort}`);
});
