import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { fetchCurrentUser, logoutProductionSession, refreshProductionSession } from "@/api/auth";
import { getAuthMode, isDevAuthEnabled } from "@/api/config";
import { AuthSession } from "@/types";

const STORAGE_KEY = "plantlab.web.session";
const PRODUCTION_REFRESH_SKEW_MS = 60 * 1000;
const MIN_PRODUCTION_REFRESH_DELAY_MS = 5 * 1000;

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
  authMode: "production" | "dev";
  isHydrated: boolean;
  authError: string | null;
  getAccessToken: () => Promise<string | null>;
  signIn: (session: AuthSession) => void;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: PropsWithChildren) {
  const authMode = getAuthMode();
  const [session, setSession] = useState<AuthSession | null>(() => {
    if (!isDevAuthEnabled()) {
      return null;
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as AuthSession;
    } catch {
      return null;
    }
  });
  const sessionRef = useRef<AuthSession | null>(session);
  const sessionGenerationRef = useRef(0);
  const refreshPromiseRef = useRef<Promise<AuthSession | null> | null>(null);
  const [isHydrated, setIsHydrated] = useState(authMode === "dev");
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  const clearSession = useCallback((message?: string | null) => {
    sessionGenerationRef.current += 1;
    sessionRef.current = null;
    window.localStorage.removeItem(STORAGE_KEY);
    setSession(null);
    setAuthError(message ?? null);
  }, []);

  const refreshProductionAuth = useCallback(
    async ({ clearOnFailure = false }: { clearOnFailure?: boolean } = {}) => {
      if (authMode !== "production") {
        return sessionRef.current;
      }
      if (refreshPromiseRef.current) {
        return refreshPromiseRef.current;
      }

      const generationAtStart = sessionGenerationRef.current;
      const refreshPromise = refreshProductionSession()
        .then((nextSession) => {
          if (sessionGenerationRef.current === generationAtStart) {
            sessionRef.current = nextSession;
            window.localStorage.removeItem(STORAGE_KEY);
            setSession(nextSession);
            setAuthError(null);
          }
          return nextSession;
        })
        .catch((error) => {
          if (clearOnFailure && sessionGenerationRef.current === generationAtStart) {
            clearSession(normalizeSessionRefreshError(error));
          }
          throw error;
        })
        .finally(() => {
          refreshPromiseRef.current = null;
        });

      refreshPromiseRef.current = refreshPromise;
      return refreshPromise;
    },
    [authMode, clearSession],
  );

  const getAccessToken = useCallback(async () => {
    const currentSession = sessionRef.current;
    if (!currentSession) {
      return null;
    }
    if (currentSession.mode !== "production") {
      return currentSession.token;
    }
    if (!shouldRefreshProductionAuthSession(currentSession)) {
      return currentSession.token;
    }

    try {
      const nextSession = await refreshProductionAuth({ clearOnFailure: true });
      return nextSession?.token ?? null;
    } catch (error) {
      throw new Error(normalizeSessionRefreshError(error));
    }
  }, [refreshProductionAuth]);

  useEffect(() => {
    const authCompleted = new URLSearchParams(window.location.search).get("auth") === "complete";
    if (authMode !== "production" && !authCompleted) {
      setIsHydrated(true);
      return;
    }

    let cancelled = false;
    refreshProductionAuth()
      .then(() => {
        if (cancelled) {
          return;
        }
        if (authCompleted) {
          const cleanUrl = new URL(window.location.href);
          cleanUrl.searchParams.delete("auth");
          window.history.replaceState({}, "", cleanUrl.toString());
        }
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        clearSession(authCompleted ? normalizeSessionRefreshError(error) : null);
      })
      .finally(() => {
        if (!cancelled) {
          setIsHydrated(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authMode, clearSession, refreshProductionAuth]);

  useEffect(() => {
    if (authMode !== "production" || session?.mode !== "production") {
      return;
    }

    const expiresAtMs = getSessionExpiryMs(session);
    const delayMs =
      expiresAtMs === null
        ? MIN_PRODUCTION_REFRESH_DELAY_MS
        : Math.max(expiresAtMs - Date.now() - PRODUCTION_REFRESH_SKEW_MS, MIN_PRODUCTION_REFRESH_DELAY_MS);

    const timeoutId = window.setTimeout(() => {
      void refreshProductionAuth({ clearOnFailure: true }).catch(() => {
        // The failed refresh has already cleared the session state.
      });
    }, delayMs);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [authMode, refreshProductionAuth, session?.expiresAt, session?.mode, session?.token]);

  useEffect(() => {
    if (!session || session.mode !== "api" || !isDevAuthEnabled()) {
      setAuthError(null);
      return;
    }

    let cancelled = false;
    fetchCurrentUser(session.token)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        if (!payload.authenticated) {
          window.localStorage.removeItem(STORAGE_KEY);
          setSession(null);
          setAuthError("Your dev session expired. Please sign in again.");
          return;
        }
        setAuthError(null);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        window.localStorage.removeItem(STORAGE_KEY);
        setSession(null);
        setAuthError(error instanceof Error ? error.message : "Unable to verify session.");
      });

    return () => {
      cancelled = true;
    };
  }, [session]);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      token: session?.token ?? null,
      authMode,
      isHydrated,
      authError,
      getAccessToken,
      signIn: (nextSession) => {
        sessionGenerationRef.current += 1;
        sessionRef.current = nextSession;
        if (nextSession.mode === "api" && isDevAuthEnabled()) {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
        } else {
          window.localStorage.removeItem(STORAGE_KEY);
        }
        setSession(nextSession);
        setAuthError(null);
      },
      signOut: async () => {
        if (session?.mode === "production" || authMode === "production") {
          try {
            await logoutProductionSession();
          } catch {
            // Local state still clears; the next refresh will fail if the backend logout did not complete.
          }
        }
        clearSession(null);
      },
    }),
    [authError, authMode, clearSession, getAccessToken, isHydrated, session],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}

function shouldRefreshProductionAuthSession(session: AuthSession): boolean {
  const expiresAtMs = getSessionExpiryMs(session);
  return expiresAtMs === null || expiresAtMs - Date.now() <= PRODUCTION_REFRESH_SKEW_MS;
}

function getSessionExpiryMs(session: AuthSession): number | null {
  if (!session.expiresAt) {
    return null;
  }
  const expiresAtMs = Date.parse(session.expiresAt);
  return Number.isFinite(expiresAtMs) ? expiresAtMs : null;
}

function normalizeSessionRefreshError(error: unknown): string {
  if (error instanceof Error && error.message && error.message !== "Sign in required.") {
    return error.message;
  }
  return "Your session expired. Please sign in again.";
}
