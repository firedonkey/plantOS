import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { getSetupStatus } from "@/api/devices";
import { useSession } from "@/hooks/useSession";

export function SetupFinishingScreen() {
  const { getAccessToken, token } = useSession();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const deviceName = searchParams.get("device_name") ?? "";
  const location = searchParams.get("location") ?? "";
  const expectImage = !["0", "false", "no"].includes((searchParams.get("expect_image") ?? "1").toLowerCase());
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const [status, setStatus] = useState<{
    ready: boolean;
    deviceFound: boolean;
    hasReading: boolean;
    hasImage: boolean;
    expectImage: boolean;
    deviceId?: string;
    redirectPath?: string;
  } | null>(null);

  useEffect(() => {
    if (!deviceName) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const refresh = async (background = false) => {
      setError(null);
      if (background) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      try {
        const accessToken = await getAccessToken();
        const result = await getSetupStatus(
          {
            deviceName,
            location: location || undefined,
            expectImage,
          },
          accessToken ?? undefined,
        );
        if (cancelled) {
          return;
        }
        setUsedMock(result.usedMock);
        setStatus(result.status);
        setLastCheckedAt(new Date().toISOString());
        setPollCount((count) => count + 1);
        if (result.status.ready && result.status.deviceId) {
          navigate(result.status.redirectPath ?? `/devices/${result.status.deviceId}?setup=complete`, { replace: true });
          return;
        }
      } catch (err) {
        if (!cancelled) {
          setUsedMock(false);
          setError(err instanceof Error ? err.message : "Unable to check setup status.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
          setIsRefreshing(false);
          timeoutId = window.setTimeout(() => {
            void refresh(true);
          }, 3000);
        }
      }
    };

    void refresh();

    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [deviceName, expectImage, getAccessToken, location, navigate, token]);

  const waitingReason = status
    ? !status.deviceFound
      ? "We are still waiting for the device registration to finish. Keep the PlantLab setup page open until the ESP32 confirms it joined your home Wi-Fi."
      : !status.hasReading
        ? "The device is in your account, but it has not posted its first reading yet. This usually means it is still reconnecting to Wi-Fi or waiting for its first sensor loop."
        : status.expectImage && !status.hasImage
          ? "The main board is online. We are waiting for the camera node to register and upload its first image before opening the dashboard."
          : "Everything looks ready. Redirecting to the dashboard now."
    : "Checking the latest setup status.";

  if (!deviceName) {
    return (
      <section className="page-section">
        <div className="empty-state">
          <h3>Setup details missing</h3>
          <p className="subtitle">Use the mobile app to add devices, then return here to monitor them on the web dashboard.</p>
          <Link className="text-link" to="/devices">
            Back to devices
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">SETUP</div>
          <h2>Finishing setup for {deviceName}</h2>
          <p className="subtitle">
            We’re waiting for the new PlantLab to appear, send its first reading, and{expectImage ? " upload its first image." : " finish reconnecting."}
          </p>
          <p className="meta-text">
            {lastCheckedAt ? `Last checked ${new Date(lastCheckedAt).toLocaleTimeString()}` : "Waiting for the first status check."}
          </p>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" disabled={isLoading || isRefreshing} onClick={() => window.location.reload()}>
            {isLoading || isRefreshing ? "Checking..." : "Check again"}
          </button>
        </div>
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && !status ? <p className="status-banner">Checking setup progress…</p> : null}
      {status ? (
        <p className={`status-banner ${status.ready ? "status-banner-success" : "status-banner-info"}`}>
          {waitingReason}
        </p>
      ) : null}

      <div className="card stack-form">
        <div className={`status-step ${status?.deviceFound ? "status-step-complete" : ""}`}>
          <strong>Device connected</strong>
          <span>{status?.deviceFound ? "We found the new device in your account." : "Waiting for the new device to appear in your account."}</span>
        </div>
        <div className={`status-step ${status?.hasReading ? "status-step-complete" : ""}`}>
          <strong>First sensor update</strong>
          <span>{status?.hasReading ? "The device sent its first reading." : "Waiting for the first reading from the device."}</span>
        </div>
        <div className={`status-step ${!status?.expectImage || status?.hasImage ? "status-step-complete" : ""}`}>
          <strong>First photo uploaded</strong>
          <span>
            {!status?.expectImage
              ? "This setup does not require an image before opening the dashboard."
              : status?.hasImage
                ? "The first camera image arrived."
                : "Waiting for the first camera image."}
          </span>
        </div>
        <div className="setup-status-footer">
          <span>{isRefreshing ? "Polling again..." : "The page checks automatically every few seconds."}</span>
          <span>{pollCount > 0 ? `${pollCount} check${pollCount === 1 ? "" : "s"} completed` : "No checks completed yet."}</span>
        </div>
      </div>

      <div className="card stack-form">
        <h3>Troubleshooting</h3>
        <div className="setup-help-grid">
          <div className="setup-help-item">
            <strong>Setup page was slow to open</strong>
            <span>After joining <strong>PlantLab-Setup</strong>, your laptop may take 20-30 seconds to switch fully onto the local ESP32 access point. If the page says it cannot be reached, stay on the Wi-Fi and try again once the network settles.</span>
          </div>
          <div className="setup-help-item">
            <strong>Device not found yet</strong>
            <span>Keep the browser on the ESP32 setup page until it says the device is connecting, then come back here. The device is only added to your account after registration succeeds.</span>
          </div>
          <div className="setup-help-item">
            <strong>Waiting for the first image</strong>
            <span>If the master board is online but the photo step is still pending, check that the camera node is powered, flashed, and responding to the master board.</span>
          </div>
        </div>
      </div>
    </section>
  );
}
