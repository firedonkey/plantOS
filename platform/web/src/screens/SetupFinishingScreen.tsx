import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { getSetupStatus } from "@/api/devices";
import { useSession } from "@/hooks/useSession";

export function SetupFinishingScreen() {
  const { token } = useSession();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const deviceName = searchParams.get("device_name") ?? "";
  const location = searchParams.get("location") ?? "";
  const expectImage = !["0", "false", "no"].includes((searchParams.get("expect_image") ?? "1").toLowerCase());
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
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

    const refresh = async () => {
      setError(null);
      setIsLoading(true);
      try {
        const result = await getSetupStatus(
          {
            deviceName,
            location: location || undefined,
            expectImage,
          },
          token ?? undefined,
        );
        if (cancelled) {
          return;
        }
        setUsedMock(result.usedMock);
        setStatus(result.status);
        setLastCheckedAt(new Date().toISOString());
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
          timeoutId = window.setTimeout(refresh, 2000);
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
  }, [deviceName, expectImage, location, navigate, token]);

  if (!deviceName) {
    return (
      <section className="page-section">
        <div className="empty-state">
          <h3>Setup details missing</h3>
          <p className="subtitle">Start from the add-device flow so we know which PlantLab to watch during onboarding.</p>
          <Link className="text-link" to="/devices/add">
            Go to add device
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
      </div>

      {usedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && !status ? <p className="status-banner">Checking setup progress…</p> : null}

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
      </div>
    </section>
  );
}
