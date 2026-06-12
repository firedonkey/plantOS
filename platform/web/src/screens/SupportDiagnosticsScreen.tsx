import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchCurrentUserProfile } from "@/api/auth";
import { getDeviceDiagnostics, listDevices } from "@/api/devices";
import { useSession } from "@/hooks/useSession";
import {
  CurrentUserProfile,
  Device,
  DeviceDiagnosticEvent,
  DeviceDiagnosticSnapshot,
  DeviceDiagnostics,
} from "@/types";

type DeviceDiagnosticRecord = {
  device: Device;
  diagnostics: DeviceDiagnostics | null;
  usedMock: boolean;
  error?: string;
};

export function SupportDiagnosticsScreen() {
  const { authMode, getAccessToken, session, token } = useSession();
  const [account, setAccount] = useState<CurrentUserProfile | null>(null);
  const [records, setRecords] = useState<DeviceDiagnosticRecord[]>([]);
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const [accountResult, devicesResult] = await Promise.all([
        fetchCurrentUserProfile(token ?? undefined, session?.email),
        listDevices(token ?? undefined),
      ]);
      const deviceRecords = await Promise.all(
        devicesResult.devices.map(async (device): Promise<DeviceDiagnosticRecord> => {
          try {
            const diagnosticsResult = await getDeviceDiagnostics(device.id, token ?? undefined, 20);
            return {
              device,
              diagnostics: diagnosticsResult.diagnostics,
              usedMock: diagnosticsResult.usedMock,
            };
          } catch (err) {
            return {
              device,
              diagnostics: null,
              usedMock: false,
              error: err instanceof Error ? err.message : "Unable to load diagnostics for this device.",
            };
          }
        }),
      );

      setAccount(accountResult.profile);
      setRecords(deviceRecords);
      setUsedMock(accountResult.usedMock || devicesResult.usedMock || deviceRecords.some((record) => record.usedMock));
      setLastUpdatedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load support diagnostics.");
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken, session?.email, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const summary = useMemo(() => summarizeRecords(records), [records]);
  const recentEvents = useMemo(() => collectRecentEvents(records), [records]);

  return (
    <section className="page-section support-diagnostics-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">SUPPORT</div>
          <h2>Diagnostics</h2>
          <p className="subtitle">Current account, device status, diagnostic snapshots, and recent backend events.</p>
          <p className="meta-text">
            {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Waiting for first refresh."}
          </p>
        </div>
        <div className="header-actions">
          {usedMock ? <span className="chip chip-mock">Mock mode</span> : null}
          <button className="secondary-button" disabled={isLoading} onClick={() => void refresh()}>
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && !account ? <p className="status-banner">Loading support diagnostics…</p> : null}

      <div className="diagnostics-overview-grid">
        <div className="card diagnostic-summary-card">
          <h3>Account health</h3>
          <div className="detail-grid">
            <DiagnosticRow label="Signed in" value={account ? (account.authenticated ? "Yes" : "No") : "Waiting"} />
            <DiagnosticRow label="Email" value={account?.email ?? "Waiting"} />
            <DiagnosticRow label="Name" value={account?.name ?? "Not reported"} />
            <DiagnosticRow label="User ID" value={account?.id ?? "Not reported"} />
            <DiagnosticRow label="Session" value={`${session?.mode ?? "signed out"} (${authMode})`} />
          </div>
        </div>

        <div className="card diagnostic-summary-card">
          <h3>Fleet health</h3>
          <div className="diagnostic-metric-grid">
            <SummaryMetric label="Devices" value={summary.deviceCount} />
            <SummaryMetric label="Online" value={summary.onlineCount} />
            <SummaryMetric label="Needs review" value={summary.needsReviewCount} />
            <SummaryMetric label="Events" value={summary.eventCount} />
          </div>
        </div>
      </div>

      {records.length === 0 && !isLoading && !error ? (
        <div className="empty-state">
          <h3>No devices found</h3>
          <p className="subtitle">Diagnostics will appear after a device is added from the mobile app.</p>
        </div>
      ) : null}

      <section className="support-section">
        <div className="section-header">
          <div>
            <h3>Device health</h3>
            <p className="subtitle">Status comes from the device list and the per-device diagnostics endpoint.</p>
          </div>
        </div>

        <div className="support-device-grid">
          {records.map((record) => (
            <article className="card support-device-card" key={record.device.id}>
              <div className="support-card-header">
                <div>
                  <h4>{record.device.name}</h4>
                  <p className="meta-text">{record.device.location ?? "No location set"}</p>
                </div>
                <span className={`chip chip-${chipToneForStatus(record.device.status)}`}>{formatStatus(record.device.status)}</span>
              </div>

              {record.error ? <p className="status-banner status-banner-error">{record.error}</p> : null}

              <div className="detail-grid">
                <DiagnosticRow label="Device ID" value={record.device.id} />
                <DiagnosticRow label="Plant" value={record.device.plantType ?? "Not set"} />
                <DiagnosticRow label="Last seen" value={formatTime(record.device.lastSeenAt)} />
                <DiagnosticRow label="Last reading" value={formatTime(record.device.latestReading?.timestamp)} />
                <DiagnosticRow label="Snapshots" value={String(record.diagnostics?.snapshots.length ?? 0)} />
                <DiagnosticRow label="Recent events" value={String(record.diagnostics?.recentEvents.length ?? 0)} />
              </div>

              {record.diagnostics?.snapshots.length ? (
                <div className="support-node-list">
                  {record.diagnostics.snapshots.map((snapshot) => (
                    <DiagnosticSnapshotSummary snapshot={snapshot} key={snapshot.hardwareDeviceId} />
                  ))}
                </div>
              ) : (
                <p className="meta-text">No diagnostic snapshots reported for this device yet.</p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="card support-events-panel">
        <div className="section-header">
          <div>
            <h3>Recent diagnostic events</h3>
            <p className="subtitle">Latest warnings and errors across devices.</p>
          </div>
        </div>

        {recentEvents.length ? (
          <div className="activity-list">
            {recentEvents.map(({ device, event }) => (
              <div className="activity-row" key={`${device.id}-${event.id}`}>
                <div>
                  <strong>{device.name}</strong>
                  <p className="meta-text">{formatDiagnosticEvent(event)}</p>
                </div>
                <span className={`chip chip-${chipToneForSeverity(event.severity)}`}>{formatStatus(event.severity)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtitle">No recent diagnostic events.</p>
        )}
      </section>
    </section>
  );
}

function DiagnosticSnapshotSummary({ snapshot }: { snapshot: DeviceDiagnosticSnapshot }) {
  return (
    <div className="support-node-row">
      <div className="support-node-title">
        <strong>{formatNodeTitle(snapshot)}</strong>
        <span className={`chip chip-${chipToneForStatus(snapshot.reportedStatus ?? "unknown")}`}>
          {formatStatus(snapshot.reportedStatus ?? "unknown")}
        </span>
      </div>
      <div className="detail-grid">
        <DiagnosticRow label="Firmware" value={snapshot.firmwareVersion ?? "Not reported"} />
        <DiagnosticRow label="Uptime" value={formatUptime(snapshot.uptimeSeconds)} />
        <DiagnosticRow label="Wi-Fi RSSI" value={formatRssi(snapshot.wifiRssiDbm)} />
        <DiagnosticRow label="Reboot" value={formatCode(snapshot.rebootReason)} />
        <DiagnosticRow label="Provisioning" value={formatCode(snapshot.provisioningState)} />
        <DiagnosticRow label="Last command" value={formatLastCommand(snapshot)} />
        <DiagnosticRow label="Last error" value={formatLastError(snapshot)} />
        <DiagnosticRow label="Counters" value={formatCounters(snapshot.errorCounters)} />
        <DiagnosticRow label="Updated" value={formatTime(snapshot.updatedAt)} />
      </div>
    </div>
  );
}

function DiagnosticRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-row">
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="diagnostic-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function summarizeRecords(records: DeviceDiagnosticRecord[]) {
  return records.reduce(
    (summary, record) => {
      summary.deviceCount += 1;
      if (record.device.status === "online") {
        summary.onlineCount += 1;
      }
      const hasDiagnosticConcern = (record.diagnostics?.recentEvents ?? []).some((event) => isConcernSeverity(event.severity));
      const hasSnapshotConcern = (record.diagnostics?.snapshots ?? []).some((snapshot) =>
        isConcernStatus(snapshot.reportedStatus) || Boolean(snapshot.lastErrorCode) || hasNonZeroCounters(snapshot.errorCounters),
      );
      if (isConcernStatus(record.device.status) || hasDiagnosticConcern || hasSnapshotConcern || record.error) {
        summary.needsReviewCount += 1;
      }
      summary.eventCount += record.diagnostics?.recentEvents.length ?? 0;
      return summary;
    },
    { deviceCount: 0, onlineCount: 0, needsReviewCount: 0, eventCount: 0 },
  );
}

function collectRecentEvents(records: DeviceDiagnosticRecord[]) {
  return records
    .flatMap((record) =>
      (record.diagnostics?.recentEvents ?? []).map((event) => ({
        device: record.device,
        event,
      })),
    )
    .sort((left, right) => new Date(right.event.occurredAt).getTime() - new Date(left.event.occurredAt).getTime())
    .slice(0, 12);
}

function formatDiagnosticEvent(event: DeviceDiagnosticEvent): string {
  const code = event.code ? formatCode(event.code) : formatCode(event.eventType);
  const count = typeof event.count === "number" ? ` (${event.count})` : "";
  const message = event.message ? `: ${event.message}` : "";
  return `${code}${count}${message} · ${formatTime(event.occurredAt)}`;
}

function formatNodeTitle(snapshot: DeviceDiagnosticSnapshot): string {
  const role = snapshot.nodeRole ? formatCode(snapshot.nodeRole) : "Node";
  return `${role} · ${snapshot.hardwareDeviceId}`;
}

function formatLastCommand(snapshot: DeviceDiagnosticSnapshot): string {
  if (!snapshot.lastCommandStatus && !snapshot.lastCommandCode) {
    return "Not reported";
  }
  const status = formatCode(snapshot.lastCommandStatus);
  const code = snapshot.lastCommandCode ? ` / ${formatCode(snapshot.lastCommandCode)}` : "";
  const message = snapshot.lastCommandMessage ? ` / ${snapshot.lastCommandMessage}` : "";
  return `${status}${code}${message}`;
}

function formatLastError(snapshot: DeviceDiagnosticSnapshot): string {
  if (!snapshot.lastErrorCode && !snapshot.lastErrorMessage) {
    return "None reported";
  }
  const code = formatCode(snapshot.lastErrorCode);
  const message = snapshot.lastErrorMessage ? ` / ${snapshot.lastErrorMessage}` : "";
  return `${code}${message}`;
}

function formatCounters(counters: Record<string, number>): string {
  const entries = Object.entries(counters).filter(([, value]) => value > 0);
  if (!entries.length) {
    return "None";
  }
  return entries.map(([key, value]) => `${formatCode(key)}: ${value}`).join(", ");
}

function hasNonZeroCounters(counters: Record<string, number>): boolean {
  return Object.values(counters).some((value) => value > 0);
}

function isConcernSeverity(severity: string): boolean {
  const normalized = severity.toLowerCase();
  return normalized === "warning" || normalized === "error" || normalized === "critical";
}

function isConcernStatus(status: string | undefined): boolean {
  return status === "offline" || status === "stale" || status === "warning" || status === "degraded" || status === "error";
}

function chipToneForStatus(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "online") {
    return "online";
  }
  if (normalized === "offline" || normalized === "error" || normalized === "critical") {
    return "offline";
  }
  if (normalized === "degraded" || normalized === "warning" || normalized === "stale") {
    return "degraded";
  }
  return "unknown";
}

function chipToneForSeverity(severity: string): string {
  return isConcernSeverity(severity) ? (severity.toLowerCase() === "error" || severity.toLowerCase() === "critical" ? "offline" : "degraded") : "online";
}

function formatStatus(status: string): string {
  return formatCode(status);
}

function formatCode(value: string | undefined): string {
  if (!value) {
    return "Not reported";
  }
  return value.replace(/_/g, " ");
}

function formatUptime(seconds: number | undefined): string {
  if (typeof seconds !== "number") {
    return "Not reported";
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatRssi(value: number | undefined): string {
  return typeof value === "number" ? `${value} dBm` : "Not reported";
}

function formatTime(timestamp: string | undefined): string {
  if (!timestamp) {
    return "Waiting";
  }
  return new Date(timestamp).toLocaleString();
}
