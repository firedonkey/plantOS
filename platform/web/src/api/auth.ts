import { apiRequest, shouldUseMockFallback } from "./client";
import { AuthSession } from "@/types";

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
  } | null;
};

type ApiLoginResponse = {
  token: string;
  email: string;
  mode: "api";
};

export async function loginWithBackendFallback({ email, password }: LoginInput): Promise<AuthSession> {
  try {
    return await apiRequest<ApiLoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
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
