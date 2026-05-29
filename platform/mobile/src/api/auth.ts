import { apiRequest, shouldUseMockFallback } from "./client";
import { getApiBaseUrl } from "./config";
import { AuthSession } from "@/types";

type LoginInput = {
  email: string;
  password: string;
};

type ApiLoginResponse = {
  token: string;
  email: string;
  mode: "api";
  user?: {
    id: number;
    email: string;
    name?: string | null;
    avatar_url?: string | null;
  };
};

type ApiRefreshResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  expires_at: string;
  mode: "standalone";
  refresh_token?: string | null;
  user: {
    id: number;
    email: string;
    name?: string | null;
    avatar_url?: string | null;
  };
};

type AppleLoginInput = {
  identityToken: string;
  email?: string | null;
  fullName?: string | null;
};

export async function loginWithBackendFallback({ email, password }: LoginInput): Promise<AuthSession> {
  try {
    const session = await apiRequest<ApiLoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    return {
      token: session.token,
      email: session.user?.email ?? session.email,
      name: session.user?.name ?? undefined,
      mode: session.mode,
    };
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
    return {
      token: `mock-token:${email}`,
      email,
      name: "Demo User",
      mode: "mock",
    };
  }
}

export async function loginWithAppleIdentityToken(input: AppleLoginInput): Promise<{ session: AuthSession; refreshToken?: string | null }> {
  const payload = await apiRequest<ApiRefreshResponse>("/api/auth/apple/mobile", {
    method: "POST",
    body: JSON.stringify({
      identity_token: input.identityToken,
      email: input.email,
      full_name: input.fullName,
    }),
  });
  return {
    session: {
      token: payload.access_token,
      email: payload.user.email,
      name: payload.user.name ?? undefined,
      mode: "production",
      expiresAt: payload.expires_at,
      refreshToken: payload.refresh_token ?? undefined,
    },
    refreshToken: payload.refresh_token,
  };
}

export async function refreshProductionSession(input: {
  refreshToken?: string;
  handoffCode?: string;
}): Promise<{ session: AuthSession; refreshToken?: string | null }> {
  const payload = await apiRequest<ApiRefreshResponse>("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({
      refresh_token: input.refreshToken,
      handoff_code: input.handoffCode,
    }),
  });
  return {
    session: {
      token: payload.access_token,
      email: payload.user.email,
      name: payload.user.name ?? undefined,
      mode: "production",
      expiresAt: payload.expires_at,
      refreshToken: payload.refresh_token ?? undefined,
    },
    refreshToken: payload.refresh_token,
  };
}

export async function logoutProductionSession(refreshToken?: string): Promise<void> {
  await apiRequest<{ ok: boolean }>("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function deleteAccount(token?: string | null): Promise<void> {
  await apiRequest<{ ok: boolean }>("/api/me", { method: "DELETE" }, token ?? undefined);
}

export function getMobileGoogleAuthStartUrl(returnTo = "plantlab://auth/callback"): string {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    throw new Error("API base URL is not configured. Set EXPO_PUBLIC_API_BASE_URL before using Google sign-in.");
  }
  const params = new URLSearchParams({ client: "mobile", return_to: returnTo });
  return `${baseUrl}/api/auth/google/start?${params.toString()}`;
}
