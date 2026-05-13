import { useCallback, useEffect, useState } from "react";

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

  const refresh = useCallback(async (options?: { background?: boolean }) => {
    try {
      setError(null);
      if (!options?.background || devices.length === 0) {
        setIsLoading(true);
      }
      const result = await listDevices(token ?? undefined);
      setDevices(result.devices);
      setUsedMock(result.usedMock);
      setLastUpdatedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load devices.");
    } finally {
      setIsLoading(false);
    }
  }, [devices.length, token]);

  useEffect(() => {
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
