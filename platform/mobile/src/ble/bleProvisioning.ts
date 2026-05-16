import { PermissionsAndroid, Platform } from "react-native";
import type { BleManager, Device } from "react-native-ble-plx";
import {
  BleProvisioningError,
  type BleProvisioningStatus,
  buildBleProvisioningPayload,
  decodeBase64Utf8,
  encodeUtf8ToBase64,
  isBleProvisioningFailure,
  isBleProvisioningSuccess,
  parseBleProvisioningStatus,
  provisioningErrorMessage,
  provisioningStatusMessage,
} from "./bleProvisioningPayload";

export { BleProvisioningError } from "./bleProvisioningPayload";

export const BLE_PROVISIONING_SERVICE_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901";
export const BLE_PROVISIONING_WRITE_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902";
export const BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903";
export const BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a904";
export const BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a905";
export const BLE_PROVISIONING_DEVICE_IDENTITY_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a906";

const PLANTLAB_SETUP_NAME_PREFIX = "PlantLab-Setup";
const DEFAULT_SCAN_TIMEOUT_MS = 6000;
const DEFAULT_WIFI_SCAN_TIMEOUT_MS = 20000;
const DEFAULT_PROVISIONING_STATUS_TIMEOUT_MS = 45000;
const BLE_WIFI_SCAN_POLL_MS = 700;
const BLE_PROVISIONING_STATUS_POLL_MS = 1000;
const BLUETOOTH_READY_WAIT_MS = 5000;

export type BleProvisioningDevice = {
  id: string;
  name: string;
  rssi?: number;
  displaySuffix?: string;
  identity?: BleDeviceIdentity;
};

export type BleDeviceIdentity = {
  source: "esp32-ble";
  schemaVersion: number;
  deviceId: string;
  hardwareDeviceId: string;
  hardwareModel?: string;
  hardwareVersion?: string;
  softwareVersion?: string;
  nodeRole?: string;
  displayName?: string;
  bleName?: string;
  serialNumber?: string;
};

export type BleWifiNetwork = {
  ssid: string;
  rssi?: number;
};

export type BleWifiNetworksResult = {
  device: BleProvisioningDevice;
  networks: BleWifiNetwork[];
  truncated: boolean;
};

export type BleProvisioningProgressPhase = "connecting" | "sending" | "committing" | "success" | "error";

export type BleProvisioningProgress = {
  phase: BleProvisioningProgressPhase;
  message: string;
  status?: BleProvisioningStatus;
};

export type ProvisionDeviceOverBleInput = {
  deviceId: string;
  ssid: string;
  password: string;
  setupToken: string;
  platformUrl: string;
  backendUrl?: string | null;
  attachToPlatformDeviceId?: number | null;
  timeoutMs?: number;
  onProgress?: (progress: BleProvisioningProgress) => void;
};

type ParsedBleWifiNetworksPayload = {
  scanId: number | null;
  networks: BleWifiNetwork[];
  truncated: boolean;
  status: string;
  cursor: number;
  nextCursor: number | null;
};

type BleWifiScanPayloadRequest = {
  expectedCursor: number;
  expectedScanId?: number | null;
  minimumScanId?: number | null;
};

type BleWifiPayloadSource = "notify" | "immediate_read" | "poll_read";

let bleManager: BleManager | null = null;

async function getBleManager(): Promise<BleManager> {
  if (bleManager) {
    return bleManager;
  }

  try {
    const module = await import("react-native-ble-plx");
    bleManager = new module.BleManager();
    return bleManager;
  } catch {
    throw new BleProvisioningError(
      "ble_unavailable",
      "BLE scanning requires a native development build with Bluetooth support. Type the Wi-Fi name manually or use SoftAP fallback.",
    );
  }
}

