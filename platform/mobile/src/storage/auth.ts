import AsyncStorage from "@react-native-async-storage/async-storage";

import { AuthSession } from "@/types";

const AUTH_SESSION_KEY = "plantlab.auth.session";

export async function loadAuthSession(): Promise<AuthSession | null> {
  const raw = await AsyncStorage.getItem(AUTH_SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export async function saveAuthSession(session: AuthSession): Promise<void> {
  if (session.mode === "production" && !session.isDemo) {
    await AsyncStorage.removeItem(AUTH_SESSION_KEY);
    return;
  }
  await AsyncStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

export async function clearAuthSession(): Promise<void> {
  await AsyncStorage.removeItem(AUTH_SESSION_KEY);
}
