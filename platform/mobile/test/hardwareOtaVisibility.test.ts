import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { getDeviceDashboard } from "../src/api/devices";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");

test("mobile API maps optional firmware and OTA fields without requiring old backend responses to include them", async () => {
  const source = await readText("../src/api/devices.ts");

  for (const requiredText of [
    "software_version?: string | null;",
    "ota_status?: string | null;",
    "ota_available_version?: string | null;",
    "ota_target_version?: string | null;",
    "ota_release_id?: string | null;",
    "ota_progress?: number | null;",
    "ota_error?: string | null;",
    "ota_updated_at?: string | null;",
    "ota_last_success_at?: string | null;",
    "softwareVersion: node.software_version ?? undefined",
    "otaStatus: normalizeOtaStatus(node.ota_status)",
    "otaAvailableVersion: node.ota_available_version ?? undefined",
    "otaTargetVersion: node.ota_target_version ?? undefined",
    "otaError: node.ota_error ?? undefined",
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.match(source, /function normalizeOtaStatus\(status\?: string \| null\): HardwareNodeHealth\["otaStatus"\] \| undefined/);
  assert.match(source, /normalized === "idle"/);
  assert.match(source, /normalized === "available"/);
  assert.match(source, /normalized === "downloading"/);
  assert.match(source, /normalized === "installing"/);
  assert.match(source, /normalized === "success"/);
  assert.match(source, /normalized === "failed"/);
});

test("hardware health panel renders without OTA fields in old backend health payloads", () => {
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
    const html = renderToStaticMarkup(
      React.createElement(HardwareHealthPanel, {
        health: {
          overallStatus: "online",
          masterOnline: true,
          masterStatus: "online",
          primary: {
            hardwareDeviceId: "master-01",
            nodeRole: "master",
            softwareVersion: "0.2.3",
            status: "online",
          },
          cameras: [],
        },
      }),
    );

    assert.match(html, /Firmware/);
    assert.match(html, /0\.2\.3 · Unknown/);
    assert.match(html, /No update pending/);
  } finally {
    React.useState = originalUseState;
    globals.React = originalGlobalReact;
    if (originalReactNative) {
      moduleCache[reactNativePath] = originalReactNative;
    } else {
      delete moduleCache[reactNativePath];
    }
  }
});

test("mobile dashboard mapping tolerates hardware health nodes without OTA fields", async () => {
  process.env.EXPO_PUBLIC_API_BASE_URL = "https://backend.example.test";
  const originalFetch = globalThis.fetch;
  const requests: string[] = [];

  globalThis.fetch = (async (input: string | URL | Request) => {
    const url = String(input);
    requests.push(url);
    let payload: unknown;
    if (url.endsWith("/api/devices/7/summary")) {
      payload = {
        id: 7,
        name: "OTA test device",
        hardware_health: {
          overall_status: "online",
          master_online: true,
          master_status: "online",
          primary: {
            hardware_device_id: "master-01",
            node_role: "master",
            status: "online",
            software_version: "0.2.3",
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
    assert.equal(usedMock, false);
    assert.equal(dashboard.hardwareHealth?.primary?.softwareVersion, "0.2.3");
    assert.equal(dashboard.hardwareHealth?.primary?.otaStatus, undefined);
    assert.equal(dashboard.hardwareHealth?.primary?.otaAvailableVersion, undefined);
    assert.equal(dashboard.hardwareHealth?.primary?.otaTargetVersion, undefined);
    assert.equal(dashboard.hardwareHealth?.primary?.otaError, undefined);
    assert.equal(requests.length, 4);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