export async function requestBlePermissions(): Promise<void> {
  if (Platform.OS !== "android") {
    return;
  }

  const androidVersion = typeof Platform.Version === "number" ? Platform.Version : Number.parseInt(String(Platform.Version), 10);
  const permissions =
    androidVersion >= 31
      ? [PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN, PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT]
      : [PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION];

  const result = await PermissionsAndroid.requestMultiple(permissions);
  const denied = permissions.some((permission) => result[permission] !== PermissionsAndroid.RESULTS.GRANTED);
  if (denied) {
    throw new BleProvisioningError(
      "permission_denied",
      "Bluetooth permission is required to load nearby Wi-Fi over BLE. Type the SSID manually if you do not want to allow it.",
    );
  }
}

export async function scanForBleProvisioningDevices(timeoutMs = DEFAULT_SCAN_TIMEOUT_MS): Promise<BleProvisioningDevice[]> {
  await requestBlePermissions();
  const manager = await ensureBluetoothReady("load nearby Wi-Fi over BLE");

  return new Promise((resolve, reject) => {
    const devices = new Map<string, BleProvisioningDevice>();
    const timeoutId = setTimeout(() => {
      manager.stopDeviceScan();
      resolve(Array.from(devices.values()));
    }, timeoutMs);

    manager.startDeviceScan(null, { allowDuplicates: false }, (error, device) => {
      if (error) {
        clearTimeout(timeoutId);
        manager.stopDeviceScan();
        reject(new BleProvisioningError("scan_failed", "Could not scan for PlantLab BLE devices. Type the SSID manually or try again."));
        return;
      }
      if (!device || !isProvisioningDevice(device)) {
        return;
      }
      devices.set(device.id, {
        id: device.id,
        name: device.name ?? device.localName ?? "PlantLab setup device",
        rssi: typeof device.rssi === "number" ? device.rssi : undefined,
        displaySuffix: displaySuffixForBleDevice(device.name ?? device.localName ?? ""),
      });
    });
  });
}

export async function readBleDeviceIdentity(deviceId: string): Promise<BleDeviceIdentity> {
  await requestBlePermissions();
  const manager = await ensureBluetoothReady("read this device identity over BLE");
  let connectedDevice: Device | null = null;
  try {
    connectedDevice = await manager.connectToDevice(deviceId, { timeout: 10000 });
    if (Platform.OS === "android") {
      const deviceWithRequestedMtu = await connectedDevice.requestMTU(512).catch(() => connectedDevice as Device);
      connectedDevice = deviceWithRequestedMtu;
    }
    const discoveredDevice = await connectedDevice.discoverAllServicesAndCharacteristics();
    const characteristic = await discoveredDevice.readCharacteristicForService(
      BLE_PROVISIONING_SERVICE_UUID,
      BLE_PROVISIONING_DEVICE_IDENTITY_CHARACTERISTIC_UUID,
    );
    if (!characteristic.value) {
      throw new BleProvisioningError("identity_empty", "This PlantLab firmware did not provide BLE identity. Update the device firmware, then try BLE setup again.");
    }
    return parseBleDeviceIdentityPayload(decodeBase64Utf8(characteristic.value));
  } catch (error) {
    if (error instanceof BleProvisioningError) {
      throw error;
    }
    const detail = describeBleReadError(error);
    throw new BleProvisioningError(
      "identity_unavailable",
      detail
        ? `Could not read this device identity over BLE (${detail}). Toggle Bluetooth, restart the app, and try again.`
        : "Could not read this device identity over BLE. Toggle Bluetooth, restart the app, and try again.",
    );
  } finally {
    if (connectedDevice) {
      await connectedDevice.cancelConnection().catch(() => undefined);
    }
  }
}

