import { getApiBaseUrl } from "./config";

export class ApiError extends Error {
  status: number | null;
  code: string | null;
  detail: string | null;
  details: Record<string, unknown> | null;
  isNetworkError: boolean;

  constructor(
    message: string,
    {
      status = null,
      code = null,
      detail = null,
      details = null,
      isNetworkError = false,
    }: {
      status?: number | null;
      code?: string | null;
      detail?: string | null;
      details?: Record<string, unknown> | null;
      isNetworkError?: boolean;
    } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.details = details;
    this.isNetworkError = isNetworkError;
  }
}

export function shouldUseMockFallback(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.isNetworkError || error.status === null;
  }
  return false;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    throw new ApiError("API base URL is not configured.", {
      isNetworkError: true,
    });
  }

  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    throw new ApiError(error instanceof Error ? error.message : "Network request failed.", {
      isNetworkError: true,
    });
  }

  if (!response.ok) {
    let detail: string | null = null;
    let code: string | null = null;
    let details: Record<string, unknown> | null = null;
    try {
      const payload = (await response.json()) as {
        detail?: string;
        error?: {
          code?: string;
          message?: string;
          details?: Record<string, unknown>;
        };
      };
      if (payload.error && typeof payload.error.message === "string") {
        detail = payload.error.message;
        code = typeof payload.error.code === "string" ? payload.error.code : null;
        details = payload.error.details ?? null;
      } else {
        detail = typeof payload.detail === "string" ? payload.detail : null;
      }
    } catch {
      detail = null;
    }
    throw new ApiError(detail ?? `API request failed: ${response.status}`, {
      status: response.status,
      code,
      detail,
      details,
    });
  }

  return (await response.json()) as T;
}
