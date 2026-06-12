import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchAdminDiagnostics } from "@/api/admin";
import { useSession } from "@/hooks/useSession";
import { AdminCommand, AdminDevice, AdminDiagnostics, AdminEvent, AdminUser } from "@/types";

type UserRollup = {
  user: AdminUser;
  devices: AdminDevice[];
  events: AdminEvent[];
  commands: AdminCommand[];
  hardwareIssueCount: number;
};

export function AdminDiagnosticsScreen() {
  const { getAccessToken, token } = useSession();
  const [diagnostics, setDiagnostics] = useState<AdminDiagnostics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const accessToken = await getAccessToken();
      setDiagnostics(await fetchAdminDiagnostics(accessToken ?? undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load admin diagnostics.");
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const userRollups = useMemo(() => (diagnostics ? buildUserRollups(diagnostics) : []), [diagnostics]);

  return (
    <section className="page-section admin-diagnostics-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">ADMIN</div>
          <h2>System diagnostics</h2>
          <p className="subtitle">System-wide integration health first, then per-user device, hardware, and command details.</p>
          <p className="meta-text">
            {diagnostics ? `Generated ${new Date(diagnostics.generatedAt).toLocaleString()} for ${diagnostics.requestedBy.email}` : "Waiting for first refresh."}
          </p>
        </div>
        <button className="secondary-button" disabled={isLoading} onClick={() => void refresh()}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && !diagnostics ? <p className="status-banner">Loading admin diagnostics...</p> : null}

      {diagnostics ? (
        <>
          <section className="card admin-section-card">
            <div className="section-header">
              <div>
                <h3>Overall data integration</h3>
                <p className="subtitle">Account, device, hardware-node, diagnostic-event, and firmware release coverage across the whole system.</p>
              </div>
            </div>
            <div className="diagnostic-metric-grid admin-metric-grid">
              <SummaryMetric label="Users" value={diagnostics.summary.users} />
              <SummaryMetric label="Active users" value={diagnostics.summary.activeUsers} />
              <SummaryMetric label="Devices" value={diagnostics.summary.devices} />
              <SummaryMetric label="Active devices" value={diagnostics.summary.activeDevices} />
              <SummaryMetric label="Hardware nodes" value={diagnostics.summary.hardwareNodes} />
              <SummaryMetric label="Stale nodes" value={diagnostics.summary.staleNodes} />
              <SummaryMetric label="24h warnings" value={diagnostics.summary.recentWarningEvents} />
              <SummaryMetric label="Firmware releases" value={diagnostics.summary.firmwareReleases} />
            </div>
            <div className="admin-integration-grid">
              <DiagnosticRow label="Released devices" value={String(diagnostics.summary.releasedDevices)} />
              <DiagnosticRow label="Archived devices" value={String(diagnostics.summary.archivedDevices)} />
              <DiagnosticRow label="Recent commands" value={String(diagnostics.recentCommands.length)} />
              <DiagnosticRow label="Recent events" value={String(diagnostics.recentEvents.length)} />
            </div>
          </section>

          <section className="admin-section-card">
            <div className="section-header">
              <div>
                <h3>Per-user data</h3>
                <p className="subtitle">Online time, hardware issues, command log, and device status grouped by account.</p>
              </div>
            </div>
            <div className="admin-user-grid">
              {userRollups.map((rollup) => (
                <UserDiagnosticsCard rollup={rollup} key={rollup.user.id} />
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}

function UserDiagnosticsCard({ rollup }: { rollup: UserRollup }) {
  const { user, devices, events, commands, hardwareIssueCount } = rollup;
  return (
    <article className="card admin-user-card">
      <div className="support-card-header">
        <div>
          <h4>{user.email}</h4>
          <p className="meta-text">{user.name ?? "No display name"}</p>
        </div>
        <span className={`chip chip-${user.activeDeviceCount > 0 ? "online" : "unknown"}`}>{user.activeDeviceCount > 0 ? "Active" : "Inactive"}</span>
      </div>

      <div className="detail-grid">
        <DiagnosticRow label="User ID" value={user.id} />
        <DiagnosticRow label="Created" value={formatTime(user.createdAt)} />
        <DiagnosticRow label="Last online" value={formatTime(user.lastSeenAt)} />
        <DiagnosticRow label="Devices" value={`${user.activeDeviceCount} active / ${user.deviceCount} total`} />
        <DiagnosticRow label="Hardware issues" value={String(hardwareIssueCount)} />
        <DiagnosticRow label="24h commands" value={String(user.recentCommandCount)} />
        <DiagnosticRow label="Last command" value={formatTime(user.lastCommandAt)} />
      </div>

      <div className="admin-user-subsection">
        <h5>Device status</h5>
        {devices.length ? (
          <div className="activity-list">
            {devices.map((device) => (
              <div className="activity-row" key={device.id}>
                <div>
                  <strong>{device.name}</strong>
                  <p className="meta-text">
                    {device.nodeCount} node(s) | Last reading {formatTime(device.latestReadingAt)} | Last image {formatTime(device.latestImageAt)}
                  </p>
                  {device.lastErrorCode ? <p className="meta-text">Last error: {formatCode(device.lastErrorCode)}</p> : null}
                </div>
                <span className={`chip chip-${chipToneForStatus(device.status)}`}>{formatCode(device.status)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtitle">No devices for this user.</p>
        )}
      </div>

      <div className="admin-user-subsection">
        <h5>Command log</h5>
        {commands.length ? (
          <div className="activity-list">
            {commands.slice(0, 5).map((command) => (
              <div className="activity-row" key={command.id}>
                <div>
                  <strong>{command.deviceName}</strong>
                  <p className="meta-text">
                    {formatCode(command.target)} / {formatCode(command.action)}
                    {command.value ? ` (${command.value})` : ""} | {formatTime(command.createdAt)}
                  </p>
                  {command.message ? <p className="meta-text">{command.message}</p> : null}
                </div>
                <span className={`chip chip-${chipToneForStatus(command.status)}`}>{formatCode(command.status)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtitle">No recent commands.</p>
        )}
      </div>

      <div className="admin-user-subsection">
        <h5>Hardware issues</h5>
        {events.length ? (
          <div className="activity-list">
            {events.slice(0, 5).map((event) => (
              <div className="activity-row" key={event.id}>
                <div>
                  <strong>{event.deviceName}</strong>
                  <p className="meta-text">
                    {formatCode(event.code ?? event.eventType)}{event.message ? `: ${event.message}` : ""} | {formatTime(event.occurredAt)}
                  </p>
                </div>
                <span className={`chip chip-${chipToneForSeverity(event.severity)}`}>{formatCode(event.severity)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtitle">No recent hardware issues.</p>
        )}
      </div>
    </article>
  );
}

function buildUserRollups(diagnostics: AdminDiagnostics): UserRollup[] {
  return diagnostics.users.map((user) => {
    const devices = diagnostics.devices.filter((device) => device.ownerEmail === user.email);
    const events = diagnostics.recentEvents.filter((event) => event.ownerEmail === user.email && isConcernSeverity(event.severity));
    const commands = diagnostics.recentCommands.filter((command) => command.ownerEmail === user.email);
    const deviceIssues = devices.filter(
      (device) => isConcernStatus(device.status) || Boolean(device.lastErrorCode) || device.nodes.some((node) => isConcernStatus(node.status) || Boolean(node.otaError)),
    ).length;
    return {
      user,
      devices,
      events,
      commands,
      hardwareIssueCount: user.recentWarningEventCount + deviceIssues,
    };
  });
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

function isConcernSeverity(severity: string): boolean {
  const normalized = severity.toLowerCase();
  return normalized === "warning" || normalized === "error" || normalized === "critical";
}

function isConcernStatus(status: string | undefined): boolean {
  const normalized = (status ?? "").toLowerCase();
  return normalized === "offline" || normalized === "stale" || normalized === "warning" || normalized === "degraded" || normalized === "error" || normalized === "timed_out";
}

function chipToneForStatus(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "online" || normalized === "completed") {
    return "online";
  }
  if (normalized === "offline" || normalized === "error" || normalized === "critical" || normalized === "failed" || normalized === "timed_out") {
    return "offline";
  }
  if (normalized === "degraded" || normalized === "warning" || normalized === "stale" || normalized === "in_progress" || normalized === "pending") {
    return "degraded";
  }
  return "unknown";
}

function chipToneForSeverity(severity: string): string {
  return isConcernSeverity(severity) ? (severity.toLowerCase() === "error" || severity.toLowerCase() === "critical" ? "offline" : "degraded") : "online";
}

function formatCode(value: string): string {
  return value.replace(/_/g, " ");
}

function formatTime(timestamp: string | undefined): string {
  if (!timestamp) {
    return "Waiting";
  }
  return new Date(timestamp).toLocaleString();
}