export async function readBleWifiNetworksFromDevice(deviceId: string): Promise<BleWifiNetworksResult> {
  await requestBlePermissions();
  const manager = await ensureBluetoothReady("load nearby Wi-Fi over BLE");
  let connectedDevice: Device | null = null;
  try {
    connectedDevice = await manager.connectToDevice(deviceId, { timeout: 10000 });
    if (Platform.OS === "android") {
      const deviceWithRequestedMtu = await connectedDevice.requestMTU(512).catch(() => connectedDevice as Device);
      connectedDevice = deviceWithRequestedMtu;
    }
    const discoveredDevice = await connectedDevice.discoverAllServicesAndCharacteristics();
    const scanned = await requestBleWifiScan(discoveredDevice);
    return {
      device: {
        id: discoveredDevice.id,
        name: discoveredDevice.name ?? discoveredDevice.localName ?? "PlantLab setup device",
      },
      networks: scanned.networks,
      truncated: scanned.truncated,
    };
  } catch (error) {
    if (error instanceof BleProvisioningError) {
      throw error;
    }
    throw new BleProvisioningError(
      "read_failed",
      "Could not scan nearby 2.4 GHz Wi-Fi over BLE. Retry, type the SSID manually, or use the SoftAP fallback.",
    );
  } finally {
    if (connectedDevice) {
      await connectedDevice.cancelConnection().catch(() => undefined);
    }
  }
}

export async function provisionDeviceOverBle(input: ProvisionDeviceOverBleInput): Promise<BleProvisioningStatus> {
  const payload = buildBleProvisioningPayload(input);
  await requestBlePermissions();
  const manager = await ensureBluetoothReady("provision the device over BLE");

  let connectedDevice: Device | null = null;
  let waitForStatus: ReturnType<typeof createProvisioningStatusWaiter> | null = null;
  let fallbackError: BleProvisioningError = new BleProvisioningError("connect_failed", "Could not connect to the PlantLab setup device over BLE.");
  try {
    input.onProgress?.({ phase: "connecting", message: "Connecting to PlantLab setup device..." });
    connectedDevice = await manager.connectToDevice(input.deviceId, { timeout: 10000 });
    if (Platform.OS === "android") {
      const deviceWithRequestedMtu = await connectedDevice.requestMTU(512).catch(() => connectedDevice as Device);
      connectedDevice = deviceWithRequestedMtu;
    }
    const discoveredDevice = await connectedDevice.discoverAllServicesAndCharacteristics();
    waitForStatus = createProvisioningStatusWaiter(discoveredDevice, input.timeoutMs ?? DEFAULT_PROVISIONING_STATUS_TIMEOUT_MS, input.onProgress);
    const initialStatus = await readInitialProvisioningStatus(discoveredDevice).catch(() => null);
    assertInitialProvisioningStatus(initialStatus);

    fallbackError = new BleProvisioningError("write_failed", "Could not send provisioning details over BLE. Retry provisioning.");
    input.onProgress?.({ phase: "sending", message: "Sending Wi-Fi credentials to the device..." });
    await discoveredDevice.writeCharacteristicWithResponseForService(
      BLE_PROVISIONING_SERVICE_UUID,
      BLE_PROVISIONING_WRITE_CHARACTERISTIC_UUID,
      encodeUtf8ToBase64(payload),
    );
    waitForStatus.markWritten();
    return await waitForStatus.promise;
  } catch (error) {
    if (error instanceof BleProvisioningError) {
      input.onProgress?.({ phase: "error", message: error.message });
      throw error;
    }
    input.onProgress?.({ phase: "error", message: fallbackError.message });
    throw fallbackError;
  } finally {
    waitForStatus?.cleanup();
    if (connectedDevice) {
      await connectedDevice.cancelConnection().catch(() => undefined);
    }
  }
}

async function ensureBluetoothReady(action: string): Promise<BleManager> {
  const manager = await getBleManager();
  const module = await import("react-native-ble-plx");
  let state = String(await manager.state());
  if (state === module.State.PoweredOn) {
    return manager;
  }

  if (state === module.State.Unknown || state === module.State.Resetting) {
    state = await waitForBluetoothState(manager, state);
    if (state === module.State.PoweredOn) {
      return manager;
    }
  }

  throw bluetoothStateError(state, action);
}

