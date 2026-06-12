import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { logoutProductionSession, refreshProductionSession } from "@/api/auth";
import { getAuthMode, isDevAuthEnabled } from "@/api/config";
import { AuthSession } from "@/types";
import { clearAuthSession, loadAuthSession, saveAuthSession } from "@/storage/auth";

type SessionContextValue = {
  session: AuthSession | null;
  token: string | null;
  authMode: "production" | "dev";
  isHydrated: boolean;
  signIn: (nextSession: AuthSession) => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: PropsWithChildren) {
  const authMode = getAuthMode();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    loadAuthSession()
      .then(async (stored) => {
        if (!stored) {
          return;
        }
        if (stored.mode === "api" && !isDevAuthEnabled()) {
          void clearAuthSession();
          return;
        }
        if (stored.mode === "production" && (!stored.isDemo || !stored.refreshToken)) {
          void clearAuthSession();
          return;
        }
        if (stored.mode === "production" && stored.isDemo && stored.refreshToken) {
          const { session: refreshedSession } = await refreshProductionSession({ refreshToken: stored.refreshToken });
          await saveAuthSession(refreshedSession);
          setSession(refreshedSession);
          return;
        }
        setSession(stored);
      })
      .catch(() => {
        void clearAuthSession();
      })
      .finally(() => setIsHydrated(true));
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      token: session?.token ?? null,
      authMode,
      isHydrated,
      signIn: async (nextSession) => {
        await saveAuthSession(nextSession);
        setSession(nextSession);
      },
      signOut: async () => {
        if (session?.mode === "production") {
          try {
            await logoutProductionSession(session.refreshToken);
          } catch {
            // Mobile production refresh persistence is not enabled until secure storage is added.
          }
        }
        await clearAuthSession();
        setSession(null);
      },
    }),
    [authMode, isHydrated, session],
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
