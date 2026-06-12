import { useCallback, useEffect, useRef, useState } from "react";

import { listDevices } from "@/api/devices";
import { Device } from "@/types";
import { useSession } from "@/hooks/useSession";

export function useDevices() {
  const autoRefreshMs = 10000;
  const { getAccessToken, token } = useSession();
  const [devices, setDevices] = useState<Device[]>([]);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const hasLoadedRef = useRef(false);

  const refresh = useCallback(async (options?: { background?: boolean }) => {
    if (!options?.background || !hasLoadedRef.current) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const accessToken = await getAccessToken();
      const result = await listDevices(accessToken ?? undefined);
      setDevices(result.devices);
      setUsedMock(result.usedMock);
      setLastUpdatedAt(new Date().toISOString());
      hasLoadedRef.current = true;
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load devices.");
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken, token]);

  useEffect(() => {
    hasLoadedRef.current = false;
    void refresh();
    const intervalId = window.setInterval(() => {
      void refresh({ background: true });
    }, autoRefreshMs);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [refresh]);

  return { devices, usedMock, isLoading, error, refresh, lastUpdatedAt };
}