function waitForBluetoothState(manager: BleManager, initialState: string): Promise<string> {
  return new Promise((resolve) => {
    let lastState = initialState;
    let settled = false;
    let subscription: { remove: () => void } | null = null;
    const timeoutId = setTimeout(() => finish(lastState), BLUETOOTH_READY_WAIT_MS);
    subscription = manager.onStateChange((state) => {
      lastState = state;
      if (state === "PoweredOn" || state === "PoweredOff" || state === "Unauthorized" || state === "Unsupported") {
        finish(state);
      }
    }, true);
    if (settled) {
      subscription.remove();
    }

    function finish(state: string) {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeoutId);
      subscription?.remove();
      resolve(state);
    }
  });
}

function bluetoothStateError(state: string, action: string): BleProvisioningError {
  if (state === "Unauthorized") {
    return new BleProvisioningError("permission_denied", `Allow Bluetooth permission to ${action}, or type the SSID manually.`);
  }
  if (state === "Unsupported") {
    return new BleProvisioningError(
      "ble_unavailable",
      "This device or build does not support BLE provisioning. Type the SSID manually or use SoftAP fallback.",
    );
  }
  if (state === "Unknown" || state === "Resetting") {
    return new BleProvisioningError("bluetooth_off", `Bluetooth is still initializing. Keep Bluetooth on and retry to ${action}.`);
  }
  return new BleProvisioningError("bluetooth_off", `Turn on Bluetooth to ${action}, or type the SSID manually.`);
}

async function requestBleWifiScan(device: Device): Promise<Omit<BleWifiNetworksResult, "device">> {
  const baselineScanId = await readBleWifiNetworksSnapshotScanId(device);
  const firstPage = await requestBleWifiScanPayload(device, { command: "wifi_scan_start" }, { expectedCursor: 0, minimumScanId: baselineScanId ?? 0 });
  let parsed = parseBleWifiNetworksPayload(firstPage);
  const scanId = parsed.scanId;
  let networks = parsed.networks;
  let truncated = parsed.truncated;
  let nextCursor = parsed.nextCursor;
  if (nextCursor !== null && scanId === null) {
    throw new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually.");
  }

  while (nextCursor !== null) {
    const pageCommand: Record<string, unknown> = { command: "wifi_scan_page", cursor: nextCursor };
    pageCommand.scan_id = scanId;
    const pagePayload = await requestBleWifiScanPayload(device, pageCommand, { expectedCursor: nextCursor, expectedScanId: scanId });
    parsed = parseBleWifiNetworksPayload(pagePayload);
    networks = mergeBleWifiNetworks([...networks, ...parsed.networks]);
    truncated = truncated || parsed.truncated;
    nextCursor = parsed.nextCursor;
  }

  return { networks, truncated };
}

async function readBleWifiNetworksSnapshotScanId(device: Device): Promise<number | null> {
  try {
    const characteristic = await device.readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID);
    if (!characteristic.value) {
      return null;
    }
    return parseBleWifiNetworksPayload(decodeBase64Utf8(characteristic.value)).scanId;
  } catch {
    return null;
  }
}

