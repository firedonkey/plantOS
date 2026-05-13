import { useCallback, useEffect, useRef, useState } from "react";

import { listDevices } from "@/api/devices";
import { Device } from "@/types";
import { useSession } from "@/hooks/useSession";

export function useDevices() {
  const autoRefreshMs = 10000;
  const { token } = useSession();
  const [devices, setDevices] = useState<Device[]>([]);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const hasLoadedRef = useRef(false);

  const refresh = useCallback(async (options?: { background?: boolean }) => {
    try {
      setError(null);
      if (!options?.background || !hasLoadedRef.current) {
        setIsLoading(true);
      }
      const result = await listDevices(token ?? undefined);
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
  }, [token]);

  useEffect(() => {
    hasLoadedRef.current = false;
    void refresh();
    const intervalId = setInterval(() => {
      void refresh({ background: true });
    }, autoRefreshMs);
    return () => {
      clearInterval(intervalId);
    };
  }, [refresh]);

  return {
    devices,
    usedMock,
    isLoading,
    error,
    refresh,
    lastUpdatedAt,
  };
}
