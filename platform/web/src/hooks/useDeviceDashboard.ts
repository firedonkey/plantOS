import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/api/client";
import { getDeviceDashboard, sendDeviceCommand } from "@/api/devices";
import { DeviceCommand, DeviceDashboard } from "@/types";
import { useSession } from "@/hooks/useSession";

export function useDeviceDashboard(deviceId: string) {
  const { token } = useSession();
  const [dashboard, setDashboard] = useState<DeviceDashboard | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commandMessage, setCommandMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getDeviceDashboard(deviceId, token ?? undefined);
      setDashboard(result.dashboard);
      setUsedMock(result.usedMock);
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [deviceId, token]);

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    refresh();
  }, [deviceId, refresh]);

  const runCommand = useCallback(
    async (action: DeviceCommand["action"]) => {
      setError(null);
      setCommandMessage(null);
      try {
        const result = await sendDeviceCommand(deviceId, action, token ?? undefined);
        setCommandMessage(result.usedMock ? `Mock command: ${action}` : `Sent command: ${action}`);
      } catch (err) {
        if (err instanceof ApiError && action === "capture_image" && err.status === 501) {
          setError("Capture command is not supported by the backend yet.");
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to send command.");
      }
    },
    [deviceId, token],
  );

  const imageAuthHeaders = useMemo(() => {
    if (!token) {
      return undefined;
    }
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  return { dashboard, usedMock, isLoading, error, commandMessage, refresh, runCommand, imageAuthHeaders };
}
