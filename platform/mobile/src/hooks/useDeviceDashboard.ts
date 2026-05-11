import { useCallback, useEffect, useState } from "react";

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
    try {
      setError(null);
      setIsLoading(true);
      const result = await getDeviceDashboard(deviceId, token ?? undefined);
      setDashboard(result.dashboard);
      setUsedMock(result.usedMock);
    } catch (err) {
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
      const result = await sendDeviceCommand(deviceId, action, token ?? undefined);
      setCommandMessage(
        result.usedMock
          ? `Command simulated in mock mode: ${action}`
          : `Command sent: ${action}`,
      );
    },
    [deviceId, token],
  );

  return {
    dashboard,
    usedMock,
    isLoading,
    error,
    commandMessage,
    refresh,
    runCommand,
  };
}
