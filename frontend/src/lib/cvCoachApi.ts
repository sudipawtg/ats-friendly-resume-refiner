import { API_BASE_URL } from "@/constants";
import { buildTenantHeaders } from "@/lib/tenant";
import type {
  CoachChatMessage,
  CoachChatResponse,
  CVCoachReviewRequest,
  CVCoachReviewResponse,
} from "@/lib/api";

async function coachApiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...buildTenantHeaders(),
        ...options?.headers,
      },
    });
  } catch (error) {
    const isNetworkError =
      error instanceof TypeError ||
      (error instanceof Error && error.message.toLowerCase().includes("failed to fetch"));
    const message = isNetworkError
      ? "Cannot reach the ResumeForge API. The backend may be restarting or a long Preview request was interrupted. Wait a moment, refresh the page, and try again."
      : "Network request failed";
    throw new Error(message);
  }

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchCVCoachReview(
  projectId: string,
  payload: CVCoachReviewRequest = {}
): Promise<CVCoachReviewResponse> {
  return coachApiRequest<CVCoachReviewResponse>(
    `/cvs/${encodeURIComponent(projectId)}/coach/review`,
    {
      method: "POST",
      body: JSON.stringify({
        target_role: payload.target_role ?? "",
        focus: payload.focus ?? "",
      }),
    }
  );
}

export async function sendCoachChatMessage(
  projectId: string,
  payload: {
    message: string;
    history: CoachChatMessage[];
    targetRole?: string;
    focus?: string;
  }
): Promise<CoachChatResponse> {
  return coachApiRequest<CoachChatResponse>(`/cvs/${encodeURIComponent(projectId)}/coach/chat`, {
    method: "POST",
    body: JSON.stringify({
      message: payload.message,
      history: payload.history,
      target_role: payload.targetRole ?? "",
      focus: payload.focus ?? "",
    }),
  });
}
