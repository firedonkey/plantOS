import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { deleteDevice } from "@/api/devices";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { useSession } from "@/hooks/useSession";

export function RemoveDeviceScreen() {
  const { deviceId = "" } = useParams();
  const navigate = useNavigate();
  const { token } = useSession();
  const { dashboard, usedMock: dashboardUsedMock, isLoading, error } = useDeviceDashboard(deviceId, { autoRefresh: false });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (!deviceId) {
    return <p className="error-text">Missing device id.</p>;
  }

  const deviceName = dashboard?.device.name ?? `Device ${deviceId}`;

  const onDelete = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const result = await deleteDevice(deviceId, token ?? undefined);
      navigate("/devices", {
        replace: true,
        state: {
          flashMessage: result.usedMock
            ? `Mock mode simulated removal for ${deviceName}.`
            : `${deviceName} was removed.`,
          flashTone: result.usedMock ? "info" : "success",
        },
      });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Unable to remove device.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">DEVICE SETTINGS</div>
          <h2>Remove device</h2>
          <p className="subtitle">This confirms the standalone remove-device flow while keeping the legacy backend-rendered flow available for comparison.</p>
        </div>
      </div>

      {dashboardUsedMock ? <p className="chip chip-mock">Mock data mode</p> : null}
      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {submitError ? <p className="status-banner status-banner-error">{submitError}</p> : null}

      <div className="card stack-form">
        <h3>Confirm removal</h3>
        <p className="subtitle">
          {isLoading ? "Loading device details…" : `You are about to remove ${deviceName}.`}
        </p>
        <div className="button-row">
          <button className="danger-button" disabled={isSubmitting || isLoading} onClick={onDelete}>
            {isSubmitting ? "Removing..." : "Yes, remove device"}
          </button>
          <Link className="secondary-button" to={`/devices/${deviceId}`}>
            Cancel
          </Link>
        </div>
      </div>
    </section>
  );
}