function requestBleWifiScanPayload(device: Device, command: Record<string, unknown>, request: BleWifiScanPayloadRequest): Promise<string> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let commandWritten = false;
    let pollId: ReturnType<typeof setInterval> | null = null;
    const subscription = device.monitorCharacteristicForService(
      BLE_PROVISIONING_SERVICE_UUID,
      BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID,
      (error, characteristic) => {
        if (error) {
          finish(undefined, new BleProvisioningError("scan_notify_failed", "BLE Wi-Fi scan notifications failed. Retry or type the SSID manually."));
          return;
        }
        handleCharacteristicValue(characteristic?.value, "notify");
      },
    );

    const timeoutId = setTimeout(() => {
      finish(
        undefined,
        new BleProvisioningError(
          "wifi_scan_timeout",
          "The device did not finish scanning nearby 2.4 GHz Wi-Fi. Retry or type the SSID manually.",
        ),
      );
    }, DEFAULT_WIFI_SCAN_TIMEOUT_MS);

    function finish(payload?: string, error?: BleProvisioningError) {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeoutId);
      if (pollId) {
        clearInterval(pollId);
      }
      subscription.remove();
      if (error) {
        reject(error);
      } else {
        resolve(payload ?? "");
      }
    }

    function logWifiPayloadEvent(message: string) {
      console.log(`[ble-wifi] ${message}`);
    }

    function handleCharacteristicValue(value: string | null | undefined, source: BleWifiPayloadSource) {
      if (!value || settled) {
        if (!value) {
          logWifiPayloadEvent(`${source}: empty characteristic value`);
        }
        return;
      }
      if (!commandWritten) {
        logWifiPayloadEvent(`${source}: ignored value before scan command write`);
        return;
      }
      let payload: string;
      try {
        payload = decodeBase64Utf8(value);
      } catch (error) {
        finish(
          undefined,
          error instanceof BleProvisioningError
            ? error
            : new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually."),
        );
        return;
      }
      logWifiPayloadEvent(`${source}: received bytes=${payload.length} shape=${describeWifiPayloadForLog(payload)}`);
      let parsed: ParsedBleWifiNetworksPayload;
      try {
        parsed = parseBleWifiNetworksPayload(payload);
      } catch (error) {
        finish(
          undefined,
          error instanceof BleProvisioningError
            ? error
            : new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually."),
        );
        return;
      }
      logWifiPayloadEvent(
        `${source}: parsed status=${parsed.status} scan_id=${parsed.scanId ?? "null"} cursor=${parsed.cursor} next=${
          parsed.nextCursor ?? "null"
        } networks=${parsed.networks.length}`,
      );
      if (parsed.status === "idle" || parsed.status === "scanning") {
        logWifiPayloadEvent(`${source}: waiting for scan completion`);
        return;
      }
      if (!isExpectedScanPayload(parsed, request)) {
        logWifiPayloadEvent(
          `${source}: dropped stale/unexpected payload expected_scan_id=${request.expectedScanId ?? "none"} minimum_scan_id=${
            request.minimumScanId ?? "none"
          } expected_cursor=${request.expectedCursor}`,
        );
        return;
      }
      if (parsed.status === "error") {
        finish(undefined, new BleProvisioningError("wifi_scan_error", "The device could not scan nearby Wi-Fi. Retry or type the SSID manually."));
        return;
      }
      if (parsed.status === "timeout") {
        finish(undefined, new BleProvisioningError("wifi_scan_timeout", "The device Wi-Fi scan timed out. Retry or type the SSID manually."));
        return;
      }
      if (parsed.cursor !== request.expectedCursor) {
        logWifiPayloadEvent(`${source}: dropped cursor=${parsed.cursor}; expected_cursor=${request.expectedCursor}`);
        return;
      }
      logWifiPayloadEvent(`${source}: accepted scan_id=${parsed.scanId ?? "null"} networks=${parsed.networks.map((network) => network.ssid).join(",")}`);
      finish(payload);
    }

    device
      .writeCharacteristicWithResponseForService(
        BLE_PROVISIONING_SERVICE_UUID,
        BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID,
        encodeUtf8ToBase64(JSON.stringify(command)),
      )
      .then(() => {
        commandWritten = true;
        device
          .readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID)
          .then((characteristic) => handleCharacteristicValue(characteristic.value, "immediate_read"))
          .catch(() => undefined);
        pollId = setInterval(() => {
          device
            .readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID)
            .then((characteristic) => handleCharacteristicValue(characteristic.value, "poll_read"))
            .catch(() => {
              finish(undefined, new BleProvisioningError("read_failed", "Could not read nearby Wi-Fi over BLE. Retry or type the SSID manually."));
            });
        }, BLE_WIFI_SCAN_POLL_MS);
      })
      .catch(() => {
        finish(undefined, new BleProvisioningError("scan_request_failed", "Could not request a BLE Wi-Fi scan. Retry or type the SSID manually."));
      });
  });
}

