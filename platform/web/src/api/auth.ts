import { apiRequest, shouldUseMockFallback } from "./client";
import { getApiBaseUrl } from "./config";
import { AuthSession, CurrentUserProfile } from "@/types";

type LoginInput = {
  email: string;
  password: string;
};

type ApiCurrentUser = {
  authenticated: boolean;
  user: {
    id: number;
    email: string;
    name?: string | null;
    avatar_url?: string | null;
    is_admin?: boolean;
  } | null;
};

type ApiLoginResponse = {
  token: string;
  email: string;
  mode: "api";
  user?: {
    is_admin?: boolean;
  };
};

type ApiRefreshResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  expires_at: string;
  mode: "standalone";
  user: {
    id: number;
    email: string;
    name?: string | null;
    avatar_url?: string | null;
    is_admin?: boolean;
  };
};

export async function loginWithBackendFallback({ email, password }: LoginInput): Promise<AuthSession> {
  try {
    const payload = await apiRequest<ApiLoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    return {
      token: payload.token,
      email: payload.email,
      mode: payload.mode,
      isAdmin: payload.user?.is_admin ?? false,
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
    return {
      token: `mock-token:${email}`,
      email,
      mode: "mock",
    };
  }
}

export async function fetchCurrentUser(token?: string): Promise<ApiCurrentUser> {
  return apiRequest<ApiCurrentUser>("/api/me", {}, token);
}

export async function fetchCurrentUserProfile(
  token?: string,
  fallbackEmail?: string,
): Promise<{ profile: CurrentUserProfile; usedMock: boolean }> {
  try {
    const payload = await fetchCurrentUser(token);
    return {
      usedMock: false,
      profile: {
        authenticated: payload.authenticated,
        id: payload.user?.id !== undefined ? String(payload.user.id) : undefined,
        email: payload.user?.email ?? fallbackEmail ?? "Unknown account",
        name: payload.user?.name ?? undefined,
        avatarUrl: payload.user?.avatar_url ?? undefined,
        isAdmin: payload.user?.is_admin ?? false,
      },
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    return {
      usedMock: true,
      profile: {
        authenticated: Boolean(token),
        email: fallbackEmail ?? "mock@example.com",
        name: "Mock support user",
        isAdmin: true,
      },
    };
  }
}

export async function refreshProductionSession(): Promise<AuthSession> {
  const payload = await apiRequest<ApiRefreshResponse>("/api/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
  return {
    token: payload.access_token,
    email: payload.user.email,
    mode: "production",
    expiresAt: payload.expires_at,
    isAdmin: payload.user.is_admin,
  };
}

export async function logoutProductionSession(): Promise<void> {
  await apiRequest<{ ok: boolean }>("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
}

export function getGoogleAuthStartUrl(returnTo: string = `${window.location.origin}/login?auth=complete`): string {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    throw new Error("API base URL is not configured. Set VITE_API_BASE_URL before using Google sign-in.");
  }
  const params = new URLSearchParams({ client: "web", return_to: returnTo });
  return `${baseUrl}/api/auth/google/start?${params.toString()}`;
}
