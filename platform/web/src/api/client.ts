import { getApiBaseUrl } from "./config";

export class ApiError extends Error {
  status: number | null;
  detail: string | null;
  isNetworkError: boolean;

  constructor(
    message: string,
    {
      status = null,
      detail = null,
      isNetworkError = false,
    }: { status?: number | null; detail?: string | null; isNetworkError?: boolean } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
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
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = typeof payload.detail === "string" ? payload.detail : null;
    } catch {
      detail = null;
    }
    throw new ApiError(detail ?? `API request failed: ${response.status}`, {
      status: response.status,
      detail,
    });
  }

  return (await response.json()) as T;
}