function describeWifiPayloadForLog(payload: string): string {
  const normalized = payload.trim();
  if (!normalized) {
    return "empty";
  }
  if (normalized.startsWith("{") && normalized.endsWith("}")) {
    return "json";
  }
  return `text:${normalized.slice(0, 24).replace(/\s+/g, " ")}`;
}

async function readInitialProvisioningStatus(device: Device): Promise<BleProvisioningStatus | null> {
  const characteristic = await device.readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID);
  if (!characteristic.value) {
    return null;
  }
  return parseBleProvisioningStatus(decodeBase64Utf8(characteristic.value));
}

function assertInitialProvisioningStatus(status: BleProvisioningStatus | null) {
  if (!status || status.ready || status.state === "PROVISIONING_BLE") {
    return;
  }
  if (isBleProvisioningSuccess(status)) {
    throw new BleProvisioningError("already_committed", "This setup payload was already saved. Restart provisioning mode to retry.");
  }
  if (isBleProvisioningFailure(status)) {
    const message = status.error ? provisioningErrorMessage(status.error) : "The device is not ready for BLE provisioning.";
    throw new BleProvisioningError(status.error ?? "provisioning_failed", message);
  }
  throw new BleProvisioningError("busy", "The device is not ready for BLE provisioning. Wait a moment and retry.");
}

function createProvisioningStatusWaiter(
  device: Device,
  timeoutMs: number,
  onProgress?: (progress: BleProvisioningProgress) => void,
): {
  promise: Promise<BleProvisioningStatus>;
  markWritten: () => void;
  cleanup: () => void;
} {
  let settled = false;
  let writeCompleted = false;
  let sawCurrentAttemptProgress = false;
  let pollId: ReturnType<typeof setInterval> | null = null;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let subscriptionRemoved = false;
  let resolvePromise: (status: BleProvisioningStatus) => void = () => undefined;
  let rejectPromise: (error: BleProvisioningError) => void = () => undefined;
  const promise = new Promise<BleProvisioningStatus>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
    timeoutId = setTimeout(() => {
      settle(undefined, new BleProvisioningError("provisioning_timeout", "Timed out waiting for the device to confirm provisioning."));
    }, timeoutMs);
  });
  void promise.catch(() => undefined);

  const subscription = device.monitorCharacteristicForService(
    BLE_PROVISIONING_SERVICE_UUID,
    BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID,
    (error, characteristic) => {
      if (error) {
        settle(undefined, new BleProvisioningError("read_failed", "BLE status notifications failed. Retry provisioning."));
        return;
      }
      handleCharacteristicValue(characteristic?.value);
    },
  );

  function markWritten() {
    writeCompleted = true;
    onProgress?.({ phase: "committing", message: "Waiting for device confirmation..." });
    const pollStatus = () => {
      device
        .readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID)
        .then((characteristic) => handleCharacteristicValue(characteristic.value))
        .catch(() => undefined);
    };
    pollStatus();
    pollId = setInterval(pollStatus, BLE_PROVISIONING_STATUS_POLL_MS);
  }

  function cleanup() {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (pollId) {
      clearInterval(pollId);
    }
    if (!subscriptionRemoved) {
      subscriptionRemoved = true;
      subscription.remove();
    }
  }

  function handleCharacteristicValue(value?: string | null) {
    if (!value || settled || !writeCompleted) {
      return;
    }
    let status: BleProvisioningStatus;
    try {
      status = parseBleProvisioningStatus(decodeBase64Utf8(value));
    } catch {
      settle(undefined, new BleProvisioningError("status_parse_failed", "The device sent an unreadable provisioning status."));
      return;
    }
    if (isBleProvisioningSuccess(status)) {
      onProgress?.({ phase: "success", message: provisioningStatusMessage(status), status });
      settle(status);
      return;
    }
    if (isBleProvisioningFailure(status)) {
      if (status.state === "PROVISIONING_BLE" && !sawCurrentAttemptProgress) {
        return;
      }
      const message = status.error ? provisioningErrorMessage(status.error) : "The device rejected provisioning details. Retry provisioning.";
      onProgress?.({ phase: "error", message, status });
      settle(undefined, new BleProvisioningError(status.error ?? "provisioning_failed", message));
      return;
    }
    const phase =
      status.state === "WIFI_CONNECTING"
        ? "connecting"
        : status.state === "PROVISIONING_COMMITTING"
          ? "committing"
          : "sending";
    sawCurrentAttemptProgress = true;
    onProgress?.({ phase, message: provisioningStatusMessage(status), status });
  }

  function settle(status?: BleProvisioningStatus, error?: BleProvisioningError) {
    if (settled) {
      return;
    }
    settled = true;
    cleanup();
    if (error) {
      rejectPromise(error);
    } else if (status) {
      resolvePromise(status);
    }
  }

  return { promise, markWritten, cleanup };
}

