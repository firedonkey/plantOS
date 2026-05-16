import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BLE_PROVISIONING_LIMITS,
  BleProvisioningError,
  buildBleProvisioningPayload,
  decodeBase64Utf8,
  encodeUtf8ToBase64,
  isBleProvisioningFailure,
  isBleProvisioningSuccess,
  maskSecret,
  parseBleProvisioningStatus,
} from "../src/ble/bleProvisioningPayload";

test("buildBleProvisioningPayload emits compact firmware JSON only", () => {
  const payload = buildBleProvisioningPayload({
    ssid: " PlantLab ",
    password: " wifi password ",
    setupToken: " setup-token ",
    platformUrl: " http://192.168.1.10:8000 ",
    backendUrl: " http://192.168.1.10:8000/api/devices/register-provisioned ",
  });
  const parsed = JSON.parse(payload);

  assert.equal(payload.includes("\n"), false);
  assert.deepEqual(parsed, {
    ssid: "PlantLab",
    password: " wifi password ",
    plantlab_token: "setup-token",
    platform_url: "http://192.168.1.10:8000",
    backend_url: "http://192.168.1.10:8000/api/devices/register-provisioned",
  });
  assert.equal("device_token" in parsed, false);
  assert.equal("device_access_token" in parsed, false);
});

test("buildBleProvisioningPayload includes recovery attach target only when provided", () => {
  const normalPayload = JSON.parse(buildBleProvisioningPayload({
    ssid: "PlantLab",
    password: "wifi password",
    setupToken: "setup-token",
    platformUrl: "http://192.168.1.10:8000",
  }));
  const recoveryPayload = JSON.parse(buildBleProvisioningPayload({
    ssid: "PlantLab",
    password: "wifi password",
    setupToken: "setup-token",
    platformUrl: "http://192.168.1.10:8000",
    attachToPlatformDeviceId: 42,
  }));

  assert.equal("attach_to_platform_device_id" in normalPayload, false);
  assert.equal(recoveryPayload.attach_to_platform_device_id, 42);
});

test("buildBleProvisioningPayload validates required fields and firmware limits", () => {
  assertBleError("missing_ssid", () =>
    buildBleProvisioningPayload({ ssid: " ", password: "password", setupToken: "token", platformUrl: "http://host" }),
  );
  assertBleError("missing_password", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "", setupToken: "token", platformUrl: "http://host" }),
  );
  assertBleError("missing_token", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: " ", platformUrl: "http://host" }),
  );
  assertBleError("missing_platform_url", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "token", platformUrl: " " }),
  );
  assertBleError("ssid_too_long", () =>
    buildBleProvisioningPayload({ ssid: "x".repeat(BLE_PROVISIONING_LIMITS.ssidBytes + 1), password: "password", setupToken: "token", platformUrl: "http://host" }),
  );
  assertBleError("password_too_long", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "x".repeat(BLE_PROVISIONING_LIMITS.passwordBytes + 1), setupToken: "token", platformUrl: "http://host" }),
  );
  assertBleError("token_too_long", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "x".repeat(BLE_PROVISIONING_LIMITS.tokenBytes + 1), platformUrl: "http://host" }),
  );
  assertBleError("platform_url_too_long", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "token", platformUrl: `http://${"x".repeat(BLE_PROVISIONING_LIMITS.urlBytes)}` }),
  );
  assertBleError("backend_url_too_long", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "token", platformUrl: "http://host", backendUrl: `http://${"x".repeat(BLE_PROVISIONING_LIMITS.urlBytes)}` }),
  );
  assertBleError("invalid_payload", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "token", platformUrl: "http://host", attachToPlatformDeviceId: 0 }),
  );
  assertBleError("invalid_payload", () =>
    buildBleProvisioningPayload({ ssid: "PlantLab", password: "password", setupToken: "token", platformUrl: "http://host", attachToPlatformDeviceId: 1.5 }),
  );
  assertBleError("payload_too_large", () =>
    buildBleProvisioningPayload({
      ssid: "x".repeat(BLE_PROVISIONING_LIMITS.ssidBytes),
      password: "x".repeat(BLE_PROVISIONING_LIMITS.passwordBytes),
      setupToken: "x".repeat(BLE_PROVISIONING_LIMITS.tokenBytes),
      platformUrl: `http://${"x".repeat(BLE_PROVISIONING_LIMITS.urlBytes - "http://".length)}`,
      backendUrl: `http://${"x".repeat(BLE_PROVISIONING_LIMITS.urlBytes - "http://".length)}`,
    }),
  );
});

test("base64 helpers round-trip UTF-8 provisioning values", () => {
  const payload = JSON.stringify({ ssid: "PlantLab-ñ", password: "wifi-密码" });
  assert.equal(decodeBase64Utf8(encodeUtf8ToBase64(payload)), payload);
});

test("base64 decoder accepts plain JSON BLE values from firmware", () => {
  const payload = JSON.stringify({ source: "esp32-ble", device_id: "pl-esp32-64e0a80af6e8" });
  assert.equal(decodeBase64Utf8(payload), payload);
});

test("base64 decoder accepts plain JSON wrapped by BLE control bytes", () => {
  const payload = JSON.stringify({ source: "esp32-ble", device_id: "pl-esp32-64e0a80af6e8" });
  assert.equal(decodeBase64Utf8(`\u0000${payload}\u0000`), payload);
  assert.equal(decodeBase64Utf8(`identity=${payload}\u0000`), payload);
});

test("status parser identifies ready, committing, success, and firmware errors", () => {
  assert.deepEqual(parseBleProvisioningStatus('{"state":"PROVISIONING_BLE","ready":true}'), {
    state: "PROVISIONING_BLE",
    ready: true,
    rebooting: false,
    error: undefined,
    message: undefined,
  });
  assert.equal(parseBleProvisioningStatus('{"state":"PROVISIONING_COMMITTING"}').state, "PROVISIONING_COMMITTING");
  assert.equal(parseBleProvisioningStatus('{"state":"WIFI_CONNECTING"}').state, "WIFI_CONNECTING");
  assert.equal(isBleProvisioningSuccess(parseBleProvisioningStatus('{"state":"PROVISIONING_SUCCESS","rebooting":true}')), true);
  assert.equal(isBleProvisioningFailure(parseBleProvisioningStatus('{"state":"PROVISIONING_FAILED","error":"save_failed"}')), true);
  assert.equal(isBleProvisioningFailure(parseBleProvisioningStatus('{"state":"PROVISIONING_BLE","ready":true,"error":"wifi_connect_failed"}')), true);
  assertBleError("status_parse_failed", () => parseBleProvisioningStatus("not-json"));
});

test("maskSecret hides setup tokens for normal UI", () => {
  assert.equal(maskSecret("abcd1234wxyz"), "abcd...wxyz");
  assert.equal(maskSecret("short"), "••••");
  assert.equal(maskSecret(""), "");
});

function assertBleError(code: string, action: () => void) {
  assert.throws(
    action,
    (error) => error instanceof BleProvisioningError && error.code === code,
  );
}
