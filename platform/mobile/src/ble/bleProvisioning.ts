import { PermissionsAndroid, Platform } from "react-native";
import { decode as decodeBase64, encode as encodeBase64 } from "base-64";
import type { BleManager, Device } from "react-native-ble-plx";

export const BLE_PROVISIONING_SERVICE_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901";
export const BLE_PROVISIONING_WRITE_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902";
export const BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903";
export const BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a904";
export const BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a905";

const PLANTLAB_SETUP_NAME_PREFIX = "PlantLab-Setup";
const DEFAULT_SCAN_TIMEOUT_MS = 6000;
const DEFAULT_WIFI_SCAN_TIMEOUT_MS = 20000;
const BLE_WIFI_SCAN_POLL_MS = 700;

export type BleProvisioningDevice = {
  id: string;
  name: string;
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

export class BleProvisioningError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "BleProvisioningError";
    this.code = code;
  }
}

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
  const manager = await getBleManager();
  const module = await import("react-native-ble-plx");
  const state = await manager.state();
  if (state !== module.State.PoweredOn) {
    throw new BleProvisioningError("bluetooth_off", "Turn on Bluetooth to load nearby Wi-Fi over BLE, or type the SSID manually.");
  }

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
      });
    });
  });
}

export async function readBleWifiNetworksFromDevice(deviceId: string): Promise<BleWifiNetworksResult> {
  await requestBlePermissions();
  const manager = await getBleManager();
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

async function requestBleWifiScan(device: Device): Promise<Omit<BleWifiNetworksResult, "device">> {
  const baselineScanId = await readBleWifiNetworksSnapshotScanId(device);
  const firstPage = await requestBleWifiScanPayload(device, { command: "wifi_scan_start" }, { expectedCursor: 0, minimumScanId: baselineScanId });
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
    return parseBleWifiNetworksPayload(decodeBase64(characteristic.value)).scanId;
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
        handleCharacteristicValue(characteristic?.value);
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

    function handleCharacteristicValue(value?: string | null) {
      if (!value || settled) {
        return;
      }
      if (!commandWritten) {
        return;
      }
      const payload = decodeBase64(value);
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
      if (parsed.status === "idle" || parsed.status === "scanning") {
        return;
      }
      if (!isExpectedScanPayload(parsed, request)) {
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
        return;
      }
      finish(payload);
    }

    device
      .writeCharacteristicWithResponseForService(
        BLE_PROVISIONING_SERVICE_UUID,
        BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID,
        encodeBase64(JSON.stringify(command)),
      )
      .then(() => {
        commandWritten = true;
        pollId = setInterval(() => {
          device
            .readCharacteristicForService(BLE_PROVISIONING_SERVICE_UUID, BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID)
            .then((characteristic) => handleCharacteristicValue(characteristic.value))
            .catch(() => undefined);
        }, BLE_WIFI_SCAN_POLL_MS);
      })
      .catch(() => {
        finish(undefined, new BleProvisioningError("scan_request_failed", "Could not request a BLE Wi-Fi scan. Retry or type the SSID manually."));
      });
  });
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
