import { decode as decodeBase64, encode as encodeBase64 } from "base-64";

export const BLE_PROVISIONING_LIMITS = {
  ssidBytes: 32,
  passwordBytes: 63,
  tokenBytes: 256,
  urlBytes: 256,
  payloadBytes: 768,
} as const;

export type BleProvisioningErrorCode =
  | "already_committed"
  | "backend_url_too_long"
  | "ble_unavailable"
  | "bluetooth_off"
  | "busy"
  | "connect_failed"
  | "direct_device_token_unsupported"
  | "invalid_payload"
  | "missing_password"
  | "missing_platform_url"
  | "missing_ssid"
  | "missing_token"
  | "no_devices"
  | "password_too_long"
  | "payload_too_large"
  | "permission_denied"
  | "platform_url_too_long"
  | "provisioning_failed"
  | "provisioning_timeout"
  | "read_failed"
  | "save_failed"
  | "scan_failed"
  | "scan_notify_failed"
  | "scan_request_failed"
  | "ssid_too_long"
  | "status_parse_failed"
  | "token_too_long"
  | "wifi_scan_error"
  | "wifi_scan_timeout"
  | "write_failed";

export class BleProvisioningError extends Error {
  code: BleProvisioningErrorCode | string;

  constructor(code: BleProvisioningErrorCode | string, message: string) {
    super(message);
    this.name = "BleProvisioningError";
    this.code = code;
  }
}

export type BuildBleProvisioningPayloadInput = {
  ssid: string;
  password: string;
  setupToken: string;
  platformUrl: string;
  backendUrl?: string | null;
};

export type BleProvisioningStatus = {
  state: string;
  ready: boolean;
  rebooting: boolean;
  error?: string;
  message?: string;
};

export function buildBleProvisioningPayload(input: BuildBleProvisioningPayloadInput): string {
  const ssid = input.ssid.trim();
  const setupToken = input.setupToken.trim();
  const platformUrl = input.platformUrl.trim();
  const backendUrl = input.backendUrl?.trim() ?? "";
  const password = input.password;

  assertRequired(ssid, "missing_ssid", "Select or type the Wi-Fi name before provisioning.");
  assertRequired(password, "missing_password", "Enter the Wi-Fi password before provisioning.");
  assertRequired(setupToken, "missing_token", "Create another setup token before provisioning.");
  assertRequired(platformUrl, "missing_platform_url", "A platform URL is required before provisioning.");
  assertByteLength(ssid, BLE_PROVISIONING_LIMITS.ssidBytes, "ssid_too_long", "Wi-Fi SSID is too long for ESP32 provisioning.");
  assertByteLength(password, BLE_PROVISIONING_LIMITS.passwordBytes, "password_too_long", "Wi-Fi password is too long for ESP32 provisioning.");
  assertByteLength(setupToken, BLE_PROVISIONING_LIMITS.tokenBytes, "token_too_long", "Setup token is too long for ESP32 provisioning.");
  assertByteLength(platformUrl, BLE_PROVISIONING_LIMITS.urlBytes, "platform_url_too_long", "Platform URL is too long for ESP32 provisioning.");
  if (backendUrl) {
    assertByteLength(backendUrl, BLE_PROVISIONING_LIMITS.urlBytes, "backend_url_too_long", "Provisioning URL is too long for ESP32 provisioning.");
  }

  const payload: Record<string, string> = {
    ssid,
    password,
    plantlab_token: setupToken,
    platform_url: platformUrl,
  };
  if (backendUrl) {
    payload.backend_url = backendUrl;
  }

  const json = JSON.stringify(payload);
  assertByteLength(json, BLE_PROVISIONING_LIMITS.payloadBytes, "payload_too_large", "Provisioning details are too large to send over BLE.");
  return json;
}

export function parseBleProvisioningStatus(json: string): BleProvisioningStatus {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    throw new BleProvisioningError("status_parse_failed", "The device sent an unreadable provisioning status.");
  }

  if (!parsed || typeof parsed !== "object") {
    throw new BleProvisioningError("status_parse_failed", "The device sent an unreadable provisioning status.");
  }

  const body = parsed as { state?: unknown; ready?: unknown; rebooting?: unknown; error?: unknown; message?: unknown };
  return {
    state: typeof body.state === "string" ? body.state : "UNKNOWN",
    ready: body.ready === true,
    rebooting: body.rebooting === true,
    error: typeof body.error === "string" && body.error.trim().length > 0 ? body.error.trim() : undefined,
    message: typeof body.message === "string" && body.message.trim().length > 0 ? body.message.trim() : undefined,
  };
}

