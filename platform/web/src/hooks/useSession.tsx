import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { fetchCurrentUser } from "@/api/auth";
import { AuthSession } from "@/types";

const STORAGE_KEY = "plantlab.web.session";

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
  authError: string | null;
  signIn: (session: AuthSession) => void;
  signOut: () => void;
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<AuthSession | null>(() => {
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
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    if (!session || session.mode !== "api") {
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
      authError,
      signIn: (nextSession) => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
        setSession(nextSession);
        setAuthError(null);
      },
      signOut: () => {
        window.localStorage.removeItem(STORAGE_KEY);
        setSession(null);
        setAuthError(null);
      },
    }),
    [authError, session],
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
