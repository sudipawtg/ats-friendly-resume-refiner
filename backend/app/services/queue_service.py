import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.async_jobs_enabled and bool(self._settings.queue_service_url)

    async def enqueue(
        self,
        queue_name: str,
        job_name: str,
        job_id: str,
        tenant_id: str,
        payload: dict,
    ) -> str | None:
        if not self.enabled:
            return None

        request_body = {
            "queue": queue_name,
            "name": job_name,
            "jobId": job_id,
            "tenantId": tenant_id,
            "payload": payload,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._settings.queue_service_url.rstrip('/')}/enqueue",
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()
            queue_job_id = data.get("queueJobId")
            logger.info("Enqueued %s job %s as queue job %s", job_name, job_id, queue_job_id)
            return queue_job_id
