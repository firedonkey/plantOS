import { useEffect, useMemo, useState } from "react";
import { Keyboard, Linking, Modal, Share, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { BarcodeScanningResult, CameraView, useCameraPermissions } from "expo-camera";

import { requestDeviceSetupCode } from "@/api/devices";
import type { DeviceSetupHandoff } from "@/api/devices";
import { getApiBaseUrl, getConfiguredWifiSsidOptions } from "@/api/config";
import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

const DEFAULT_DEVICE_NAME = "esp32";
const DEFAULT_DEVICE_LOCATION = "1";
const DEVICE_SETUP_WIFI_NETWORKS_URL = "http://10.42.0.1:8080/wifi/networks";

export function AddDeviceScreen() {
  const { token } = useSession();
  const [deviceName, setDeviceName] = useState("");
  const [location, setLocation] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [wifiSsid, setWifiSsid] = useState("");
  const [isManualWifiSsid, setIsManualWifiSsid] = useState(false);
  const [wifiPassword, setWifiPassword] = useState("");
  const [wifiDetailsConfirmed, setWifiDetailsConfirmed] = useState(false);
  const [isBlePayloadModalOpen, setIsBlePayloadModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usedMock, setUsedMock] = useState(false);
  const [handoff, setHandoff] = useState<DeviceSetupHandoff | null>(null);
  const [isScannerOpen, setIsScannerOpen] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [discoveredWifiSsids, setDiscoveredWifiSsids] = useState<string[]>([]);
  const [wifiScanMessage, setWifiScanMessage] = useState<string | null>(null);
  const [isLoadingWifiNetworks, setIsLoadingWifiNetworks] = useState(false);
  const [wifiPickerOpenSignal, setWifiPickerOpenSignal] = useState(0);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const wifiSsidOptions = useMemo(
    () => mergeWifiSsidOptions([...discoveredWifiSsids, ...getConfiguredWifiSsidOptions()]),
    [discoveredWifiSsids],
  );

  const blePayload = useMemo(() => {
    if (!handoff?.setupToken) {
      return "";
    }
    return JSON.stringify(
      {
        ssid: wifiSsid,
        password: wifiPassword,
        plantlab_token: handoff.setupToken,
        platform_url: getApiBaseUrl(),
      },
      null,
      2,
    );
  }, [handoff, wifiPassword, wifiSsid]);

  const canSubmit = serialNumber.trim().length > 0 && !isSubmitting;
  const canConfirmWifiDetails = wifiSsid.trim().length > 0 && wifiPassword.length > 0;

  function updateWifiSsid(value: string) {
    setWifiSsid(value);
    setWifiDetailsConfirmed(false);
  }

  function updateWifiPassword(value: string) {
    setWifiPassword(value);
    setWifiDetailsConfirmed(false);
  }

  function confirmWifiDetails() {
    if (!canConfirmWifiDetails) {
      return;
    }
    Keyboard.dismiss();
    setWifiDetailsConfirmed(true);
    setIsBlePayloadModalOpen(true);
  }

  async function shareBlePayload() {
    if (!blePayload) {
      return;
    }
    await Share.share({ message: blePayload });
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
    } catch (err) {
      setUsedMock(false);
      setHandoff(null);
      setError(err instanceof Error ? err.message : "Unable to start device setup.");
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
    setWifiScanMessage(null);
    setIsLoadingWifiNetworks(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch(DEVICE_SETUP_WIFI_NETWORKS_URL, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`Device Wi-Fi scan request failed: ${response.status}`);
      }
      const payload = (await response.json()) as {
        networks?: { ssid?: string | null; rssi?: number | null }[];
      };
      const ssids = mergeWifiSsidOptions((payload.networks ?? []).map((network) => network.ssid ?? ""));
      setDiscoveredWifiSsids(ssids);
      setWifiDetailsConfirmed(false);
      if (ssids.length > 0) {
        setIsManualWifiSsid(false);
        setWifiPickerOpenSignal((value) => value + 1);
        setWifiScanMessage(`Loaded ${ssids.length} nearby Wi-Fi network(s) from the device.`);
      } else {
        setWifiScanMessage("The device did not report any nearby Wi-Fi networks. Type the SSID manually.");
      }
    } catch (err) {
      setWifiScanMessage(
        "Could not load Wi-Fi networks from the device. Connect this phone to PlantLab-Setup, wait a few seconds, then try again.",
      );
    } finally {
      clearTimeout(timeoutId);
      setIsLoadingWifiNetworks(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>DEVICE ONBOARDING</Text>
        <Text style={styles.title}>Add device</Text>
        <Text style={styles.subtitle}>Create a setup token, then use BLE provisioning or the existing PlantLab-Setup Wi-Fi flow.</Text>
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Card>
        <Text style={styles.cardTitle}>Device details</Text>
        <LabeledInput label="Device name" value={deviceName} onChangeText={setDeviceName} placeholder={DEFAULT_DEVICE_NAME} />
        <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_NAME}.</Text>
        <LabeledInput label="Location" value={location} onChangeText={setLocation} placeholder={DEFAULT_DEVICE_LOCATION} />
        <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_LOCATION}.</Text>
        <LabeledInput label="Serial number" value={serialNumber} onChangeText={setSerialNumber} placeholder="SN-ESP32-001" />
        <PrimaryButton label="Scan QR code" tone="secondary" onPress={openScanner} />
        {scanError ? <Text style={styles.error}>{scanError}</Text> : null}
        <PrimaryButton label={isSubmitting ? "Verifying..." : "Verify serial and create setup token"} onPress={onSubmit} disabled={!canSubmit} />
      </Card>

      {handoff ? (
        <Card>
          <Text style={styles.cardTitle}>BLE provisioning test</Text>
          <Text style={styles.cardSubtitle}>
            Long-press GPIO14 on the master node, connect to the PlantLab BLE device, and write this JSON to the provisioning
            characteristic.
          </Text>
          <PrimaryButton
            label={isLoadingWifiNetworks ? "Loading nearby Wi-Fi..." : "Load nearby Wi-Fi from device"}
            onPress={loadDeviceWifiNetworks}
            disabled={isLoadingWifiNetworks}
          />
          {wifiScanMessage ? <Text style={styles.meta}>{wifiScanMessage}</Text> : null}
          <WifiSsidPicker
            manualMode={isManualWifiSsid}
            onChangeManualMode={setIsManualWifiSsid}
            onChangeSsid={updateWifiSsid}
            openSignal={wifiPickerOpenSignal}
            options={wifiSsidOptions}
            value={wifiSsid}
          />
          <LabeledInput label="Home Wi-Fi password" value={wifiPassword} onChangeText={updateWifiPassword} placeholder="Required for BLE test" secureTextEntry />
          <PrimaryButton label="Confirm Wi-Fi details" onPress={confirmWifiDetails} disabled={!canConfirmWifiDetails} />
          {!canConfirmWifiDetails ? <Text style={styles.meta}>Select or type your Wi-Fi name, then enter the Wi-Fi password to continue.</Text> : null}
          {wifiDetailsConfirmed ? (
            <View style={styles.confirmedBlock}>
              <Text style={styles.success}>Wi-Fi details confirmed. Next, write the BLE payload to the device.</Text>
              <PrimaryButton label="Show BLE write instructions" onPress={() => setIsBlePayloadModalOpen(true)} />
              {handoff.setupToken ? <Text style={styles.meta}>Setup token: {handoff.setupToken}</Text> : null}
              <Text selectable style={styles.payload}>
                {blePayload || "Setup token missing. Create another setup token before testing BLE."}
              </Text>
              <Text style={styles.meta}>Service UUID: c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901</Text>
              <Text style={styles.meta}>Write UUID: c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902</Text>
              <Text style={styles.meta}>Status UUID: c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903</Text>
            </View>
          ) : null}
        </Card>
      ) : null}

      {handoff ? (
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

      <Modal animationType="slide" visible={isBlePayloadModalOpen} onRequestClose={() => setIsBlePayloadModalOpen(false)}>
        <View style={styles.bleModalScreen}>
          <Text style={styles.scannerTitle}>Write BLE payload</Text>
          <Text style={styles.bleModalCopy}>
            Wi-Fi details are ready. This app prepares the payload, but Expo Go does not write BLE characteristics directly.
            Use a BLE client such as nRF Connect to connect to the PlantLab device and write the payload below.
          </Text>
          <View style={styles.bleSteps}>
            <Text style={styles.bleStep}>1. Keep the master in BLE provisioning mode.</Text>
            <Text style={styles.bleStep}>2. Connect to PlantLab-Setup in your BLE client.</Text>
            <Text style={styles.bleStep}>3. Open service c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901.</Text>
            <Text style={styles.bleStep}>4. Write this JSON to characteristic c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902.</Text>
          </View>
          <Text selectable style={styles.blePayload}>
            {blePayload || "Setup token missing. Create another setup token before testing BLE."}
          </Text>
          <PrimaryButton label="Share payload" onPress={shareBlePayload} disabled={!blePayload} />
          <PrimaryButton label="Done" tone="secondary" onPress={() => setIsBlePayloadModalOpen(false)} />
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
  const showManualInput = manualMode || availableOptions.length === 0;

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
        label={value && !manualMode ? value : availableOptions.length > 0 ? `Select Wi-Fi network (${availableOptions.length})` : "Type Wi-Fi name manually"}
        tone="secondary"
        onPress={() => setIsOpen(true)}
      />
      {showManualInput ? (
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={onChangeSsid}
          placeholder="Your Wi-Fi"
          placeholderTextColor={theme.colors.textMuted}
          style={styles.input}
          value={value}
        />
      ) : null}
      <Text style={styles.meta}>
        Connect this phone to PlantLab-Setup and load nearby Wi-Fi from the device to populate this list.
      </Text>

      <Modal animationType="slide" visible={isOpen} onRequestClose={() => setIsOpen(false)} transparent>
        <View style={styles.pickerOverlay}>
          <View style={styles.pickerPanel}>
            <Text style={styles.cardTitle}>Choose Wi-Fi network</Text>
            {availableOptions.length > 0 ? (
              availableOptions.map((ssid) => (
                <PrimaryButton key={ssid} label={ssid} tone={ssid === value && !manualMode ? "primary" : "secondary"} onPress={() => selectSsid(ssid)} />
              ))
            ) : (
              <Text style={styles.cardSubtitle}>No configured Wi-Fi options yet.</Text>
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
  meta: { fontSize: 13, color: theme.colors.textMuted },
  payload: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#f9fbfa",
    color: theme.colors.textPrimary,
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
    padding: 12,
  },
  confirmedBlock: { gap: 10 },
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
  bleModalScreen: {
    flex: 1,
    backgroundColor: "#0f1713",
    paddingTop: 60,
    paddingHorizontal: 20,
    paddingBottom: 24,
    gap: 16,
  },
  bleModalCopy: {
    color: "#dbe7de",
    fontSize: 15,
    lineHeight: 22,
  },
  bleSteps: {
    gap: 8,
  },
  bleStep: {
    color: "#ffffff",
    fontSize: 14,
    lineHeight: 20,
  },
  blePayload: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.22)",
    backgroundColor: "rgba(255,255,255,0.08)",
    color: "#ffffff",
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
    padding: 12,
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
