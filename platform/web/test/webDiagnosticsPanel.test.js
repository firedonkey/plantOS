import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path) => readFile(join(testDir, path), "utf8");

function escaped(text) {
  return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

function functionSource(source, functionName) {
  const start = source.indexOf(`function ${functionName}`);
  assert.notEqual(start, -1, `${functionName} should exist`);
  const nextFunction = source.indexOf("\nfunction ", start + 1);
  return source.slice(start, nextFunction === -1 ? source.length : nextFunction);
}

test("web diagnostics panel is routed from the app shell", async () => {
  const appSource = await readText("../src/App.tsx");
  const layoutSource = await readText("../src/components/AppLayout.tsx");

  for (const requiredText of [
    "SupportDiagnosticsScreen",
    'path="support/diagnostics"',
    'to="/support/diagnostics"',
    "Support",
  ]) {
    assert.match(`${appSource}\n${layoutSource}`, escaped(requiredText));
  }
});

test("web admin diagnostics separates system integration from per-user operations", async () => {
  const appSource = await readText("../src/App.tsx");
  const layoutSource = await readText("../src/components/AppLayout.tsx");
  const apiSource = await readText("../src/api/admin.ts");
  const authSource = await readText("../src/api/auth.ts");
  const screenSource = await readText("../src/screens/AdminDiagnosticsScreen.tsx");
  const typeSource = await readText("../src/types/api.ts");

  for (const requiredText of [
    "AdminDiagnosticsScreen",
    'path="admin/diagnostics"',
    'to="/admin/diagnostics"',
    "profile.isAdmin",
    "is_admin",
    'apiRequest<ApiAdminDiagnostics>("/api/admin/diagnostics", {}, token)',
    "Overall data integration",
    "Active users",
    "Per-user data",
    "Last online",
    "Hardware issues",
    "Command log",
    "recentCommands",
    "AdminDiagnostics",
  ]) {
    assert.match(`${appSource}\n${layoutSource}\n${apiSource}\n${authSource}\n${screenSource}\n${typeSource}`, escaped(requiredText));
  }
});

test("standalone web removes add-device entry points", async () => {
  const appSource = await readText("../src/App.tsx");
  const layoutSource = await readText("../src/components/AppLayout.tsx");
  const deviceListSource = await readText("../src/screens/DeviceListScreen.tsx");
  const supportSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");

  assert.match(appSource, escaped('path="devices/add" element={<Navigate to="/devices" replace />}'));
  assert.doesNotMatch(layoutSource, /Add device/);
  assert.doesNotMatch(deviceListSource, /to="\/devices\/add"|Open add-device flow/);
  assert.match(deviceListSource, /mobile app/);
  assert.doesNotMatch(supportSource, /to="\/devices\/add"|Add a device/);
});

test("web landing page remains visible for signed-in users", async () => {
  const landingSource = await readText("../src/screens/LandingScreen.tsx");
  const appSource = await readText("../src/App.tsx");

  assert.match(appSource, escaped('<Route path="/" element={<LandingScreen />} />'));
  assert.match(landingSource, escaped('const dashboardHref = token ? "/devices" : "/login";'));
  assert.match(landingSource, escaped('const dashboardLabel = token ? "Dashboard" : "Sign in";'));
  assert.doesNotMatch(landingSource, /Navigate to="\/devices"|return <Navigate/);
});

test("web diagnostics panel uses account, device, and per-device diagnostics APIs", async () => {
  const authSource = await readText("../src/api/auth.ts");
  const devicesSource = await readText("../src/api/devices.ts");
  const screenSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");

  for (const requiredText of [
    'apiRequest<ApiCurrentUser>("/api/me", {}, token)',
    "fetchCurrentUserProfile(token ?? undefined, session?.email)",
    "listDevices(token ?? undefined)",
    "getDeviceDiagnostics(device.id, token ?? undefined, 20)",
    '`/api/devices/${deviceId}/diagnostics?${params.toString()}`',
    "snapshots: (payload.snapshots ?? []).map(mapDiagnosticSnapshot)",
    "recentEvents: (payload.recent_events ?? []).map(mapDiagnosticEvent)",
  ]) {
    assert.match(`${authSource}\n${devicesSource}\n${screenSource}`, escaped(requiredText));
  }
});

test("web diagnostics panel surfaces support health summary and event details", async () => {
  const screenSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");
  const typeSource = await readText("../src/types/api.ts");
  const mockSource = await readText("../src/mock/data.ts");

  for (const requiredText of [
    "Account health",
    "Fleet health",
    "Device health",
    "Recent diagnostic events",
    "DeviceDiagnosticSnapshot",
    "DeviceDiagnosticEvent",
    "lastCommandMessage",
    "reportedAt",
    'friendlyStatus: "needs_attention"',
    'attentionReasons: ["camera_offline", "upload_failures"]',
    'lastErrorCode: "upload_failed"',
  ]) {
    assert.match(`${screenSource}\n${typeSource}\n${mockSource}`, escaped(requiredText));
  }
});

test("web diagnostics panel isolates per-device diagnostics failures", async () => {
  const screenSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");

  for (const requiredText of [
    "devicesResult.devices.map(async (device): Promise<DeviceDiagnosticRecord> => {",
    "diagnostics: null",
    "Unable to load diagnostics for this device.",
    'record.error ? <p className="status-banner status-banner-error">{record.error}</p> : null',
    "records.length === 0 && !isLoading && !error",
  ]) {
    assert.match(screenSource, escaped(requiredText));
  }
});

test("web diagnostics panel computes triage summary from device, snapshot, and event signals", async () => {
  const screenSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");

  for (const requiredText of [
    "function summarizeRecords(records: DeviceDiagnosticRecord[])",
    "const hasDiagnosticConcern = (record.diagnostics?.recentEvents ?? []).some((event) => isConcernSeverity(event.severity));",
    "isConcernStatus(snapshot.reportedStatus) || Boolean(snapshot.lastErrorCode) || hasNonZeroCounters(snapshot.errorCounters)",
    "isConcernStatus(record.device.status) || hasDiagnosticConcern || hasSnapshotConcern || record.error",
    "summary.eventCount += record.diagnostics?.recentEvents.length ?? 0;",
    "function collectRecentEvents(records: DeviceDiagnosticRecord[])",
    ".sort((left, right) => new Date(right.event.occurredAt).getTime() - new Date(left.event.occurredAt).getTime())",
    ".slice(0, 12);",
  ]) {
    assert.match(screenSource, escaped(requiredText));
  }
});

test("web diagnostics API preserves backend stale status for triage", async () => {
  const devicesSource = await readText("../src/api/devices.ts");
  const screenSource = await readText("../src/screens/SupportDiagnosticsScreen.tsx");
  const mapStatusSource = functionSource(devicesSource, "mapStatus");
  const freshnessSource = functionSource(devicesSource, "normalizeFreshnessStatus");
  const concernSource = functionSource(screenSource, "isConcernStatus");

  for (const requiredText of [
    "const normalizedExplicit = normalizeFreshnessStatus(explicitStatus);",
  ]) {
    assert.match(mapStatusSource, escaped(requiredText));
  }

  for (const requiredText of [
    'normalized === "stale"',
    'normalized === "warning"',
    'normalized === "waiting"',
  ]) {
    assert.match(freshnessSource, escaped(requiredText));
  }

  for (const requiredText of [
    "status: mapStatus(summary, device.status)",
  ]) {
    assert.match(devicesSource, escaped(requiredText));
  }

  for (const requiredText of [
    'status === "offline" || status === "stale" || status === "warning" || status === "degraded" || status === "error"',
  ]) {
    assert.match(concernSource, escaped(requiredText));
  }
});

test("web diagnostics API maps backend diagnostics and builds mock triage data", async () => {
  const devicesSource = await readText("../src/api/devices.ts");

  for (const requiredText of [
    "errorCounters: snapshot.error_counters ?? {}",
    "metadata: event.metadata ?? {}",
    "return { snapshots: [], recentEvents: [] };",
    "snapshots: nodes.map((node) => buildMockSnapshot(deviceId, node)),",
    "recentEvents: buildMockDiagnosticEvents(deviceId, health, nodes),",
    "for (const reason of health.attentionReasons ?? [])",
    "if (diagnostics?.lastErrorCode)",
    "for (const [code, count] of Object.entries(diagnostics?.errorCounters ?? {}))",
    "count,",
  ]) {
    assert.match(devicesSource, escaped(requiredText));
  }
});
