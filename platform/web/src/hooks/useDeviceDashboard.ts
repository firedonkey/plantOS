import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { RangeKey } from "@/components/ReadingTrendSection";
import { getDeviceDashboard, sendDeviceCommand } from "@/api/devices";
import { DeviceCommand, DeviceDashboard } from "@/types";
import { useSession } from "@/hooks/useSession";

export function useDeviceDashboard(deviceId: string, options?: { autoRefresh?: boolean }) {
  const autoRefreshMs = 10000;
  const captureRefreshMs = 1000;
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
  const [trackedCommand, setTrackedCommand] = useState<{
    id: string;
    action: DeviceCommand["action"];
    baselineImageId?: string | null;
  } | null>(null);
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
      if (trackedCommand && !result.usedMock) {
        const latestImageId = result.dashboard.recentImages[0]?.id ?? result.dashboard.device.latestImage?.id ?? null;
        const hasNewCaptureImage =
          trackedCommand.action === "capture_image" &&
          latestImageId !== null &&
          latestImageId !== trackedCommand.baselineImageId;
        const matchingCommand = result.dashboard.recentCommands.find((command) => command.id === trackedCommand.id);
        if (matchingCommand) {
          if (matchingCommand.status === "completed") {
            if (trackedCommand.action === "capture_image") {
              if (hasNewCaptureImage) {
                setCommandTone("success");
                setCommandMessage(matchingCommand.detail ?? "Image captured and uploaded.");
                setTrackedCommand(null);
              } else {
                setCommandTone("info");
                setCommandMessage("Image captured. Waiting for gallery refresh.");
              }
            } else {
              setCommandMessage(null);
              setCommandTone(null);
              setTrackedCommand(null);
            }
          } else if (matchingCommand.status === "failed") {
            setCommandTone("error");
            setCommandMessage(matchingCommand.detail ?? `${friendlyCommandLabel(trackedCommand.action)} failed.`);
            setTrackedCommand(null);
          } else if (trackedCommand.action === "capture_image") {
            setCommandTone("info");
            setCommandMessage(
              matchingCommand.status === "in_progress"
                ? matchingCommand.detail ?? "Waiting for camera upload."
                : "Capture request queued for the camera.",
            );
          }
        } else if (
          !result.dashboard.recentCommands.some(
            (command) => command.action === trackedCommand.action && ["pending", "sent", "in_progress"].includes(command.status),
          )
        ) {
          if (trackedCommand.action === "capture_image") {
            if (hasNewCaptureImage) {
              setCommandMessage("Image capture completed.");
              setCommandTone("success");
              setTrackedCommand(null);
            } else {
              setCommandMessage("Image captured. Waiting for gallery refresh.");
              setCommandTone("info");
            }
          } else {
            setCommandMessage(null);
            setCommandTone(null);
            setTrackedCommand(null);
          }
        }
      }
      hasLoadedRef.current = true;
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [deviceId, selectedRange, token, trackedCommand]);

  const refreshIntervalMs = trackedCommand?.action === "capture_image" ? captureRefreshMs : autoRefreshMs;

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
    }, refreshIntervalMs);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [autoRefreshEnabled, deviceId, refresh, refreshIntervalMs]);

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
        setCommandMessage(
          result.usedMock
            ? `Simulated ${friendlyCommandLabel(action)} in mock mode.`
            : `${friendlyCommandLabel(action)} queued for the device.`,
        );
        setCommandTone(result.usedMock ? "success" : "info");
        setTrackedCommand(
          result.usedMock
            ? null
            : {
                id: result.command.id,
                action,
                baselineImageId:
                  action === "capture_image"
                    ? dashboard?.recentImages[0]?.id ?? dashboard?.device.latestImage?.id ?? null
                    : undefined,
              },
        );
        if (!result.usedMock) {
          const refreshed = await getDeviceDashboard(deviceId, selectedRange, token ?? undefined);
          setDashboard(refreshed.dashboard);
          setUsedMock(refreshed.usedMock);
          setLastUpdatedAt(new Date().toISOString());
        }
      } catch (err) {
        setTrackedCommand(null);
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
