import { apiRequest, shouldUseMockFallback } from "./client";
import { AuthSession } from "@/types";

type LoginInput = {
  email: string;
  password: string;
};

type ApiLoginResponse = {
  token: string;
  email: string;
  mode: "api";
};

export async function loginWithBackendFallback({ email, password }: LoginInput): Promise<AuthSession> {
  try {
    const session = await apiRequest<ApiLoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    return session;
  } catch (error) {
    if (!shouldUseMockFallback(error)) {
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
    return {
      token: `mock-token:${email}`,
      email,
      mode: "mock",
    };
  }
}