function isExpectedScanPayload(parsed: ParsedBleWifiNetworksPayload, request: BleWifiScanPayloadRequest): boolean {
  if (request.expectedScanId !== undefined && request.expectedScanId !== null && parsed.scanId !== request.expectedScanId) {
    return false;
  }
  if (request.minimumScanId !== undefined && request.minimumScanId !== null) {
    return parsed.scanId !== null && parsed.scanId > request.minimumScanId;
  }
  return true;
}

export async function loadBleWifiNetworks(): Promise<BleWifiNetworksResult | { devices: BleProvisioningDevice[] }> {
  const devices = await scanForBleProvisioningDevices();
  if (devices.length === 0) {
    throw new BleProvisioningError("no_devices", "No PlantLab BLE setup device was found. Keep the master in BLE provisioning mode and try again.");
  }
  if (devices.length > 1) {
    return { devices };
  }
  return readBleWifiNetworksFromDevice(devices[0].id);
}

function isProvisioningDevice(device: Device): boolean {
  const name = device.name ?? device.localName ?? "";
  if (name.startsWith(PLANTLAB_SETUP_NAME_PREFIX)) {
    return true;
  }
  return (device.serviceUUIDs ?? []).some((uuid) => uuid.toLowerCase() === BLE_PROVISIONING_SERVICE_UUID);
}

function parseBleDeviceIdentityPayload(payload: string): BleDeviceIdentity {
  let parsed: unknown;
  try {
    parsed = JSON.parse(payload);
  } catch {
    throw new BleProvisioningError("invalid_identity", "The BLE device identity was not readable. Restart BLE setup on the device, then try again.");
  }

  if (!parsed || typeof parsed !== "object") {
    throw new BleProvisioningError("invalid_identity", "The BLE device identity was not readable. Restart BLE setup on the device, then try again.");
  }
  const body = parsed as Record<string, unknown>;
  const deviceId = stringField(body.device_id);
  const hardwareDeviceId = stringField(body.hardware_device_id) || deviceId;
  if (!deviceId || !hardwareDeviceId) {
    throw new BleProvisioningError("invalid_identity", "The BLE device identity did not include a device ID. Update the device firmware, then try BLE setup again.");
  }

  return {
    source: stringField(body.source) === "esp32-ble" ? "esp32-ble" : "esp32-ble",
    schemaVersion: numberField(body.schema_version) ?? 1,
    deviceId,
    hardwareDeviceId,
    hardwareModel: stringField(body.hardware_model) || undefined,
    hardwareVersion: stringField(body.hardware_version) || undefined,
    softwareVersion: stringField(body.software_version) || undefined,
    nodeRole: stringField(body.node_role) || undefined,
    displayName: stringField(body.display_name) || undefined,
    bleName: stringField(body.ble_name) || undefined,
    serialNumber: stringField(body.serial_number) || undefined,
  };
}