export function isBleProvisioningSuccess(status: BleProvisioningStatus): boolean {
  return status.state === "PROVISIONING_SUCCESS" || status.rebooting;
}

export function isBleProvisioningFailure(status: BleProvisioningStatus): boolean {
  return status.state === "PROVISIONING_FAILED" || Boolean(status.error);
}

export function encodeUtf8ToBase64(value: string): string {
  return encodeBase64(toUtf8Binary(value));
}

export function decodeBase64Utf8(value: string): string {
  const plainJson = extractJsonPayload(value);
  if (plainJson) {
    return plainJson;
  }

  try {
    const decoded = fromUtf8Binary(decodeBase64(value));
    return extractJsonPayload(decoded) ?? decoded;
  } catch {
    const fallbackJson = extractJsonPayload(value);
    if (fallbackJson) {
      return fallbackJson;
    }
    throw new BleProvisioningError("invalid_payload", `The BLE payload was not readable (${describePayloadShape(value)}).`);
  }
}

export function utf8ByteLength(value: string): number {
  return toUtf8Binary(value).length;
}

export function maskSecret(value?: string | null): string {
  const trimmed = value?.trim() ?? "";
  if (!trimmed) {
    return "";
  }
  if (trimmed.length <= 8) {
    return "••••";
  }
  return `${trimmed.slice(0, 4)}...${trimmed.slice(-4)}`;
}

export function provisioningStatusMessage(status: BleProvisioningStatus): string {
  if (isBleProvisioningSuccess(status)) {
    return "Provisioning saved. Device is rebooting.";
  }
  if (status.error) {
    return provisioningErrorMessage(status.error);
  }
  if (status.state === "PROVISIONING_COMMITTING") {
    return "Saving credentials on the device...";
  }
  return "Waiting for device confirmation...";
}

export function provisioningErrorMessage(code: string): string {
  switch (code) {
    case "already_committed":
      return "This setup payload was already saved. Restart provisioning mode to retry.";
    case "busy":
      return "The device is busy. Wait a moment and retry provisioning.";
    case "direct_device_token_unsupported":
      return "The device rejected the token type. Create a new setup token and retry.";
    case "missing_password":
      return "Wi-Fi password is missing.";
    case "missing_ssid":
      return "Wi-Fi SSID is missing.";
    case "missing_token":
      return "Setup token is missing. Create another setup token and retry.";
    case "save_failed":
      return "The device could not save provisioning details. Retry provisioning.";
    default:
      return "The device rejected provisioning details. Check the Wi-Fi details and retry.";
  }
}

function assertRequired(value: string, code: BleProvisioningErrorCode, message: string) {
  if (!value) {
    throw new BleProvisioningError(code, message);
  }
}

function assertByteLength(value: string, maxBytes: number, code: BleProvisioningErrorCode, message: string) {
  if (utf8ByteLength(value) > maxBytes) {
    throw new BleProvisioningError(code, message);
  }
}

function toUtf8Binary(value: string): string {
  return unescape(encodeURIComponent(value));
}

function fromUtf8Binary(value: string): string {
  if (isAscii(value)) {
    return stripNullTerminators(value);
  }
  return decodeURIComponent(escape(value));
}

function isAscii(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    if (value.charCodeAt(index) > 0x7f) {
      return false;
    }
  }
  return true;
}

function extractJsonPayload(value: string): string | null {
  const normalized = stripNullTerminators(value).trim();
  const objectPayload = extractJsonBetween(normalized, "{", "}");
  if (objectPayload) {
    return objectPayload;
  }
  return extractJsonBetween(normalized, "[", "]");
}

function extractJsonBetween(value: string, startToken: string, endToken: string): string | null {
  const start = value.indexOf(startToken);
  const end = value.lastIndexOf(endToken);
  if (start === -1 || end === -1 || end <= start) {
    return null;
  }
  return value.slice(start, end + 1);
}

function stripNullTerminators(value: string): string {
  return value.replace(/\u0000/g, "");
}

function describePayloadShape(value: string): string {
  const trimmed = value.trim();
  const firstCode = trimmed.length > 0 ? trimmed.charCodeAt(0) : -1;
  const lastCode = trimmed.length > 0 ? trimmed.charCodeAt(trimmed.length - 1) : -1;
  const base64ish = /^[A-Za-z0-9+/=_-]+$/.test(trimmed);
  const hasJsonStart = trimmed.includes("{") || trimmed.includes("[");
  const hasJsonEnd = trimmed.includes("}") || trimmed.includes("]");
  return `len=${value.length}, first=${firstCode}, last=${lastCode}, base64ish=${base64ish}, jsonStart=${hasJsonStart}, jsonEnd=${hasJsonEnd}`;
}
