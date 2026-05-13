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
    if (!options?.background || devices.length === 0) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const result = await listDevices(token ?? undefined);
      setDevices(result.devices);
      setUsedMock(result.usedMock);
      setLastUpdatedAt(new Date().toISOString());
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load devices.");
    } finally {
      setIsLoading(false);
    }
  }, [devices.length, token]);

  useEffect(() => {
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
