import { useCallback, useEffect, useState } from "react";

import type { RangeKey } from "@/components/ReadingTrendSection";
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
  const [commandTone, setCommandTone] = useState<"success" | "error" | "info" | null>(null);
  const [isCommandRunning, setIsCommandRunning] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<RangeKey>("24h");

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      const result = await getDeviceDashboard(deviceId, selectedRange, token ?? undefined);
      setDashboard(result.dashboard);
      setUsedMock(result.usedMock);
      setLastUpdatedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [deviceId, selectedRange, token]);

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    refresh();
  }, [deviceId, refresh]);

  const runCommand = useCallback(
    async (action: DeviceCommand["action"]) => {
      if (action === "capture_image") {
        setCommandTone("info");
        setCommandMessage("Image capture is coming later. For now, view the latest image already uploaded by the device.");
        return;
      }
      setIsCommandRunning(true);
      try {
        setError(null);
        setCommandTone(null);
        const result = await sendDeviceCommand(deviceId, action, token ?? undefined);
        setCommandTone("success");
        setCommandMessage(
          result.usedMock
            ? `Simulated ${friendlyCommandLabel(action)} in mock mode.`
            : `${friendlyCommandLabel(action)} queued for the device.`,
        );
        if (!result.usedMock) {
          const refreshed = await getDeviceDashboard(deviceId, selectedRange, token ?? undefined);
          setDashboard(refreshed.dashboard);
          setUsedMock(refreshed.usedMock);
          setLastUpdatedAt(new Date().toISOString());
        }
      } catch (err) {
        setCommandTone("error");
        setCommandMessage(null);
        setError(err instanceof Error ? err.message : "Unable to send command.");
      } finally {
        setIsCommandRunning(false);
      }
    },
    [deviceId, selectedRange, token],
  );

  return {
    dashboard,
    usedMock,
    isLoading,
    error,
    commandMessage,
    commandTone,
    isCommandRunning,
    lastUpdatedAt,
    refresh,
    runCommand,
    selectedRange,
    setSelectedRange,
  };
}

function friendlyCommandLabel(action: DeviceCommand["action"]): string {
  switch (action) {
    case "light_on":
      return "Light on";
    case "light_off":
      return "Light off";
    case "pump_run":
      return "Pump run";
    case "capture_image":
      return "Capture image";
  }
}
