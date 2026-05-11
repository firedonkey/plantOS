import { createContext, PropsWithChildren, useContext, useMemo, useState } from "react";

import { AuthSession } from "@/types";

const STORAGE_KEY = "plantlab.web.session";

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
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

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      token: session?.token ?? null,
      signIn: (nextSession) => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
        setSession(nextSession);
      },
      signOut: () => {
        window.localStorage.removeItem(STORAGE_KEY);
        setSession(null);
      },
    }),
    [session],
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
