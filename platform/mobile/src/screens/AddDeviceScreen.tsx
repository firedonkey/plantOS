import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Animated, Easing, Keyboard, Linking, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { BarcodeScanningResult, CameraView, useCameraPermissions } from "expo-camera";

import { getSetupStatus, requestDeviceClaimToken, requestDeviceSetupCode } from "@/api/devices";
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
import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

const DEFAULT_DEVICE_NAME = "Smart Planter";
const ONLINE_POLL_INTERVAL_MS = 2000;
const ONLINE_POLL_TIMEOUT_MS = 90000;
const ONLINE_CONFIRMATION_TIMEOUT =
  "We could not confirm your Smart Planter is online yet. Please make sure your Wi-Fi password is correct and the device is nearby.";
type AddDeviceStep = "find_device" | "wifi_provisioning" | "waiting_online";

export function AddDeviceScreen() {
  const { token } = useSession();
  const [deviceName, setDeviceName] = useState("");
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
  const [isWaitingForOnline, setIsWaitingForOnline] = useState(false);
  const [bleProvisioningMessage, setBleProvisioningMessage] = useState<string | null>(null);
  const [bleProvisioningTone, setBleProvisioningTone] = useState<"idle" | "success" | "error">("idle");
  const [step, setStep] = useState<AddDeviceStep>("find_device");
  const [showSerialFallback, setShowSerialFallback] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const wifiSsidOptions = useMemo(() => mergeWifiSsidOptions(discoveredWifiSsids), [discoveredWifiSsids]);

  const canSubmit = serialNumber.trim().length > 0 && !isSubmitting;
  const canConfirmWifiDetails = wifiSsid.trim().length > 0 && wifiPassword.length > 0;
  const blePlatformUrl = handoff?.platformUrl?.trim() || getApiBaseUrl().trim();
  const canProvisionOverBle = Boolean(handoff?.setupToken && blePlatformUrl && canConfirmWifiDetails && !isProvisioningOverBle && !isWaitingForOnline);

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
          "No PlantLab setup device was found. Keep the status light blinking and try again.",
        );
      }
      if (devices.length > 1) {
        setBleDeviceOptions(devices);
        setBleDevicePickerMode("identity");
        setIsBleDevicePickerOpen(true);
        setWifiScanMessage("Choose the PlantLab device in setup mode. Use the strongest signal if you only have one planter nearby.");
        return;
      }
      await createClaimTokenFromBleDevice(devices[0]);
    } catch (err) {
      setShowSerialFallback(true);
      setError(err instanceof Error ? err.message : "Could not find a PlantLab setup device.");
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
      setError(err instanceof Error ? err.message : "Unable to read this device identity.");
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
        setWifiScanMessage("Multiple PlantLab setup devices were found. Select the device to read nearby Wi-Fi.");
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
    setWifiScanMessage("Scanning nearby Wi-Fi networks...");
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
      if (!wifiSsid.trim()) {
        setWifiSsid(ssids[0]);
        setIsManualWifiSsid(false);
      }
      setWifiScanMessage(
        `Selected ${ssids[0]} from ${ssids.length} nearby 2.4 GHz Wi-Fi network(s).${
          result.truncated ? " More networks may be available; manual entry is still available." : ""
        }`,
      );
    } else {
      setIsManualWifiSsid(true);
      setWifiScanMessage("No nearby 2.4 GHz networks were found. You can still type your Wi-Fi name.");
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
        setBleProvisioningMessage("Select the PlantLab setup device, then retry setup.");
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
      await waitForProvisionedDeviceOnline(device);
    } catch (err) {
      setBleProvisioningTone("error");
      setBleProvisioningMessage(provisioningErrorMessage(err));
    } finally {
      setIsProvisioningOverBle(false);
    }
  }

  async function waitForProvisionedDeviceOnline(device?: BleProvisioningDevice | null) {
    if (!handoff) {
      return;
    }
    const expectedDeviceId = handoff.expectedDeviceId ?? device?.identity?.hardwareDeviceId;
    const fallbackDeviceName = deviceName.trim() || DEFAULT_DEVICE_NAME;
    setStep("waiting_online");
    setIsWaitingForOnline(true);
    setBleProvisioningTone("idle");
    setBleProvisioningMessage("Connecting your Smart Planter... This may take a moment.");
    try {
      const startedAt = Date.now();
      while (Date.now() - startedAt <= ONLINE_POLL_TIMEOUT_MS) {
        const result = await getSetupStatus(
          {
            expectedDeviceId,
            deviceName: fallbackDeviceName,
            expectImage: false,
          },
          token ?? undefined,
        );
        setUsedMock((current) => current || result.usedMock);
        if (result.status.deviceId && (result.status.online || result.status.ready)) {
          setBleProvisioningTone("success");
          setBleProvisioningMessage("Smart Planter is online.");
          router.replace(`/(app)/devices/${result.status.deviceId}?setup=complete`);
          return;
        }
        await sleep(ONLINE_POLL_INTERVAL_MS);
      }
      setBleProvisioningTone("error");
      setBleProvisioningMessage(ONLINE_CONFIRMATION_TIMEOUT);
    } catch (err) {
      setBleProvisioningTone("error");
      setBleProvisioningMessage(err instanceof Error ? err.message : ONLINE_CONFIRMATION_TIMEOUT);
    } finally {
      setIsWaitingForOnline(false);
    }
  }

  async function findSingleBleProvisioningDevice(): Promise<BleProvisioningDevice | null> {
    const devices = await scanForBleProvisioningDevices();
    if (devices.length === 0) {
      throw new BleProvisioningError("no_devices", "No PlantLab setup device was found. Keep the status light blinking and try again.");
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
        <Text style={styles.title}>
          {step === "find_device" ? "Add PlantLab device" : step === "waiting_online" ? "Connecting device" : "Set up Wi-Fi"}
        </Text>
        <Text style={styles.subtitle}>
          {step === "find_device"
            ? "Put your Smart Planter in setup mode, then connect it to this app."
            : step === "waiting_online"
              ? "Your Smart Planter is joining Wi-Fi and checking in."
            : "Confirm the home Wi-Fi network and enter the password."}
        </Text>
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {step === "find_device" ? (
        <Card>
          <Text style={styles.cardTitle}>Device details</Text>
          <LabeledInput label="Device name" value={deviceName} onChangeText={setDeviceName} placeholder={DEFAULT_DEVICE_NAME} />
          <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_NAME}.</Text>
          <PrimaryButton
            label={isFindingBleDevice || isSubmitting ? "Finding PlantLab device..." : "Find PlantLab device"}
            onPress={startBleIdentityOnboarding}
            disabled={isFindingBleDevice || isSubmitting}
          />
          {isFindingBleDevice || isSubmitting ? (
            <SetupAnimation
              title="Connecting to your Smart Planter"
              detail="Keep the status light blinking while the app connects."
            />
          ) : null}
          <Text style={styles.meta}>Press and hold the setup button until the status light blinks, then tap Find PlantLab device.</Text>
        </Card>
      ) : null}

      {step === "find_device" && showSerialFallback ? (
        <Card>
          <Text style={styles.cardTitle}>QR or serial fallback</Text>
          <Text style={styles.cardSubtitle}>Use this only when the app cannot find or read the device automatically.</Text>
          <LabeledInput label="Serial number" value={serialNumber} onChangeText={setSerialNumber} placeholder="SN-ESP32-001" />
          <PrimaryButton label="Scan QR code" tone="secondary" onPress={openScanner} />
          {scanError ? <Text style={styles.error}>{scanError}</Text> : null}
          <PrimaryButton label={isSubmitting ? "Verifying..." : "Verify serial and create setup token"} onPress={onSubmit} disabled={!canSubmit} />
        </Card>
      ) : null}

      {step === "wifi_provisioning" && handoff ? (
        <Card>
          <Text style={styles.cardTitle}>Set up Wi-Fi</Text>
          <Text style={styles.cardSubtitle}>PlantLab supports 2.4 GHz Wi-Fi. The app will use the strongest network reported by your Smart Planter.</Text>
          {isLoadingWifiNetworks ? <LoadingRow text="Looking for nearby Wi-Fi networks..." /> : null}
          {wifiScanMessage ? <Text style={styles.meta}>{wifiScanMessage}</Text> : null}
          {!isLoadingWifiNetworks && selectedBleDevice && wifiSsidOptions.length === 0 ? (
            <PrimaryButton label="Refresh Wi-Fi networks" tone="secondary" onPress={loadDeviceWifiNetworks} disabled={isLoadingWifiNetworks} />
          ) : null}
          {selectedBleDevice ? <Text style={styles.meta}>Connected device: {bleDeviceLabel(selectedBleDevice)}</Text> : null}
          <WifiSsidPicker
            manualMode={isManualWifiSsid}
            onChangeManualMode={setIsManualWifiSsid}
            onChangeSsid={updateWifiSsid}
            options={wifiSsidOptions}
            value={wifiSsid}
          />
          <PasswordInput
            label="Home Wi-Fi password"
            onChangeText={updateWifiPassword}
            onToggleVisible={() => setShowWifiPassword((value) => !value)}
            placeholder="Wi-Fi password"
            value={wifiPassword}
            visible={showWifiPassword}
          />
          <Text style={styles.meta}>Enter the Wi-Fi password for this network.</Text>
          <PrimaryButton
            label={isProvisioningOverBle ? "Confirming..." : "Confirm"}
            onPress={sendProvisioningOverBle}
            disabled={!canProvisionOverBle}
          />
          {isProvisioningOverBle ? (
            <SetupAnimation
              title="Connecting your Smart Planter"
              detail="Sending Wi-Fi details and waiting for the device to restart."
            />
          ) : null}
          {!canConfirmWifiDetails ? <Text style={styles.meta}>Select or type your Wi-Fi name, then enter the Wi-Fi password to continue.</Text> : null}
          {!blePlatformUrl ? <Text style={styles.error}>A reachable platform URL is required before setup can finish.</Text> : null}
          {bleProvisioningMessage ? (
            <Text style={bleProvisioningTone === "success" ? styles.success : bleProvisioningTone === "error" ? styles.error : styles.meta}>
              {bleProvisioningMessage}
            </Text>
          ) : null}
          {bleProvisioningTone === "error" ? (
            <>
              <PrimaryButton label="Retry setup" tone="secondary" onPress={sendProvisioningOverBle} disabled={!canProvisionOverBle} />
              {!isLoadingWifiNetworks ? (
                <PrimaryButton label="Refresh Wi-Fi networks" tone="secondary" onPress={loadDeviceWifiNetworks} disabled={isLoadingWifiNetworks} />
              ) : null}
            </>
          ) : null}
        </Card>
      ) : null}

      {step === "waiting_online" && handoff ? (
        <Card>
          <Text style={styles.cardTitle}>Connecting your Smart Planter...</Text>
          <Text style={styles.cardSubtitle}>Your planter is joining Wi-Fi and checking in with PlantLab.</Text>
          {isWaitingForOnline ? (
            <SetupAnimation
              title="Checking connection"
              detail="Keep the planter powered on and close to your Wi-Fi router."
            />
          ) : null}
          {bleProvisioningMessage ? (
            <Text style={bleProvisioningTone === "success" ? styles.success : bleProvisioningTone === "error" ? styles.error : styles.meta}>
              {bleProvisioningMessage}
            </Text>
          ) : null}
          {bleProvisioningTone === "error" ? (
            <>
              <PrimaryButton label="Retry online check" tone="secondary" onPress={() => waitForProvisionedDeviceOnline(selectedBleDevice)} disabled={isWaitingForOnline} />
              <PrimaryButton label="Retry setup" tone="secondary" onPress={sendProvisioningOverBle} disabled={!canProvisionOverBle} />
            </>
          ) : null}
        </Card>
      ) : null}

      {(step === "wifi_provisioning" || step === "waiting_online") && handoff && bleProvisioningTone === "error" ? (
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
              Choose the PlantLab device in setup mode. Use the strongest signal if you only have one planter nearby.
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
  onChangeSsid: (value: string) => void;
  onChangeManualMode: (value: boolean) => void;
};

function WifiSsidPicker({ value, options, manualMode, onChangeSsid, onChangeManualMode }: WifiSsidPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const availableOptions = options;

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
      <Text style={styles.label}>Home Wi-Fi network</Text>
      <PrimaryButton
        label={value && !manualMode ? `Selected: ${value}` : availableOptions.length > 0 ? "Choose Wi-Fi network" : "Type Wi-Fi name manually"}
        tone="secondary"
        onPress={availableOptions.length > 0 ? () => setIsOpen(true) : selectManual}
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
      <Text style={styles.meta}>These networks come from your Smart Planter. If yours is missing, type it manually.</Text>

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
        <Pressable
          accessibilityLabel={visible ? "Hide Wi-Fi password" : "Show Wi-Fi password"}
          accessibilityRole="button"
          onPress={onToggleVisible}
          style={styles.passwordToggle}
        >
          <View style={styles.eyeIcon}>
            <View style={styles.eyePupil} />
            {!visible ? <View style={styles.eyeSlash} /> : null}
          </View>
        </Pressable>
      </View>
    </View>
  );
}

function SetupAnimation({ title, detail }: { title: string; detail: string }) {
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [pulse]);

  const ringScale = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.96, 1.08],
  });
  const ringOpacity = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.55, 1],
  });
  const signalOpacity = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 1],
  });

  return (
    <View style={styles.setupAnimation}>
      <View style={styles.setupVisual}>
        <Animated.View style={[styles.setupRing, { opacity: ringOpacity, transform: [{ scale: ringScale }] }]} />
        <View style={styles.setupSprout}>
          <View style={styles.setupStem} />
          <View style={[styles.setupLeaf, styles.setupLeafLeft]} />
          <View style={[styles.setupLeaf, styles.setupLeafRight]} />
        </View>
      </View>
      <View style={styles.setupText}>
        <Text style={styles.setupTitle}>{title}</Text>
        <Text style={styles.meta}>{detail}</Text>
        <View style={styles.signalDots}>
          <Animated.View style={[styles.signalDot, { opacity: signalOpacity }]} />
          <Animated.View style={[styles.signalDot, styles.signalDotMiddle, { opacity: ringOpacity }]} />
          <Animated.View style={[styles.signalDot, { opacity: signalOpacity }]} />
        </View>
      </View>
    </View>
  );
}

