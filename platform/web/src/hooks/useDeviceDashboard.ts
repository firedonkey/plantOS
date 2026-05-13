import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { RangeKey } from "@/components/ReadingTrendSection";
import { getDeviceDashboard, sendDeviceCommand } from "@/api/devices";
import { DeviceCommand, DeviceDashboard } from "@/types";
import { useSession } from "@/hooks/useSession";

export function useDeviceDashboard(deviceId: string, options?: { autoRefresh?: boolean }) {
  const autoRefreshMs = 10000;
  const autoRefreshEnabled = options?.autoRefresh ?? true;
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
  const [activeCommandAction, setActiveCommandAction] = useState<DeviceCommand["action"] | null>(null);
  const [commandBannerAction, setCommandBannerAction] = useState<DeviceCommand["action"] | null>(null);
  const hasLoadedRef = useRef(false);

  const refresh = useCallback(async (options?: { background?: boolean }) => {
    if (!options?.background || !hasLoadedRef.current) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const result = await getDeviceDashboard(deviceId, selectedRange, token ?? undefined);
      setDashboard(result.dashboard);
      setUsedMock(result.usedMock);
      setLastUpdatedAt(new Date().toISOString());
      if (
        commandBannerAction &&
        !result.usedMock &&
        !result.dashboard.recentCommands.some(
          (command) => command.action === commandBannerAction && ["pending", "sent", "in_progress"].includes(command.status),
        )
      ) {
        setCommandBannerAction(null);
        setCommandMessage(null);
        setCommandTone(null);
      }
      hasLoadedRef.current = true;
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [commandBannerAction, deviceId, selectedRange, token]);

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    hasLoadedRef.current = false;
    refresh();
    if (!autoRefreshEnabled) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void refresh({ background: true });
    }, autoRefreshMs);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [autoRefreshEnabled, deviceId, refresh]);

  const isActionBlocked = useCallback(
    (action: DeviceCommand["action"]) => {
      if (isCommandRunning && activeCommandAction === action) {
        return true;
      }
      return Boolean(
        dashboard?.recentCommands.some(
          (command) => command.action === action && ["pending", "sent", "in_progress"].includes(command.status),
        ),
      );
    },
    [activeCommandAction, dashboard?.recentCommands, isCommandRunning],
  );

  const runCommand = useCallback(
    async (action: DeviceCommand["action"]) => {
      if (action === "capture_image") {
        setCommandTone("info");
        setCommandMessage("Image capture is coming later. For now, use the latest image already uploaded by the device.");
        return;
      }
      if (isActionBlocked(action)) {
        setCommandTone("info");
        setCommandMessage(`${friendlyCommandLabel(action)} is already in progress for the device.`);
        return;
      }
      setActiveCommandAction(action);
      setIsCommandRunning(true);
      setError(null);
      setCommandMessage(null);
      setCommandTone(null);
      try {
        const result = await sendDeviceCommand(deviceId, action, token ?? undefined);
        setCommandBannerAction(result.usedMock ? null : action);
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
        setError(err instanceof Error ? err.message : "Unable to send command.");
        setCommandMessage("The command did not go through. Please try again.");
      } finally {
        setIsCommandRunning(false);
        setActiveCommandAction(null);
      }
    },
    [deviceId, isActionBlocked, selectedRange, token],
  );

  const imageAuthHeaders = useMemo(() => {
    if (!token) {
      return undefined;
    }
    return { Authorization: `Bearer ${token}` };
  }, [token]);

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
    imageAuthHeaders,
    selectedRange,
    setSelectedRange,
    isActionBlocked,
    activeCommandAction,
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
