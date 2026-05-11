import { AuthSession } from "@/types";

type LoginInput = {
  email: string;
  password: string;
};

export async function loginWithPlaceholder({ email }: LoginInput): Promise<AuthSession> {
  await new Promise((resolve) => setTimeout(resolve, 200));
  return {
    token: `mock-token:${email}`,
    email,
    mode: "mock",
  };
}

// TODO: replace this dev-only placeholder login with real standalone web auth.