function LoadingRow({ text }: { text: string }) {
  return (
    <View style={styles.loadingRow}>
      <ActivityIndicator color={theme.colors.accent} />
      <Text style={styles.meta}>{text}</Text>
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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
  return "Could not scan nearby 2.4 GHz Wi-Fi. Type the Wi-Fi name manually or use the compatibility fallback.";
}

function provisioningErrorMessage(err: unknown): string {
  if (err instanceof BleProvisioningError) {
    return err.message;
  }
  return "Could not finish device setup. Retry, or use the compatibility fallback.";
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
    minWidth: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: 12,
  },
  eyeIcon: {
    width: 25,
    height: 16,
    borderWidth: 2,
    borderColor: theme.colors.textPrimary,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  eyePupil: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.colors.textPrimary,
  },
  eyeSlash: {
    position: "absolute",
    width: 30,
    height: 2,
    borderRadius: 1,
    backgroundColor: theme.colors.textPrimary,
    transform: [{ rotate: "-35deg" }],
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  setupAnimation: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#f7faf6",
    padding: 14,
  },
  setupVisual: {
    width: 58,
    height: 58,
    alignItems: "center",
    justifyContent: "center",
  },
  setupRing: {
    position: "absolute",
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2,
    borderColor: theme.colors.accent,
    backgroundColor: "rgba(47, 125, 75, 0.08)",
  },
  setupSprout: {
    width: 34,
    height: 36,
    alignItems: "center",
    justifyContent: "flex-end",
  },
  setupStem: {
    width: 5,
    height: 24,
    borderRadius: 4,
    backgroundColor: theme.colors.accent,
  },
  setupLeaf: {
    position: "absolute",
    top: 8,
    width: 18,
    height: 12,
    borderTopLeftRadius: 14,
    borderBottomRightRadius: 14,
    backgroundColor: theme.colors.accent,
  },
  setupLeafLeft: {
    left: 2,
    transform: [{ rotate: "28deg" }],
  },
  setupLeafRight: {
    right: 2,
    transform: [{ rotate: "-28deg" }],
  },
  setupText: {
    flex: 1,
    gap: 6,
  },
  setupTitle: {
    color: theme.colors.textPrimary,
    fontSize: 15,
    fontWeight: "800",
  },
  signalDots: {
    flexDirection: "row",
    gap: 5,
    marginTop: 2,
  },
  signalDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: theme.colors.accent,
  },
  signalDotMiddle: {
    width: 20,
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
