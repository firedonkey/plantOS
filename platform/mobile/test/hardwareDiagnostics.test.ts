import assert from "node:assert/strict";
import { test } from "node:test";

import { getDeviceDashboard } from "../src/api/devices";

function renderExpandedHardwareHealthPanel(health: Record<string, unknown>) {
  const React = require("react") as any;
  const { renderToStaticMarkup } = require("react-dom/server") as { renderToStaticMarkup: (element: unknown) => string };
  const originalUseState = React.useState;
  const reactNativePath = require.resolve("react-native");
  const moduleCache = require.cache as Record<string, unknown>;
  const originalReactNative = moduleCache[reactNativePath];
  const globals = globalThis as typeof globalThis & { React?: unknown };
  const originalGlobalReact = globals.React;
  type MockProps = { children?: unknown };

  globals.React = React;
  React.useState = () => [true, () => undefined];
  moduleCache[reactNativePath] = {
    id: reactNativePath,
    filename: reactNativePath,
    loaded: true,
    exports: {
      Pressable: ({ children }: MockProps) => React.createElement("button", null, children),
      StyleSheet: { create: (styles: unknown) => styles },
      Text: ({ children }: MockProps) => React.createElement("span", null, children),
      View: ({ children }: MockProps) => React.createElement("div", null, children),
    },
  };

  try {
    const { HardwareHealthPanel } = require("../src/components/HardwareHealthPanel");
    return renderToStaticMarkup(React.createElement(HardwareHealthPanel, { health }));
  } finally {
    React.useState = originalUseState;
    globals.React = originalGlobalReact;
    if (originalReactNative) {
      moduleCache[reactNativePath] = originalReactNative;
    } else {
      delete moduleCache[reactNativePath];
    }
  }
}

test("mobile dashboard mapping tolerates partial hardware diagnostics", async () => {
  process.env.EXPO_PUBLIC_API_BASE_URL = "https://backend.example.test";
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input: string | URL | Request) => {
    const url = String(input);
    let payload: unknown;
    if (url.endsWith("/api/devices/7/summary")) {
      payload = {
        id: 7,
        name: "Diagnostics test device",
        hardware_health: {
          overall_status: "online",
          master_online: true,
          master_status: "online",
          friendly_status: "needs_attention",
          attention_reasons: ["weak_wifi_signal"],
          primary: {
            hardware_device_id: "master-01",
            node_role: "master",
            status: "online",
            software_version: "0.2.3",
            diagnostics: {
              schema_version: 1,
              uptime_seconds: 3661,
              wifi_rssi_dbm: -78,
              error_counters: {
                upload_failures: 2,
              },
            },
          },
          cameras: [],
        },
      };
    } else if (url.includes("/api/devices/7/readings?") || url.endsWith("/api/devices/7/commands") || url.includes("/api/devices/7/images?")) {
      payload = [];
    } else {
      throw new Error(`Unexpected request: ${url}`);
    }

    return {
      ok: true,
      json: async () => payload,
    } as Response;
  }) as typeof fetch;

  try {
    const { dashboard, usedMock } = await getDeviceDashboard("7");
    const diagnostics = dashboard.hardwareHealth?.primary?.diagnostics;
    assert.equal(usedMock, false);
    assert.equal(dashboard.hardwareHealth?.friendlyStatus, "needs_attention");
    assert.deepEqual(dashboard.hardwareHealth?.attentionReasons, ["weak_wifi_signal"]);
    assert.equal(diagnostics?.schemaVersion, 1);
    assert.equal(diagnostics?.uptimeSeconds, 3661);
    assert.equal(diagnostics?.wifiRssiDbm, -78);
    assert.equal(diagnostics?.errorCounters?.upload_failures, 2);
    assert.equal(diagnostics?.rebootReason, undefined);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("hardware health panel renders missing diagnostics without crashing", () => {
  const html = renderExpandedHardwareHealthPanel({
    overallStatus: "online",
    masterOnline: true,
    masterStatus: "online",
    friendlyStatus: "online",
    primary: {
      hardwareDeviceId: "master-01",
      nodeRole: "master",
      softwareVersion: "0.2.3",
      status: "online",
    },
    cameras: [],
  });

  assert.match(html, /Online/);
  assert.match(html, /Support diagnostics/);
  assert.match(html, /Uptime/);
  assert.match(html, /Not reported/);
  assert.match(html, /No update pending/);
});

test("hardware health panel renders partial diagnostics and counters", () => {
  const html = renderExpandedHardwareHealthPanel({
    overallStatus: "online",
    masterOnline: true,
    masterStatus: "online",
    friendlyStatus: "needs_attention",
    attentionReasons: ["weak_wifi_signal", "upload_failures_reported"],
    primary: {
      hardwareDeviceId: "master-01",
      nodeRole: "master",
      softwareVersion: "0.2.3",
      status: "online",
      diagnostics: {
        uptimeSeconds: 3661,
        wifiRssiDbm: -78,
        rebootReason: "power_on",
        provisioningState: "normal",
        lastCommandStatus: "failed",
        lastCommandCode: "relay_timeout",
        errorCounters: {
          upload_failures: 2,
          wifi_reconnects: 1,
        },
      },
    },
    cameras: [],
  });

  assert.match(html, /Needs attention/);
  assert.match(html, /1h 1m/);
  assert.match(html, /-78 dBm/);
  assert.match(html, /power on/);
  assert.match(html, /relay timeout/);
  assert.match(html, /upload failures: 2/);
  assert.match(html, /wifi reconnects: 1/);
});
