import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { AuthSession } from "@/types";
import { clearAuthSession, loadAuthSession, saveAuthSession } from "@/storage/auth";

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
  isHydrated: boolean;
  signIn: (nextSession: AuthSession) => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    loadAuthSession()
      .then((stored) => setSession(stored))
      .finally(() => setIsHydrated(true));
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      token: session?.token ?? null,
      isHydrated,
      signIn: async (nextSession) => {
        await saveAuthSession(nextSession);
        setSession(nextSession);
      },
      signOut: async () => {
        await clearAuthSession();
        setSession(null);
      },
    }),
    [isHydrated, session],
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
