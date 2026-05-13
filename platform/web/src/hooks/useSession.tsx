import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { fetchCurrentUser, logoutProductionSession, refreshProductionSession } from "@/api/auth";
import { getAuthMode, isDevAuthEnabled } from "@/api/config";
import { AuthSession } from "@/types";

const STORAGE_KEY = "plantlab.web.session";

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
  authMode: "production" | "dev";
  isHydrated: boolean;
  authError: string | null;
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
  const [isHydrated, setIsHydrated] = useState(authMode === "dev");
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    if (authMode !== "production") {
      setIsHydrated(true);
      return;
    }

    let cancelled = false;
    refreshProductionSession()
      .then((nextSession) => {
        if (cancelled) {
          return;
        }
        setSession(nextSession);
        setAuthError(null);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setSession(null);
        if (new URLSearchParams(window.location.search).get("auth") === "complete") {
          setAuthError(error instanceof Error ? error.message : "Unable to restore Google session.");
        } else {
          setAuthError(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsHydrated(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authMode]);

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
      signIn: (nextSession) => {
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
        window.localStorage.removeItem(STORAGE_KEY);
        setSession(null);
        setAuthError(null);
      },
    }),
    [authError, authMode, isHydrated, session],
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