function stringField(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function describeBleReadError(error: unknown): string {
  if (!error || typeof error !== "object") {
    return "";
  }
  const body = error as Record<string, unknown>;
  const candidates = [
    typeof body.errorCode === "number" ? `code ${body.errorCode}` : "",
    typeof body.attErrorCode === "number" ? `att ${body.attErrorCode}` : "",
    typeof body.reason === "string" ? body.reason : "",
    typeof body.message === "string" ? body.message : "",
  ].filter(Boolean);
  const normalized = candidates.join(": ").replace(/\s+/g, " ").trim();
  return normalized.length > 180 ? `${normalized.slice(0, 177)}...` : normalized;
}

function displaySuffixForBleDevice(name: string): string | undefined {
  const normalized = name.trim();
  if (!normalized) {
    return undefined;
  }
  const suffix = normalized.split("-").pop()?.trim();
  return suffix && suffix !== normalized ? suffix : undefined;
}

function parseBleWifiNetworksPayload(payload: string): ParsedBleWifiNetworksPayload {
  let parsed: unknown;
  try {
    parsed = JSON.parse(payload);
  } catch {
    throw new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually.");
  }

  if (!parsed || typeof parsed !== "object") {
    throw new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually.");
  }

  const body = parsed as { scan_id?: unknown; networks?: unknown; truncated?: unknown; status?: unknown; cursor?: unknown; next_cursor?: unknown };
  if (!Array.isArray(body.networks)) {
    throw new BleProvisioningError("invalid_payload", "The BLE Wi-Fi list was not readable. Type the SSID manually.");
  }

  const bySsid = new Map<string, BleWifiNetwork>();
  for (const item of body.networks) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const network = item as { ssid?: unknown; rssi?: unknown };
    if (typeof network.ssid !== "string") {
      continue;
    }
    const ssid = network.ssid.trim();
    if (!ssid) {
      continue;
    }
    const rssi = typeof network.rssi === "number" && Number.isFinite(network.rssi) ? network.rssi : undefined;
    const existing = bySsid.get(ssid);
    if (!existing || (typeof rssi === "number" && (existing.rssi === undefined || rssi > existing.rssi))) {
      bySsid.set(ssid, typeof rssi === "number" ? { ssid, rssi } : { ssid });
    }
  }

  return {
    scanId: typeof body.scan_id === "number" && Number.isFinite(body.scan_id) ? body.scan_id : null,
    networks: sortBleWifiNetworks(Array.from(bySsid.values())),
    truncated: body.truncated === true,
    status: typeof body.status === "string" ? body.status : "ready",
    cursor: typeof body.cursor === "number" && Number.isFinite(body.cursor) ? body.cursor : 0,
    nextCursor: typeof body.next_cursor === "number" && Number.isFinite(body.next_cursor) ? body.next_cursor : null,
  };
}

function mergeBleWifiNetworks(networks: BleWifiNetwork[]): BleWifiNetwork[] {
  const bySsid = new Map<string, BleWifiNetwork>();
  for (const network of networks) {
    const existing = bySsid.get(network.ssid);
    if (!existing || (network.rssi !== undefined && (existing.rssi === undefined || network.rssi > existing.rssi))) {
      bySsid.set(network.ssid, network);
    }
  }
  return sortBleWifiNetworks(Array.from(bySsid.values()));
}

function sortBleWifiNetworks(networks: BleWifiNetwork[]): BleWifiNetwork[] {
  return networks.sort((left, right) => {
    const leftRssi = left.rssi ?? -127;
    const rightRssi = right.rssi ?? -127;
    if (leftRssi === rightRssi) {
      return left.ssid.localeCompare(right.ssid);
    }
    return rightRssi - leftRssi;
  });
}
