import { useEffect, useMemo, useState } from "react";
import { Keyboard, Linking, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { BarcodeScanningResult, CameraView, useCameraPermissions } from "expo-camera";

import { requestDeviceClaimToken, requestDeviceSetupCode } from "@/api/devices";
import type { DeviceSetupHandoff } from "@/api/devices";
import { getApiBaseUrl } from "@/api/config";
import {
  BleProvisioningError,
  type BleProvisioningDevice,
  type BleProvisioningProgress,
  type BleWifiNetworksResult,
  loadBleWifiNetworks,
  provisionDeviceOverBle,
  readBleDeviceIdentity,
  readBleWifiNetworksFromDevice,
  scanForBleProvisioningDevices,
} from "@/ble/bleProvisioning";
import { maskSecret } from "@/ble/bleProvisioningPayload";
import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

const DEFAULT_DEVICE_NAME = "esp32";
const DEFAULT_DEVICE_LOCATION = "1";
type AddDeviceStep = "find_device" | "wifi_provisioning";

export function AddDeviceScreen() {
  const { token } = useSession();
  const [deviceName, setDeviceName] = useState("");
  const [location, setLocation] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [wifiSsid, setWifiSsid] = useState("");
  const [isManualWifiSsid, setIsManualWifiSsid] = useState(false);
  const [wifiPassword, setWifiPassword] = useState("");
  const [showWifiPassword, setShowWifiPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [handoff, setHandoff] = useState<DeviceSetupHandoff | null>(null);
  const [isScannerOpen, setIsScannerOpen] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [discoveredWifiSsids, setDiscoveredWifiSsids] = useState<string[]>([]);
  const [wifiScanMessage, setWifiScanMessage] = useState<string | null>(null);
  const [isLoadingWifiNetworks, setIsLoadingWifiNetworks] = useState(false);
  const [bleDeviceOptions, setBleDeviceOptions] = useState<BleProvisioningDevice[]>([]);
  const [selectedBleDevice, setSelectedBleDevice] = useState<BleProvisioningDevice | null>(null);
  const [isBleDevicePickerOpen, setIsBleDevicePickerOpen] = useState(false);
  const [bleDevicePickerMode, setBleDevicePickerMode] = useState<"identity" | "wifi">("identity");
  const [isFindingBleDevice, setIsFindingBleDevice] = useState(false);
  const [isProvisioningOverBle, setIsProvisioningOverBle] = useState(false);
  const [bleProvisioningMessage, setBleProvisioningMessage] = useState<string | null>(null);
  const [bleProvisioningTone, setBleProvisioningTone] = useState<"idle" | "success" | "error">("idle");
  const [wifiPickerOpenSignal, setWifiPickerOpenSignal] = useState(0);
  const [step, setStep] = useState<AddDeviceStep>("find_device");
  const [showSerialFallback, setShowSerialFallback] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const wifiSsidOptions = useMemo(() => mergeWifiSsidOptions(discoveredWifiSsids), [discoveredWifiSsids]);

  const canSubmit = serialNumber.trim().length > 0 && !isSubmitting;
  const canConfirmWifiDetails = wifiSsid.trim().length > 0 && wifiPassword.length > 0;
  const blePlatformUrl = handoff?.platformUrl?.trim() || getApiBaseUrl().trim();
  const canProvisionOverBle = Boolean(handoff?.setupToken && blePlatformUrl && canConfirmWifiDetails && !isProvisioningOverBle);

  function updateWifiSsid(value: string) {
    setWifiSsid(value);
    setBleProvisioningTone("idle");
    setBleProvisioningMessage(null);
  }

  function updateWifiPassword(value: string) {
    setWifiPassword(value);
    setBleProvisioningTone("idle");
    setBleProvisioningMessage(null);
  }

  async function onSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await requestDeviceSetupCode(
        {
          serialNumber: serialNumber.trim(),
          deviceName: deviceName.trim() || DEFAULT_DEVICE_NAME,
          location: location.trim() || DEFAULT_DEVICE_LOCATION,
        },
        token ?? undefined,
      );
      setUsedMock(result.usedMock);
      setHandoff(result.handoff);
      setSelectedBleDevice(null);
      setBleProvisioningMessage(null);
      setBleProvisioningTone("idle");
      setStep("wifi_provisioning");
    } catch (err) {
      setUsedMock(false);
      setHandoff(null);
      setError(err instanceof Error ? err.message : "Unable to start device setup.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function startBleIdentityOnboarding() {
    setError(null);
    setWifiScanMessage(null);
    setBleProvisioningMessage(null);
    setBleProvisioningTone("idle");
    setShowSerialFallback(false);
    setIsFindingBleDevice(true);
    try {
      const devices = await scanForBleProvisioningDevices();
      if (devices.length === 0) {
        throw new BleProvisioningError(
          "no_devices",
          "No PlantLab BLE setup device was found. Keep the master in BLE provisioning mode and try again.",
        );
      }
      if (devices.length > 1) {
        setBleDeviceOptions(devices);
        setBleDevicePickerMode("identity");
        setIsBleDevicePickerOpen(true);
        setWifiScanMessage("Choose the PlantLab device in setup mode. Use the name suffix or strongest signal if needed.");
        return;
      }
      await createClaimTokenFromBleDevice(devices[0]);
    } catch (err) {
      setShowSerialFallback(true);
      setError(err instanceof Error ? err.message : "Could not find a PlantLab BLE setup device.");
    } finally {
      setIsFindingBleDevice(false);
    }
  }

  async function createClaimTokenFromBleDevice(device: BleProvisioningDevice) {
    setIsBleDevicePickerOpen(false);
    setIsSubmitting(true);
    setError(null);
    try {
      const identity = await readBleDeviceIdentity(device.id);
      const deviceWithIdentity = {
        ...device,
        name: identity.bleName || device.name,
        displaySuffix: shortHardwareSuffix(identity.hardwareDeviceId) ?? device.displaySuffix,
        identity,
      };
      const result = await requestDeviceClaimToken(
        {
          deviceName: deviceName.trim() || DEFAULT_DEVICE_NAME,
          location: location.trim() || DEFAULT_DEVICE_LOCATION,
          deviceIdentity: identity,
        },
        token ?? undefined,
      );
      setUsedMock(result.usedMock);
      setHandoff(result.handoff);
      setSelectedBleDevice(deviceWithIdentity);
      setBleProvisioningTone("idle");
      setBleProvisioningMessage(`Connected to ${deviceWithIdentity.name}.`);
      setStep("wifi_provisioning");
      void loadSelectedBleDeviceWifiNetworks(deviceWithIdentity);
    } catch (err) {
      setUsedMock(false);
      setHandoff(null);
      setSelectedBleDevice(null);
      setShowSerialFallback(true);
      setError(err instanceof Error ? err.message : "Unable to read device identity over BLE.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function openSoftApSetup() {
    if (!handoff?.continueSetupUrl) {
      return;
    }
    await Linking.openURL(handoff.continueSetupUrl);
  }

  async function openScanner() {
    setScanError(null);
    if (!cameraPermission?.granted) {
      const permission = await requestCameraPermission();
      if (!permission.granted) {
        setScanError("Camera access is required to scan the device QR code. You can still type the serial number manually.");
        return;
      }
    }
    setIsScannerOpen(true);
  }

  function onBarcodeScanned(result: BarcodeScanningResult) {
    const serial = extractSerialNumberFromQr(result.data);
    if (!serial) {
      setScanError("QR code scanned, but no serial number was found. Type the serial number manually or scan the device label again.");
      return;
    }
    setSerialNumber(serial);
    setIsScannerOpen(false);
    setScanError(null);
  }

  async function loadDeviceWifiNetworks() {
    if (selectedBleDevice) {
      await loadSelectedBleDeviceWifiNetworks(selectedBleDevice);
      return;
    }
    setWifiScanMessage(null);
    setIsLoadingWifiNetworks(true);
    try {
      const result = await loadBleWifiNetworks();
      if ("devices" in result) {
        setBleDeviceOptions(result.devices);
        setBleDevicePickerMode("wifi");
        setIsBleDevicePickerOpen(true);
        setWifiScanMessage("Multiple PlantLab BLE setup devices were found. Select the device to read nearby Wi-Fi.");
        return;
      }
      applyBleWifiNetworksResult(result);
    } catch (err) {
      setWifiScanMessage(wifiScanErrorMessage(err));
    } finally {
      setIsLoadingWifiNetworks(false);
    }
  }

  async function loadSelectedBleDeviceWifiNetworks(device: BleProvisioningDevice) {
    setIsBleDevicePickerOpen(false);
    setWifiScanMessage("Scanning nearby 2.4 GHz Wi-Fi...");
    setIsLoadingWifiNetworks(true);
    try {
      const result = await readBleWifiNetworksFromDevice(device.id);
      applyBleWifiNetworksResult(result, device);
    } catch (err) {
      setWifiScanMessage(wifiScanErrorMessage(err));
    } finally {
      setIsLoadingWifiNetworks(false);
    }
  }

  function applyBleWifiNetworksResult(result: BleWifiNetworksResult, sourceDevice?: BleProvisioningDevice) {
    const existingIdentity =
      sourceDevice?.identity ?? (selectedBleDevice?.id === result.device.id ? selectedBleDevice.identity : undefined);
    setSelectedBleDevice({
      ...result.device,
      identity: existingIdentity,
      displaySuffix: existingIdentity ? shortHardwareSuffix(existingIdentity.hardwareDeviceId) : result.device.displaySuffix,
    });
    const ssids = mergeWifiSsidOptions(result.networks.map((network) => network.ssid));
    setDiscoveredWifiSsids(ssids);
    setBleProvisioningTone("idle");
    setBleProvisioningMessage(null);
    if (ssids.length > 0) {
      setWifiPickerOpenSignal((value) => value + 1);
      setWifiScanMessage(
        `Loaded ${ssids.length} nearby 2.4 GHz Wi-Fi network(s) from ${result.device.name}.${
          result.truncated ? " The BLE list was truncated; manual entry is still available." : ""
        }`,
      );
    } else {
      setIsManualWifiSsid(true);
      setWifiScanMessage("No 2.4 GHz networks were reported by this device. You can still type your Wi-Fi name.");
    }
  }

  async function sendProvisioningOverBle() {
    if (!handoff?.setupToken || !blePlatformUrl || !canConfirmWifiDetails) {
      return;
    }
    Keyboard.dismiss();
    setBleProvisioningTone("idle");
    setBleProvisioningMessage(null);
    setIsProvisioningOverBle(true);
    try {
      const device = selectedBleDevice ?? (await findSingleBleProvisioningDevice());
      if (!device) {
        setBleProvisioningTone("error");
        setBleProvisioningMessage("Select the PlantLab BLE setup device, then retry provisioning.");
        return;
      }
      setSelectedBleDevice(device);
      await provisionDeviceOverBle({
        deviceId: device.id,
        ssid: wifiSsid,
        password: wifiPassword,
        setupToken: handoff.setupToken,
        platformUrl: blePlatformUrl,
        backendUrl: handoff.provisioningApiUrl,
        onProgress: handleBleProvisioningProgress,
      });
      setBleProvisioningTone("success");
    } catch (err) {
      setBleProvisioningTone("error");
      setBleProvisioningMessage(provisioningErrorMessage(err));
    } finally {
      setIsProvisioningOverBle(false);
    }
  }

  async function findSingleBleProvisioningDevice(): Promise<BleProvisioningDevice | null> {
    const devices = await scanForBleProvisioningDevices();
    if (devices.length === 0) {
      throw new BleProvisioningError("no_devices", "No PlantLab BLE setup device was found. Keep the master in BLE provisioning mode and try again.");
    }
    if (devices.length > 1) {
      setBleDeviceOptions(devices);
      setBleDevicePickerMode("wifi");
      setIsBleDevicePickerOpen(true);
      return null;
    }
    return devices[0];
  }

  function handleBleProvisioningProgress(progress: BleProvisioningProgress) {
    setBleProvisioningMessage(progress.message);
    if (progress.phase === "success") {
      setBleProvisioningTone("success");
    } else if (progress.phase === "error") {
      setBleProvisioningTone("error");
    } else {
      setBleProvisioningTone("idle");
    }
  }

  return (
    <Screen scrollToTopSignal={step}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>DEVICE ONBOARDING</Text>
        <Text style={styles.title}>{step === "find_device" ? "Add PlantLab device" : "Connect Wi-Fi"}</Text>
        <Text style={styles.subtitle}>
          {step === "find_device"
            ? "Find a PlantLab device over BLE, then continue with Wi-Fi provisioning."
            : "Choose a Wi-Fi network reported by the device, then send credentials over BLE."}
        </Text>
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {step === "find_device" ? (
        <Card>
          <Text style={styles.cardTitle}>Device details</Text>
          <LabeledInput label="Device name" value={deviceName} onChangeText={setDeviceName} placeholder={DEFAULT_DEVICE_NAME} />
          <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_NAME}.</Text>
          <LabeledInput label="Location" value={location} onChangeText={setLocation} placeholder={DEFAULT_DEVICE_LOCATION} />
          <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_LOCATION}.</Text>
          <PrimaryButton
            label={isFindingBleDevice || isSubmitting ? "Finding PlantLab device..." : "Find PlantLab device"}
            onPress={startBleIdentityOnboarding}
            disabled={isFindingBleDevice || isSubmitting}
          />
          <Text style={styles.meta}>Long-press GPIO14 first so the master advertises as PlantLab-Setup.</Text>
        </Card>
      ) : null}

      {step === "find_device" && showSerialFallback ? (
        <Card>
          <Text style={styles.cardTitle}>QR or serial fallback</Text>
          <Text style={styles.cardSubtitle}>Use this only when BLE setup cannot find or read the device.</Text>
          <LabeledInput label="Serial number" value={serialNumber} onChangeText={setSerialNumber} placeholder="SN-ESP32-001" />
          <PrimaryButton label="Scan QR code" tone="secondary" onPress={openScanner} />
          {scanError ? <Text style={styles.error}>{scanError}</Text> : null}
          <PrimaryButton label={isSubmitting ? "Verifying..." : "Verify serial and create setup token"} onPress={onSubmit} disabled={!canSubmit} />
        </Card>
      ) : null}

      {step === "wifi_provisioning" && handoff ? (
        <Card>
          <Text style={styles.cardTitle}>BLE provisioning</Text>
          <Text style={styles.cardSubtitle}>
            PlantLab can only join 2.4 GHz Wi-Fi. If your network is not listed, type its name.
          </Text>
          <PrimaryButton
            label={isLoadingWifiNetworks ? "Scanning nearby 2.4 GHz Wi-Fi..." : "Scan nearby 2.4 GHz Wi-Fi"}
            onPress={loadDeviceWifiNetworks}
            disabled={isLoadingWifiNetworks}
          />
          {wifiScanMessage ? <Text style={styles.meta}>{wifiScanMessage}</Text> : null}
          {selectedBleDevice ? <Text style={styles.meta}>Selected BLE device: {bleDeviceLabel(selectedBleDevice)}</Text> : null}
          <WifiSsidPicker
            manualMode={isManualWifiSsid}
            onChangeManualMode={setIsManualWifiSsid}
            onChangeSsid={updateWifiSsid}
            openSignal={wifiPickerOpenSignal}
            options={wifiSsidOptions}
            value={wifiSsid}
          />
          <PasswordInput
            label="Home Wi-Fi password"
            onChangeText={updateWifiPassword}
            onToggleVisible={() => setShowWifiPassword((value) => !value)}
            placeholder="Required for BLE provisioning"
            value={wifiPassword}
            visible={showWifiPassword}
          />
          {handoff.setupToken ? <Text style={styles.meta}>Setup token: {maskSecret(handoff.setupToken)}</Text> : null}
          <PrimaryButton
            label={isProvisioningOverBle ? "Provisioning over BLE..." : "Send provisioning over BLE"}
            onPress={sendProvisioningOverBle}
            disabled={!canProvisionOverBle}
          />
          {!canConfirmWifiDetails ? <Text style={styles.meta}>Select or type your Wi-Fi name, then enter the Wi-Fi password to continue.</Text> : null}
          {!blePlatformUrl ? <Text style={styles.error}>A reachable platform URL is required before BLE provisioning.</Text> : null}
          {bleProvisioningMessage ? (
            <Text style={bleProvisioningTone === "success" ? styles.success : bleProvisioningTone === "error" ? styles.error : styles.meta}>
              {bleProvisioningMessage}
            </Text>
          ) : null}
          {bleProvisioningTone === "error" ? (
            <PrimaryButton label="Retry BLE provisioning" tone="secondary" onPress={sendProvisioningOverBle} disabled={!canProvisionOverBle} />
          ) : null}
        </Card>
      ) : null}

      {step === "wifi_provisioning" && handoff && bleProvisioningTone === "error" ? (
        <Card>
          <Text style={styles.cardTitle}>Existing Wi-Fi setup fallback</Text>
          <Text style={styles.cardSubtitle}>
            SoftAP setup is still available for compatibility. Connect the phone to PlantLab-Setup, wait for the network handoff,
            then open the setup page.
          </Text>
          <PrimaryButton label="Open PlantLab-Setup page" onPress={openSoftApSetup} />
        </Card>
      ) : null}

      <PrimaryButton label="Back to devices" tone="secondary" onPress={() => router.back()} />

      <Modal animationType="slide" visible={isScannerOpen} onRequestClose={() => setIsScannerOpen(false)}>
        <View style={styles.scannerScreen}>
          <View style={styles.scannerHeader}>
            <Text style={styles.scannerTitle}>Scan device QR code</Text>
            <Text style={styles.scannerSubtitle}>Point the camera at the PlantLab device label. You can close this and type the SN manually.</Text>
          </View>
          <CameraView
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            facing="back"
            onBarcodeScanned={onBarcodeScanned}
            style={styles.camera}
          />
          <View style={styles.scannerFooter}>
            <PrimaryButton label="Enter serial manually" tone="secondary" onPress={() => setIsScannerOpen(false)} />
          </View>
        </View>
      </Modal>

      <Modal animationType="slide" visible={isBleDevicePickerOpen} onRequestClose={() => setIsBleDevicePickerOpen(false)} transparent>
        <View style={styles.pickerOverlay}>
          <View style={styles.pickerPanel}>
            <Text style={styles.cardTitle}>Choose setup device</Text>
            <Text style={styles.cardSubtitle}>
              Choose the PlantLab device in setup mode. Use the name suffix on the device label or serial monitor if needed.
            </Text>
            {bleDeviceOptions.map((device) => (
              <PrimaryButton
                key={device.id}
                label={bleDeviceLabel(device)}
                tone="secondary"
                onPress={() =>
                  bleDevicePickerMode === "identity" ? createClaimTokenFromBleDevice(device) : loadSelectedBleDeviceWifiNetworks(device)
                }
              />
            ))}
            <PrimaryButton label="Cancel" tone="secondary" onPress={() => setIsBleDevicePickerOpen(false)} />
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

type WifiSsidPickerProps = {
  value: string;
  options: string[];
  manualMode: boolean;
  openSignal: number;
  onChangeSsid: (value: string) => void;
  onChangeManualMode: (value: boolean) => void;
};

function WifiSsidPicker({ value, options, manualMode, openSignal, onChangeSsid, onChangeManualMode }: WifiSsidPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const availableOptions = options;

  useEffect(() => {
    if (openSignal > 0 && availableOptions.length > 0) {
      setIsOpen(true);
    }
  }, [availableOptions.length, openSignal]);

  function selectSsid(ssid: string) {
    onChangeSsid(ssid);
    onChangeManualMode(false);
    setIsOpen(false);
  }

  function selectManual() {
    onChangeManualMode(true);
    setIsOpen(false);
  }

  return (
    <View style={styles.field}>
      <Text style={styles.label}>Home Wi-Fi SSID</Text>
      <PrimaryButton
        label={availableOptions.length > 0 ? `Choose scanned Wi-Fi (${availableOptions.length})` : "No scanned Wi-Fi networks"}
        tone="secondary"
        onPress={() => setIsOpen(true)}
      />
      <TextInput
        autoCapitalize="none"
        autoCorrect={false}
        onChangeText={(nextValue) => {
          onChangeManualMode(true);
          onChangeSsid(nextValue);
        }}
        placeholder="Your 2.4 GHz Wi-Fi name"
        placeholderTextColor={theme.colors.textMuted}
        style={styles.input}
        value={value}
      />
      <Text style={styles.meta}>PlantLab can only join 2.4 GHz Wi-Fi. If your network is not listed, type its name.</Text>

      <Modal animationType="slide" visible={isOpen} onRequestClose={() => setIsOpen(false)} transparent>
        <View style={styles.pickerOverlay}>
          <View style={styles.pickerPanel}>
            <Text style={styles.cardTitle}>Choose Wi-Fi network</Text>
            {availableOptions.length > 0 ? (
              availableOptions.map((ssid) => (
                <PrimaryButton key={ssid} label={ssid} tone={ssid === value && !manualMode ? "primary" : "secondary"} onPress={() => selectSsid(ssid)} />
              ))
            ) : (
              <Text style={styles.cardSubtitle}>No 2.4 GHz networks were reported by this scan. You can still type your Wi-Fi name.</Text>
            )}
            <PrimaryButton label="My Wi-Fi is not listed" tone="secondary" onPress={selectManual} />
            <PrimaryButton label="Cancel" tone="secondary" onPress={() => setIsOpen(false)} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

type LabeledInputProps = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
};

function LabeledInput({ label, value, onChangeText, placeholder, secureTextEntry = false }: LabeledInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        autoCapitalize="none"
        autoCorrect={false}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textMuted}
        secureTextEntry={secureTextEntry}
        style={styles.input}
        value={value}
      />
    </View>
  );
}

type PasswordInputProps = {
  label: string;
  value: string;
  visible: boolean;
  onChangeText: (value: string) => void;
  onToggleVisible: () => void;
  placeholder?: string;
};

function PasswordInput({ label, value, visible, onChangeText, onToggleVisible, placeholder }: PasswordInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.passwordRow}>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={theme.colors.textMuted}
          secureTextEntry={!visible}
          style={[styles.input, styles.passwordInput]}
          textContentType="password"
          value={value}
        />
        <Pressable accessibilityRole="button" onPress={onToggleVisible} style={styles.passwordToggle}>
          <Text style={styles.passwordToggleLabel}>{visible ? "Hide" : "Show"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

function extractSerialNumberFromQr(rawValue: string): string {
  const value = rawValue.trim();
  if (!value) {
    return "";
  }

  try {
    const parsed = JSON.parse(value) as Record<string, unknown>;
    const candidate = parsed.serial_number ?? parsed.serialNumber ?? parsed.sn;
    if (typeof candidate === "string") {
      return candidate.trim();
    }
  } catch {
    // Plain serials and setup URLs are expected too.
  }

  try {
    const url = new URL(value);
    const candidate = url.searchParams.get("sn") ?? url.searchParams.get("serial_number") ?? url.searchParams.get("serialNumber");
    if (candidate) {
      return candidate.trim();
    }
  } catch {
    // Not a URL; fall through to plain serial parsing.
  }

  const serialMatch = value.match(/\bSN-[A-Za-z0-9-]+\b/);
  if (serialMatch) {
    return serialMatch[0];
  }
  return value;
}

function mergeWifiSsidOptions(values: string[]): string[] {
  const seen = new Set<string>();
  const options: string[] = [];
  for (const value of values) {
    const ssid = value.trim();
    if (!ssid || seen.has(ssid)) {
      continue;
    }
    seen.add(ssid);
    options.push(ssid);
  }
  return options;
}

function shortHardwareSuffix(value?: string): string | undefined {
  const normalized = value?.trim();
  if (!normalized) {
    return undefined;
  }
  return normalized.slice(-6);
}

function bleDeviceLabel(device: BleProvisioningDevice): string {
  const details: string[] = [];
  const suffix = device.displaySuffix ?? shortHardwareSuffix(device.identity?.hardwareDeviceId);
  if (suffix) {
    details.push(suffix);
  }
  if (typeof device.rssi === "number") {
    details.push(`${device.rssi} dBm`);
  }
  return details.length > 0 ? `${device.name} (${details.join(", ")})` : device.name;
}

function wifiScanErrorMessage(err: unknown): string {
  if (err instanceof BleProvisioningError) {
    return err.message;
  }
  return "Could not scan nearby 2.4 GHz Wi-Fi over BLE. Type the SSID manually or use the SoftAP compatibility fallback.";
}

function provisioningErrorMessage(err: unknown): string {
  if (err instanceof BleProvisioningError) {
    return err.message;
  }
  return "Could not provision the device over BLE. Retry, or use the SoftAP compatibility fallback.";
}

const styles = StyleSheet.create({
  header: { gap: 8 },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 34, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  error: { color: "#b42318" },
  success: { color: theme.colors.accent, fontSize: 14, fontWeight: "700" },
  cardTitle: { fontSize: 20, fontWeight: "700", color: theme.colors.textPrimary },
  cardSubtitle: { fontSize: 14, color: theme.colors.textSecondary, lineHeight: 20 },
  field: { gap: 6 },
  label: { fontSize: 14, fontWeight: "700", color: theme.colors.textPrimary },
  input: {
    minHeight: 44,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    color: theme.colors.textPrimary,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
  },
  passwordRow: {
    flexDirection: "row",
    gap: 8,
  },
  passwordInput: {
    flex: 1,
  },
  passwordToggle: {
    minHeight: 44,
    minWidth: 72,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: 12,
  },
  passwordToggleLabel: {
    color: theme.colors.textPrimary,
    fontSize: 15,
    fontWeight: "700",
  },
  meta: { fontSize: 13, color: theme.colors.textMuted },
  scannerScreen: {
    flex: 1,
    backgroundColor: "#0f1713",
  },
  scannerHeader: {
    paddingTop: 60,
    paddingHorizontal: 20,
    paddingBottom: 16,
    gap: 8,
  },
  scannerTitle: { color: "#ffffff", fontSize: 24, fontWeight: "800" },
  scannerSubtitle: { color: "#dbe7de", fontSize: 15, lineHeight: 21 },
  camera: {
    flex: 1,
  },
  scannerFooter: {
    padding: 20,
    backgroundColor: "#0f1713",
  },
  pickerOverlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(15, 23, 19, 0.45)",
  },
  pickerPanel: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    padding: 20,
    gap: 12,
  },
});
