import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { RangeKey } from "@/components/ReadingTrendSection";
import { getDeviceDashboard, getDeviceTimelapse, sendDeviceCommand } from "@/api/devices";
import { CameraRole, DeviceCommand, DeviceDashboard } from "@/types";
import { useSession } from "@/hooks/useSession";

type OptimisticLightState = {
  lightOn: boolean;
  lightIntensityPercent?: number;
};

type CommandOptions = {
  intensityPercent?: number;
  cameraRole?: CameraRole | "all";
  cameraNodeId?: string;
  ambientColor?: { r: number; g: number; b: number };
  ambientBrightness?: number;
};

export function useDeviceDashboard(deviceId: string, options?: { autoRefresh?: boolean }) {
  const autoRefreshMs = 10000;
  const timelapseRefreshMs = 5 * 60 * 1000;
  const commandRefreshMs = 1000;
  const captureRefreshAttempts = 16;
  const captureRefreshDelayMs = 500;
  const autoRefreshEnabled = options?.autoRefresh ?? true;
  const { getAccessToken, token } = useSession();
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
  const [optimisticLight, setOptimisticLight] = useState<OptimisticLightState | null>(null);
  const hasLoadedRef = useRef(false);
  const timelapseLoadedRef = useRef(false);
  const lastTimelapseRefreshAtRef = useRef(0);
  const timelapseRequestIdRef = useRef(0);

  const refresh = useCallback(async (options?: { background?: boolean }) => {
    try {
      setError(null);
      if (!options?.background || !hasLoadedRef.current) {
        setIsLoading(true);
      }
      const accessToken = await getAccessToken();
      const result = await getDeviceDashboard(deviceId, selectedRange, accessToken ?? undefined, { includeTimelapse: false });
      let optimisticForRender = optimisticLight;
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
                setCommandTone(null);
                setCommandMessage(null);
                setTrackedCommand(null);
              } else {
                setCommandTone("info");
                setCommandMessage("Image captured. Waiting for gallery refresh.");
              }
            } else {
              setCommandMessage(null);
              setCommandTone(null);
              setTrackedCommand(null);
              if (isLightCommand(trackedCommand.action)) {
                setOptimisticLight(null);
                optimisticForRender = null;
              }
            }
          } else if (matchingCommand.status === "failed") {
            setCommandTone("error");
            setCommandMessage(matchingCommand.detail ?? `${friendlyCommandLabel(trackedCommand.action)} failed.`);
            setTrackedCommand(null);
            if (isLightCommand(trackedCommand.action)) {
              setOptimisticLight(null);
              optimisticForRender = null;
            }
          } else if (trackedCommand.action === "capture_image") {
            setCommandTone("info");
            setCommandMessage(
              matchingCommand.status === "in_progress"
                ? matchingCommand.detail ?? "Waiting for camera upload."
                : "Waiting for camera.",
            );
          }
        } else if (
          !result.dashboard.recentCommands.some(
            (command) => command.action === trackedCommand.action && ["pending", "sent", "in_progress"].includes(command.status),
          )
        ) {
          if (trackedCommand.action === "capture_image") {
            if (hasNewCaptureImage) {
              setCommandMessage(null);
              setCommandTone(null);
              setTrackedCommand(null);
            } else {
              setCommandMessage("Image captured. Waiting for gallery refresh.");
              setCommandTone("info");
            }
          } else {
            setCommandMessage(null);
            setCommandTone(null);
            setTrackedCommand(null);
            if (isLightCommand(trackedCommand.action)) {
              setOptimisticLight(null);
              optimisticForRender = null;
            }
          }
        }
      }
      setDashboard((current) => {
        const preservedTimelapse =
          current && current.device.id === result.dashboard.device.id ? current.timelapse : undefined;
        return applyOptimisticLight(
          {
            ...result.dashboard,
            timelapse: result.dashboard.timelapse ?? preservedTimelapse,
          },
          optimisticForRender,
        );
      });
      hasLoadedRef.current = true;
      const now = Date.now();
      const shouldRefreshTimelapse =
        !options?.background ||
        !timelapseLoadedRef.current ||
        now - lastTimelapseRefreshAtRef.current >= timelapseRefreshMs;
      if (shouldRefreshTimelapse && !result.usedMock) {
        lastTimelapseRefreshAtRef.current = now;
        const requestId = ++timelapseRequestIdRef.current;
        void getDeviceTimelapse(deviceId, accessToken ?? undefined)
          .then((timelapse) => {
            if (requestId !== timelapseRequestIdRef.current) {
              return;
            }
            setDashboard((current) =>
              current && current.device.id === result.dashboard.device.id
                ? {
                    ...current,
                    timelapse,
                  }
                : current,
            );
            timelapseLoadedRef.current = true;
          })
          .catch(() => {
            // Timelapse is useful, but it should not block the primary dashboard.
          });
      }
    } catch (err) {
      setUsedMock(false);
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [deviceId, getAccessToken, optimisticLight, selectedRange, token, trackedCommand]);

  const refreshIntervalMs = trackedCommand ? commandRefreshMs : autoRefreshMs;

  useEffect(() => {
    if (!deviceId) {
      return;
    }
    hasLoadedRef.current = false;
    timelapseLoadedRef.current = false;
    lastTimelapseRefreshAtRef.current = 0;
    timelapseRequestIdRef.current += 1;
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
    async (action: DeviceCommand["action"], options?: CommandOptions) => {
      if (isActionBlocked(action)) {
        setCommandTone("info");
        setCommandMessage(`${friendlyCommandLabel(action)} is already in progress for the device.`);
        return;
      }
      setActiveCommandAction(action);
      setIsCommandRunning(true);
      const nextOptimisticLight = optimisticLightForCommand(action, options, dashboard);
      if (nextOptimisticLight) {
        setOptimisticLight(nextOptimisticLight);
        setDashboard((current) => (current ? applyOptimisticLight(current, nextOptimisticLight) : current));
      }
      setError(null);
      setCommandMessage(null);
      setCommandTone(null);
      let accessToken: string | null = null;
      try {
        accessToken = await getAccessToken();
        const result = await sendDeviceCommand(deviceId, action, options, accessToken ?? undefined);
        if (result.usedMock) {
          if (action !== "capture_image") {
            setCommandMessage(`Simulated ${friendlyCommandLabel(action)} in mock mode.`);
            setCommandTone("success");
          }
        } else if (isAmbientLedBeltCommand(action)) {
          setCommandMessage(`${friendlyCommandLabel(action)} queued.`);
          setCommandTone("info");
        }
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
        if (!result.usedMock && action === "capture_image") {
          const baselineImageId = dashboard?.recentImages[0]?.id ?? dashboard?.device.latestImage?.id ?? null;
          const refreshed = await waitForCaptureDashboardRefresh({
            deviceId,
            selectedRange,
            token: accessToken ?? undefined,
            commandId: result.command.id,
            baselineImageId,
            attempts: captureRefreshAttempts,
            delayMs: captureRefreshDelayMs,
          });
          setDashboard(refreshed.dashboard);
          setUsedMock(refreshed.usedMock);
          setLastUpdatedAt(new Date().toISOString());
          const latestImageId = refreshed.dashboard.recentImages[0]?.id ?? refreshed.dashboard.device.latestImage?.id ?? null;
          const matchingCommand = refreshed.dashboard.recentCommands.find((command) => command.id === result.command.id);
          if (latestImageId !== null && latestImageId !== baselineImageId) {
            setTrackedCommand(null);
            setCommandTone(null);
            setCommandMessage(null);
          } else if (matchingCommand?.status === "failed") {
            setTrackedCommand(null);
            setCommandTone("error");
            setCommandMessage(matchingCommand.detail ?? "Capture image failed.");
          } else {
            setCommandTone("info");
            setCommandMessage("Image captured. Waiting for gallery refresh.");
          }
        }
      } catch (err) {
        setTrackedCommand(null);
        if (nextOptimisticLight) {
          setOptimisticLight(null);
          try {
            const refreshed = await getDeviceDashboard(deviceId, selectedRange, accessToken ?? undefined, { includeTimelapse: false });
            setDashboard(refreshed.dashboard);
            setUsedMock(refreshed.usedMock);
            setLastUpdatedAt(new Date().toISOString());
          } catch {
            // Keep the original command failure visible.
          }
        }
        setCommandTone("error");
        setError(err instanceof Error ? err.message : "Unable to send command.");
        setCommandMessage(null);
      } finally {
        setIsCommandRunning(false);
        setActiveCommandAction(null);
      }
    },
    [dashboard, deviceId, getAccessToken, isActionBlocked, selectedRange, token],
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

async function waitForCaptureDashboardRefresh({
  deviceId,
  selectedRange,
  token,
  commandId,
  baselineImageId,
  attempts,
  delayMs,
}: {
  deviceId: string;
  selectedRange: RangeKey;
  token?: string;
  commandId: string;
  baselineImageId: string | null;
  attempts: number;
  delayMs: number;
}): Promise<{ dashboard: DeviceDashboard; usedMock: boolean }> {
  let lastResult: { dashboard: DeviceDashboard; usedMock: boolean } | null = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) {
      await delay(delayMs);
    }
    const result = await getDeviceDashboard(deviceId, selectedRange, token, { includeTimelapse: false });
    lastResult = result;
    const latestImageId = result.dashboard.recentImages[0]?.id ?? result.dashboard.device.latestImage?.id ?? null;
    if (latestImageId !== null && latestImageId !== baselineImageId) {
      return result;
    }
    const matchingCommand = result.dashboard.recentCommands.find((command) => command.id === commandId);
    if (matchingCommand?.status === "failed") {
      return result;
    }
  }
  return lastResult ?? getDeviceDashboard(deviceId, selectedRange, token, { includeTimelapse: false });
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isLightCommand(action: DeviceCommand["action"]): boolean {
  return (
    action === "light_on" ||
    action === "light_off" ||
    action === "light_intensity" ||
    action === "light_red_intensity" ||
    action === "light_white_intensity"
  );
}

function isAmbientLedBeltCommand(action: DeviceCommand["action"]): boolean {
  return action === "ambient_belt_color" || action === "ambient_belt_off";
}

function optimisticLightForCommand(
  action: DeviceCommand["action"],
  options: { intensityPercent?: number } | undefined,
  dashboard: DeviceDashboard | null,
): OptimisticLightState | null {
  const currentIntensity =
    dashboard?.device.currentLightIntensityPercent ??
    dashboard?.device.latestReading?.lightIntensityPercent ??
    (dashboard?.device.currentLightOn ?? dashboard?.device.latestReading?.lightOn ? 100 : 0);
  switch (action) {
    case "light_on":
      return { lightOn: true, lightIntensityPercent: Math.max(1, currentIntensity || 100) };
    case "light_off":
      return { lightOn: false, lightIntensityPercent: 0 };
    case "light_intensity": {
      const lightIntensityPercent = clampPercent(options?.intensityPercent ?? 0);
      return { lightOn: lightIntensityPercent > 0, lightIntensityPercent };
    }
    default:
      return null;
  }
}

function applyOptimisticLight(dashboard: DeviceDashboard, optimisticLight: OptimisticLightState | null): DeviceDashboard {
  if (!optimisticLight) {
    return dashboard;
  }
  return {
    ...dashboard,
    device: {
      ...dashboard.device,
      currentLightOn: optimisticLight.lightOn,
      currentLightIntensityPercent: optimisticLight.lightIntensityPercent,
      latestReading: dashboard.device.latestReading
        ? {
            ...dashboard.device.latestReading,
            lightOn: optimisticLight.lightOn,
            lightIntensityPercent: optimisticLight.lightIntensityPercent,
          }
        : dashboard.device.latestReading,
    },
  };
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function friendlyCommandLabel(action: DeviceCommand["action"]): string {
  switch (action) {
    case "light_on":
      return "Grow LED on";
    case "light_off":
      return "Grow LED off";
    case "light_intensity":
      return "Grow LED brightness";
    case "light_red_intensity":
      return "Grow LED red channel";
    case "light_white_intensity":
      return "Grow LED white channel";
    case "ambient_belt_color":
      return "Ambient LED belt color";
    case "ambient_belt_off":
      return "Ambient LED belt off";
    case "pump_run":
      return "Legacy command";
    case "capture_image":
      return "Capture image";
  }
}
