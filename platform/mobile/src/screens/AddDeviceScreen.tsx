import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Alert, Animated, Easing, Keyboard, Linking, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { BarcodeScanningResult, CameraView, useCameraPermissions } from "expo-camera";

import { ApiError } from "@/api/client";
import { getClaimTokenStatus, getSetupStatus, requestDeviceClaimToken, requestDeviceSetupCode } from "@/api/devices";
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
import { OnboardingProgress, type OnboardingProgressStep } from "@/components/onboarding/OnboardingProgress";
import { OwnershipTransferInfo } from "@/components/onboarding/OwnershipTransferInfo";
import { RecoveryScreen } from "@/components/onboarding/RecoveryScreen";
import { PrimaryButton } from "@/components/PrimaryButton";
import { Screen } from "@/components/Screen";
import { StatusChip } from "@/components/StatusChip";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";

const DEFAULT_DEVICE_NAME = "Smart Planter";
const ONLINE_POLL_INTERVAL_MS = 2000;
const ONLINE_POLL_TIMEOUT_MS = 90000;
const ONLINE_CONFIRMATION_TIMEOUT =
  "PlantLab is taking longer than expected. Keep it powered on and close to your router, then try again.";
const RECOVERY_WIFI_RESTORED_PREVIOUS_CONFIG =
  "The new Wi-Fi details did not connect, so the device restored its previous connection. Check the Wi-Fi password and try reconnecting.";
const DEVICE_OWNERSHIP_CONFLICT = "This PlantLab is already connected to another account.";
type AddDeviceStep = "find_device" | "wifi_provisioning" | "waiting_online";
type OnboardingStageId = "connect" | "send_wifi" | "connect_wifi" | "setup_device" | "ready";
type OnboardingRecoveryKind = "wifi" | "timeout" | "connection" | "ownership" | "setup_check" | "mismatch" | "generic";

// Phase 1 keeps the existing provisioning flow, but maps coarse internal states
// into a small user-facing progress model so setup does not feel stalled.
const ONBOARDING_PROGRESS_STEPS: OnboardingProgressStep[] = [
  {
    id: "connect",
    label: "Connecting to PlantLab",
    description: "Keep your phone close to the device.",
  },
  {
    id: "send_wifi",
    label: "Sending Wi-Fi settings",
    description: "PlantLab receives the network name and password.",
  },
  {
    id: "connect_wifi",
    label: "Connecting to your Wi-Fi",
    description: "PlantLab tests the connection before saving it.",
  },
  {
    id: "setup_device",
    label: "Setting up your device",
    description: "PlantLab restarts and checks in with your account.",
  },
  {
    id: "ready",
    label: "PlantLab is ready",
    description: "Your device is online.",
  },
];

const ONBOARDING_STAGE_ORDER: OnboardingStageId[] = ["connect", "send_wifi", "connect_wifi", "setup_device", "ready"];

export function AddDeviceScreen() {
  const { token } = useSession();
  const params = useLocalSearchParams<{
    recoveryMode?: string;
    recoveryDeviceId?: string;
    recoveryHardwareId?: string;
    recoveryName?: string;
  }>();
  const recoveryMode = params.recoveryMode === "repair" ? "repair" : params.recoveryMode === "wifi" ? "wifi" : null;
  const recoveryPlatformDeviceId = parsePositiveIntParam(params.recoveryDeviceId);
  const recoveryHardwareId = typeof params.recoveryHardwareId === "string" ? params.recoveryHardwareId.trim() : "";
  const isRecoveryFlow = recoveryMode !== null && recoveryPlatformDeviceId !== null;
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
  const [onboardingStage, setOnboardingStage] = useState<OnboardingStageId>("connect");
  const [onboardingRecoveryKind, setOnboardingRecoveryKind] = useState<OnboardingRecoveryKind>("generic");
  const [isPostResetWaiting, setIsPostResetWaiting] = useState(false);
  const [step, setStep] = useState<AddDeviceStep>("find_device");
  const [showSerialFallback, setShowSerialFallback] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const wifiSsidOptions = useMemo(() => mergeWifiSsidOptions(discoveredWifiSsids), [discoveredWifiSsids]);

  const canSubmit = serialNumber.trim().length > 0 && !isSubmitting;
  const canConfirmWifiDetails = wifiSsid.trim().length > 0 && wifiPassword.length > 0;
  const blePlatformUrl = handoff?.platformUrl?.trim() || getApiBaseUrl().trim();
  const canProvisionOverBle = Boolean(handoff?.setupToken && blePlatformUrl && canConfirmWifiDetails && !isProvisioningOverBle && !isWaitingForOnline);
  const progressCompletedStepIds = completedOnboardingStages(onboardingStage, bleProvisioningTone === "success");
  const progressTitle = bleProvisioningTone === "success" ? "PlantLab is ready" : "Setting up PlantLab";
  const progressDescription =
    bleProvisioningTone === "success"
      ? "Your device is connected and ready to monitor your plant."
      : onboardingProgressDescription(onboardingStage);
  const showFindDeviceRecovery = Boolean(error && step === "find_device" && showSerialFallback);

  useEffect(() => {
    if (!isRecoveryFlow) {
      return;
    }
    const recoveryName = typeof params.recoveryName === "string" ? params.recoveryName.trim() : "";
    if (recoveryName && !deviceName.trim()) {
      setDeviceName(recoveryName);
    }
  }, [deviceName, isRecoveryFlow, params.recoveryName]);

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
      setOnboardingRecoveryKind("generic");
      setOnboardingStage("connect");
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
    setOnboardingRecoveryKind("generic");
    setOnboardingStage("connect");
    setIsPostResetWaiting(false);
    setShowSerialFallback(false);
    setIsFindingBleDevice(true);
    try {
      const devices = await scanForBleProvisioningDevices();
      if (devices.length === 0) {
        throw new BleProvisioningError(
          "no_devices",
          "No nearby PlantLab found. Hold the setup button for 5 seconds until the light blinks, then try again.",
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
      setOnboardingRecoveryKind(recoveryKindForError(err));
      setError(err instanceof BleProvisioningError ? friendlyProvisioningErrorMessage(err) : "Could not find a nearby PlantLab.");
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
      assertRecoveryHardwareMatch(identity.hardwareDeviceId);
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
      setOnboardingRecoveryKind("generic");
      setOnboardingStage("connect");
      setStep("wifi_provisioning");
      void loadSelectedBleDeviceWifiNetworks(deviceWithIdentity);
    } catch (err) {
      setUsedMock(false);
      setHandoff(null);
      setSelectedBleDevice(null);
      setShowSerialFallback(true);
      setOnboardingRecoveryKind(recoveryKindForError(err));
      setError(err instanceof BleProvisioningError ? friendlyProvisioningErrorMessage(err) : "Unable to identify this PlantLab.");
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
        setWifiScanMessage("Multiple PlantLab devices were found. Select the one you want to set up.");
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
    setOnboardingRecoveryKind("generic");
    setOnboardingStage("connect");
    setIsPostResetWaiting(false);
    setIsProvisioningOverBle(true);
    try {
      const discoveredDevice = selectedBleDevice ?? (await findSingleBleProvisioningDevice());
      if (!discoveredDevice) {
        setBleProvisioningTone("error");
        setBleProvisioningMessage("Select the PlantLab device, then try again.");
        return;
      }
      const device = await ensureRecoveryDeviceIdentity(discoveredDevice);
      setSelectedBleDevice(device);
      await provisionDeviceOverBle({
        deviceId: device.id,
        ssid: wifiSsid,
        password: wifiPassword,
        setupToken: handoff.setupToken,
        platformUrl: blePlatformUrl,
        backendUrl: handoff.provisioningApiUrl,
        attachToPlatformDeviceId: recoveryPlatformDeviceId,
        onProgress: handleBleProvisioningProgress,
      });
      await waitForProvisionedDeviceOnline(device);
    } catch (err) {
      const message = provisioningErrorMessage(err);
      setBleProvisioningTone("error");
      setOnboardingRecoveryKind(recoveryKindForError(err));
      setBleProvisioningMessage(message);
      if (isWifiCredentialProvisioningError(err)) {
        Alert.alert("Wi-Fi did not connect", message);
      }
    } finally {
      setIsProvisioningOverBle(false);
    }
  }

  async function waitForProvisionedDeviceOnline(device?: BleProvisioningDevice | null) {
    if (!handoff) {
      return;
    }
    const expectedDeviceId = handoff.expectedDeviceId ?? device?.identity?.hardwareDeviceId;
    const fallbackDeviceName = deviceName.trim() || (isRecoveryFlow ? "Recovered Smart Planter" : DEFAULT_DEVICE_NAME);
    setStep("waiting_online");
    setIsWaitingForOnline(true);
    setBleProvisioningTone("idle");
    setOnboardingRecoveryKind("generic");
    setOnboardingStage("setup_device");
    setBleProvisioningMessage("PlantLab is joining Wi-Fi and checking in. This can take a moment.");
    try {
      const startedAt = Date.now();
      while (Date.now() - startedAt <= ONLINE_POLL_TIMEOUT_MS) {
        const { result: claimStatusResult, unavailable: claimStatusUnavailable } =
          handoff.setupToken
            ? await getRecoveryClaimTokenStatus(handoff.setupToken)
            : { result: null, unavailable: false };
        if (claimStatusResult) {
          setUsedMock((current) => current || claimStatusResult.usedMock);
          const claimFailureMessage = claimTokenFailureMessage(
            claimStatusResult.status.failureCode,
            claimStatusResult.status.failureMessage,
          );
          if (claimFailureMessage) {
            setBleProvisioningTone("error");
            setOnboardingRecoveryKind("ownership");
            setBleProvisioningMessage(claimFailureMessage);
            Alert.alert("PlantLab already connected", claimFailureMessage);
            return;
          }
          if (claimStatusResult.status.expired && !claimStatusResult.status.used) {
            setBleProvisioningTone("error");
            setOnboardingRecoveryKind("timeout");
            setBleProvisioningMessage("Setup took too long. Restart setup so PlantLab can create a fresh secure connection.");
            return;
          }
        }

        const result = await getSetupStatus(
          {
            expectedDeviceId,
            deviceName: fallbackDeviceName,
            expectImage: false,
          },
          token ?? undefined,
        );
        setUsedMock((current) => current || result.usedMock);
        const claimWasUsed = claimStatusResult?.status.used ?? (claimStatusUnavailable || !handoff.setupToken);
        const expectedUsedDeviceId =
          isRecoveryFlow && recoveryPlatformDeviceId !== null ? String(recoveryPlatformDeviceId) : result.status.deviceId;
        const claimUsedByExpectedDevice =
          claimStatusUnavailable ||
          !claimStatusResult ||
          !claimStatusResult.status.usedByDeviceId ||
          !expectedUsedDeviceId ||
          claimStatusResult.status.usedByDeviceId === expectedUsedDeviceId;
        if (
          isRecoveryFlow &&
          !claimWasUsed &&
          result.status.deviceId === String(recoveryPlatformDeviceId) &&
          result.status.online &&
          heartbeatIsAfterStart(result.status.lastHeartbeatAt, startedAt)
        ) {
          setBleProvisioningTone("error");
          setOnboardingRecoveryKind("wifi");
          setBleProvisioningMessage(RECOVERY_WIFI_RESTORED_PREVIOUS_CONFIG);
          Alert.alert("Wi-Fi did not connect", RECOVERY_WIFI_RESTORED_PREVIOUS_CONFIG);
          return;
        }
        if (result.status.deviceId && (result.status.online || result.status.ready)) {
          if (!claimWasUsed) {
            await sleep(ONLINE_POLL_INTERVAL_MS);
            continue;
          }
          if (!claimUsedByExpectedDevice) {
            setBleProvisioningTone("error");
            setOnboardingRecoveryKind("mismatch");
            setBleProvisioningMessage("Setup finished for a different PlantLab. Start recovery again and choose the matching device.");
            return;
          }
          setBleProvisioningTone("success");
          setOnboardingStage("ready");
          setBleProvisioningMessage("PlantLab is ready. You can now monitor your plant from anywhere.");
          if (isRecoveryFlow && recoveryPlatformDeviceId !== null) {
            router.replace(`/(app)/devices/${recoveryPlatformDeviceId}?setup=complete`);
          } else {
            router.replace(`/(app)/devices/${result.status.deviceId}?setup=complete`);
          }
          return;
        }
        await sleep(ONLINE_POLL_INTERVAL_MS);
      }
      setBleProvisioningTone("error");
      setOnboardingRecoveryKind("timeout");
      setBleProvisioningMessage(ONLINE_CONFIRMATION_TIMEOUT);
    } catch (err) {
      setBleProvisioningTone("error");
      setOnboardingRecoveryKind(err instanceof ApiError ? "setup_check" : "timeout");
      setBleProvisioningMessage(err instanceof ApiError ? "Could not check setup status. Keep PlantLab powered on and try again." : ONLINE_CONFIRMATION_TIMEOUT);
    } finally {
      setIsWaitingForOnline(false);
    }
  }

  async function getRecoveryClaimTokenStatus(setupToken: string): Promise<{
    result: Awaited<ReturnType<typeof getClaimTokenStatus>> | null;
    unavailable: boolean;
  }> {
    try {
      return {
        result: await getClaimTokenStatus({ setupToken }, token ?? undefined),
        unavailable: false,
      };
    } catch (err) {
      if (isNotFoundApiError(err)) {
        return { result: null, unavailable: true };
      }
      throw err;
    }
  }

  async function findSingleBleProvisioningDevice(): Promise<BleProvisioningDevice | null> {
    const devices = await scanForBleProvisioningDevices();
    if (devices.length === 0) {
      throw new BleProvisioningError("no_devices", "No nearby PlantLab found. Hold the setup button for 5 seconds until the light blinks, then try again.");
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
    setOnboardingStage(stageForProvisioningProgress(progress));
    setBleProvisioningMessage(userFacingProgressMessage(progress));
    if (progress.phase === "success") {
      setBleProvisioningTone("success");
    } else if (progress.phase === "error") {
      setBleProvisioningTone("error");
    } else {
      setBleProvisioningTone("idle");
    }
  }

  function assertRecoveryHardwareMatch(hardwareDeviceId?: string) {
    if (!isRecoveryFlow || !recoveryHardwareId || !hardwareDeviceId) {
      return;
    }
    if (hardwareDeviceId.trim() !== recoveryHardwareId) {
      throw new BleProvisioningError(
        "identity_mismatch",
        "This is not the PlantLab selected for recovery. Choose the matching device before sending Wi-Fi details.",
      );
    }
  }

  function showResetDeviceHelp() {
    Alert.alert(
      "Reset PlantLab",
      "Hold the setup button for 20 seconds. Release when the light blinks quickly, then wait for PlantLab to restart before setup again.",
      [
        { text: "Close", style: "cancel" },
        { text: "I reset PlantLab", onPress: () => setIsPostResetWaiting(true) },
      ],
    );
  }

  function returnToWifiDetails() {
    setBleProvisioningTone("idle");
    setBleProvisioningMessage(null);
    setOnboardingRecoveryKind("generic");
    setOnboardingStage("connect");
    setIsPostResetWaiting(false);
    setStep("wifi_provisioning");
  }

  function restartSetup() {
    setError(null);
    setWifiScanMessage(null);
    setBleProvisioningMessage(null);
    setBleProvisioningTone("idle");
    setOnboardingRecoveryKind("generic");
    setOnboardingStage("connect");
    setIsPostResetWaiting(false);
    setHandoff(null);
    setSelectedBleDevice(null);
    setShowSerialFallback(false);
    setStep("find_device");
  }

  function retryCurrentRecovery() {
    if (step === "waiting_online") {
      void waitForProvisionedDeviceOnline(selectedBleDevice);
      return;
    }
    if (step === "wifi_provisioning") {
      void sendProvisioningOverBle();
      return;
    }
    void startBleIdentityOnboarding();
  }

  function lookForDeviceAfterReset() {
    restartSetup();
    void startBleIdentityOnboarding();
  }

  function renderRecovery(kind: OnboardingRecoveryKind, message?: string | null) {
    const copy = recoveryContentForKind(kind, message);
    const primary =
      kind === "timeout" || kind === "setup_check"
        ? { label: "Keep waiting", onPress: () => { void waitForProvisionedDeviceOnline(selectedBleDevice); }, disabled: isWaitingForOnline }
        : { label: kind === "connection" ? "Reconnect" : "Try again", onPress: retryCurrentRecovery, disabled: isProvisioningOverBle || isWaitingForOnline };
    const secondary =
      step === "find_device"
        ? { label: "Restart setup", onPress: restartSetup }
        : { label: "Change Wi-Fi details", onPress: returnToWifiDetails };
    const tertiary =
      kind === "ownership" || kind === "timeout" || kind === "setup_check" || kind === "wifi"
        ? { label: "Reset device instructions", onPress: showResetDeviceHelp }
        : undefined;

    return (
      <>
        <RecoveryScreen
          title={copy.title}
          explanation={copy.explanation}
          likelyCauses={copy.likelyCauses}
          recommendedActions={copy.recommendedActions}
          primaryAction={primary}
          secondaryAction={secondary}
          tertiaryAction={tertiary}
        />
        {kind === "ownership" ? <OwnershipTransferInfo variant="conflict" /> : null}
      </>
    );
  }

  async function ensureRecoveryDeviceIdentity(device: BleProvisioningDevice): Promise<BleProvisioningDevice> {
    if (!isRecoveryFlow) {
      return device;
    }
    if (device.identity) {
      assertRecoveryHardwareMatch(device.identity.hardwareDeviceId);
      return device;
    }
    const identity = await readBleDeviceIdentity(device.id);
    assertRecoveryHardwareMatch(identity.hardwareDeviceId);
    return {
      ...device,
      name: identity.bleName || device.name,
      displaySuffix: shortHardwareSuffix(identity.hardwareDeviceId) ?? device.displaySuffix,
      identity,
    };
  }

  return (
    <Screen scrollToTopSignal={step}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>{isRecoveryFlow ? "DEVICE RECOVERY" : "DEVICE ONBOARDING"}</Text>
        <Text style={styles.title}>
          {step === "find_device"
            ? isRecoveryFlow
              ? recoveryMode === "repair"
                ? "Repair device setup"
                : "Reconnect Wi-Fi"
              : "Add PlantLab device"
            : step === "waiting_online"
              ? "Connecting device"
              : "Set up Wi-Fi"}
        </Text>
        <Text style={styles.subtitle}>
          {step === "find_device"
            ? isRecoveryFlow
              ? "Hold the setup button for 5 seconds until the status light blinks, then connect to the same device."
              : "Put your PlantLab in setup mode, then connect it to this app."
            : step === "waiting_online"
              ? "Your PlantLab is joining Wi-Fi and checking in."
              : isRecoveryFlow
                ? "Your account and history stay with this device while Wi-Fi is updated."
                : "Confirm the home Wi-Fi network and enter the password."}
        </Text>
      </View>

      {usedMock ? <StatusChip label="Mock data mode" tone="mock" /> : null}
      {error && !showFindDeviceRecovery ? <Text style={styles.error}>{error}</Text> : null}

      {isPostResetWaiting ? (
        <Card>
          <OwnershipTransferInfo variant="postReset" />
          <PrimaryButton
            label={isFindingBleDevice || isSubmitting ? "Looking for PlantLab..." : "Look for PlantLab again"}
            onPress={lookForDeviceAfterReset}
            disabled={isFindingBleDevice || isSubmitting}
          />
        </Card>
      ) : null}

      {step === "find_device" ? (
        <Card>
          <Text style={styles.cardTitle}>Device details</Text>
          {isRecoveryFlow ? (
            <Text style={styles.meta}>The app will verify this is the selected PlantLab before sending new Wi-Fi details.</Text>
          ) : (
            <>
              <LabeledInput label="Device name" value={deviceName} onChangeText={setDeviceName} placeholder={DEFAULT_DEVICE_NAME} />
              <Text style={styles.meta}>Leave blank to use {DEFAULT_DEVICE_NAME}.</Text>
            </>
          )}
          <PrimaryButton
            label={isFindingBleDevice || isSubmitting ? "Finding PlantLab device..." : "Find PlantLab device"}
            onPress={startBleIdentityOnboarding}
            disabled={isFindingBleDevice || isSubmitting}
          />
          {isFindingBleDevice || isSubmitting ? (
            <OnboardingProgress
              title="Finding PlantLab"
              description="Looking for a nearby PlantLab in setup mode. Keep the status light blinking and your phone close to the device."
              steps={ONBOARDING_PROGRESS_STEPS}
              currentStepId="connect"
              loading
            />
          ) : null}
          <Text style={styles.meta}>Press and hold the setup button for 5 seconds until the status light blinks, then tap Find PlantLab device.</Text>
        </Card>
      ) : null}

      {step === "find_device" && showSerialFallback ? (
        <Card>
          <Text style={styles.cardTitle}>QR or serial backup</Text>
          <Text style={styles.cardSubtitle}>Use this only when the app cannot find or read the device automatically.</Text>
          {showFindDeviceRecovery ? renderRecovery(onboardingRecoveryKind, error) : null}
          <LabeledInput label="Serial number" value={serialNumber} onChangeText={setSerialNumber} placeholder="SN-ESP32-001" />
          <PrimaryButton label="Scan QR code" tone="secondary" onPress={openScanner} />
          {scanError ? <Text style={styles.error}>{scanError}</Text> : null}
          <PrimaryButton label={isSubmitting ? "Verifying..." : "Verify serial"} onPress={onSubmit} disabled={!canSubmit} />
        </Card>
      ) : null}

      {step === "wifi_provisioning" && handoff ? (
        <Card>
          <Text style={styles.cardTitle}>Set up Wi-Fi</Text>
          <Text style={styles.cardSubtitle}>PlantLab supports 2.4 GHz Wi-Fi. The app will use the strongest network reported by your device.</Text>
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
            label={isProvisioningOverBle ? "Setting up..." : "Confirm Wi-Fi"}
            onPress={sendProvisioningOverBle}
            disabled={!canProvisionOverBle}
          />
          {isProvisioningOverBle ? (
            <OnboardingProgress
              title={progressTitle}
              description={progressDescription}
              steps={ONBOARDING_PROGRESS_STEPS}
              currentStepId={onboardingStage}
              completedStepIds={progressCompletedStepIds}
              loading={bleProvisioningTone !== "success" && bleProvisioningTone !== "error"}
              errorMessage={bleProvisioningTone === "error" ? bleProvisioningMessage : null}
              successMessage={bleProvisioningTone === "success" ? bleProvisioningMessage : null}
            />
          ) : null}
          {!canConfirmWifiDetails ? <Text style={styles.meta}>Select or type your Wi-Fi name, then enter the Wi-Fi password to continue.</Text> : null}
          {!blePlatformUrl ? <Text style={styles.error}>A reachable platform URL is required before setup can finish.</Text> : null}
          {!isProvisioningOverBle && bleProvisioningTone !== "error" && bleProvisioningMessage ? (
            <Text style={bleProvisioningTone === "success" ? styles.success : styles.meta}>
              {bleProvisioningMessage}
            </Text>
          ) : null}
          {!isProvisioningOverBle && bleProvisioningTone === "error" ? renderRecovery(onboardingRecoveryKind, bleProvisioningMessage) : null}
        </Card>
      ) : null}

      {step === "waiting_online" && handoff ? (
        <Card>
          <OnboardingProgress
            title={progressTitle}
            description={progressDescription}
            steps={ONBOARDING_PROGRESS_STEPS}
            currentStepId={onboardingStage}
            completedStepIds={progressCompletedStepIds}
            loading={isWaitingForOnline && bleProvisioningTone !== "error"}
            errorMessage={null}
            successMessage={bleProvisioningTone === "success" ? bleProvisioningMessage : null}
          />
          {bleProvisioningTone === "error" ? renderRecovery(onboardingRecoveryKind, bleProvisioningMessage) : null}
        </Card>
      ) : null}

      {step === "waiting_online" && handoff && bleProvisioningTone === "error" ? (
        <Card>
          <Text style={styles.cardTitle}>Compatibility setup</Text>
          <Text style={styles.cardSubtitle}>
            If app setup still does not finish, use the built-in setup page on the device. Keep PlantLab powered on while it opens.
          </Text>
          <PrimaryButton label="Open compatibility setup" onPress={openSoftApSetup} />
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
            <Text style={styles.cardTitle}>Choose PlantLab</Text>
            <Text style={styles.cardSubtitle}>
              Choose the PlantLab in setup mode. Use the strongest signal if you only have one planter nearby.
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
      <Text style={styles.meta}>These networks come from PlantLab. If yours is missing, type it manually.</Text>

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

function parsePositiveIntParam(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value;
  if (typeof raw !== "string") {
    return null;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function heartbeatIsAfterStart(lastHeartbeatAt: string | undefined, startedAt: number): boolean {
  if (!lastHeartbeatAt) {
    return false;
  }
  const heartbeatMs = Date.parse(lastHeartbeatAt);
  return Number.isFinite(heartbeatMs) && heartbeatMs >= startedAt;
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

function stageForProvisioningProgress(progress: BleProvisioningProgress): OnboardingStageId {
  if (progress.phase === "success") {
    return "setup_device";
  }
  if (progress.status?.state === "WIFI_CONNECTING") {
    return "connect_wifi";
  }
  if (progress.status?.state === "PROVISIONING_COMMITTING") {
    return "setup_device";
  }
  if (progress.phase === "sending") {
    return "send_wifi";
  }
  if (progress.phase === "committing") {
    return "setup_device";
  }
  return "connect";
}

function userFacingProgressMessage(progress: BleProvisioningProgress): string {
  if (progress.phase === "success") {
    return "Wi-Fi details are saved. PlantLab is restarting.";
  }
  if (progress.status?.state === "WIFI_CONNECTING") {
    return "PlantLab is testing your Wi-Fi connection.";
  }
  if (progress.status?.state === "PROVISIONING_COMMITTING") {
    return "PlantLab is saving setup details.";
  }
  if (progress.phase === "sending") {
    return "Sending Wi-Fi information to PlantLab.";
  }
  if (progress.phase === "committing") {
    return "Finishing setup on PlantLab.";
  }
  if (progress.phase === "error") {
    return progress.message.replace(/\bBLE\b/g, "PlantLab").replace(/\bSoftAP\b/g, "compatibility setup");
  }
  return "Connecting to PlantLab.";
}

function completedOnboardingStages(currentStage: OnboardingStageId, success: boolean): OnboardingStageId[] {
  if (success) {
    return ONBOARDING_STAGE_ORDER;
  }
  const currentIndex = ONBOARDING_STAGE_ORDER.indexOf(currentStage);
  if (currentIndex <= 0) {
    return [];
  }
  return ONBOARDING_STAGE_ORDER.slice(0, currentIndex);
}

function onboardingProgressDescription(stage: OnboardingStageId): string {
  switch (stage) {
    case "connect":
      return "PlantLab is connecting to your phone so setup can begin.";
    case "send_wifi":
      return "Sending Wi-Fi information to PlantLab.";
    case "connect_wifi":
      return "PlantLab is connecting to your Wi-Fi. Keep it powered on and nearby.";
    case "setup_device":
      return "PlantLab is finishing setup and checking in with your account.";
    case "ready":
      return "PlantLab is online and ready.";
  }
}

function recoveryKindForError(err: unknown): OnboardingRecoveryKind {
  if (!(err instanceof BleProvisioningError)) {
    return "generic";
  }
  if (["wifi_connect_failed", "wifi_connect_timeout", "wifi_network_not_found"].includes(err.code)) {
    return "wifi";
  }
  if (["no_devices", "connect_failed", "read_failed", "write_failed", "scan_failed", "scan_notify_failed", "scan_request_failed"].includes(err.code)) {
    return "connection";
  }
  if (err.code === "provisioning_timeout") {
    return "timeout";
  }
  if (err.code === "identity_mismatch") {
    return "mismatch";
  }
  return "generic";
}

function recoveryContentForKind(kind: OnboardingRecoveryKind, message?: string | null): {
  title: string;
  explanation: string;
  likelyCauses: string[];
  recommendedActions: string[];
} {
  switch (kind) {
    case "wifi":
      return {
        title: "PlantLab could not connect to your Wi-Fi",
        explanation: message || "The device could not join the selected network.",
        likelyCauses: ["The Wi-Fi password may be incorrect.", "The network may be out of range.", "The router may be temporarily unavailable."],
        recommendedActions: ["Check the password.", "Move PlantLab closer to the router.", "Try the same network again or choose another one."],
      };
    case "timeout":
      return {
        title: "PlantLab is taking longer than expected",
        explanation: message || "Setup may still be finishing in the background.",
        likelyCauses: ["PlantLab may be restarting.", "Wi-Fi may be weak.", "Your network may be slow to let a new device check in."],
        recommendedActions: ["Keep PlantLab powered on.", "Wait a little longer, then try again.", "Change Wi-Fi details if this keeps happening."],
      };
    case "connection":
      return {
        title: "Connection to PlantLab was interrupted",
        explanation: message || "The app lost contact with the device during setup.",
        likelyCauses: ["Your phone may be too far from PlantLab.", "Bluetooth may have disconnected.", "PlantLab may no longer be in setup mode."],
        recommendedActions: ["Keep your phone close to PlantLab.", "Make sure the status light is blinking.", "Reconnect and continue setup."],
      };
    case "ownership":
      return {
        title: "This PlantLab is already connected to another account",
        explanation: "If you recently reset it, wait a moment and try again. If it belongs to someone else, ask them to remove it first.",
        likelyCauses: ["The device may still be connected to another account.", "The full reset may not have completed yet."],
        recommendedActions: [
          "Try again after PlantLab restarts.",
          "Ask the previous owner to remove it from their account.",
          "Use full reset instructions only if this is your device.",
        ],
      };
    case "setup_check":
      return {
        title: "PlantLab could not confirm setup",
        explanation: message || "The app could not confirm that the device checked in.",
        likelyCauses: ["Your phone or backend connection may be temporarily unavailable.", "PlantLab may still be restarting.", "Wi-Fi may be weak."],
        recommendedActions: ["Keep PlantLab powered on.", "Keep waiting for another check.", "Change Wi-Fi details if the device never appears online."],
      };
    case "mismatch":
      return {
        title: "This is not the selected PlantLab",
        explanation: message || "The app found a different PlantLab than the one selected for recovery.",
        likelyCauses: ["More than one PlantLab may be nearby.", "The wrong device may be in setup mode."],
        recommendedActions: ["Restart setup.", "Choose the matching device.", "Use the strongest signal if only one device is nearby."],
      };
    case "generic":
    default:
      return {
        title: "Setup needs attention",
        explanation: message || "PlantLab could not finish setup.",
        likelyCauses: ["The connection may have been interrupted.", "PlantLab may still be restarting.", "Your network may need another try."],
        recommendedActions: ["Try again.", "Change Wi-Fi details if setup keeps failing.", "Use reset instructions if the device is stuck."],
      };
  }
}

function wifiScanErrorMessage(err: unknown): string {
  if (err instanceof BleProvisioningError) {
    return friendlyProvisioningErrorMessage(err);
  }
  return "PlantLab could not scan nearby Wi-Fi. Type your Wi-Fi name manually or try again.";
}

function claimTokenFailureMessage(failureCode?: string, failureMessage?: string): string | null {
  if (!failureCode) {
    return null;
  }
  if (failureCode === "device_owned_by_another_user") {
    return DEVICE_OWNERSHIP_CONFLICT;
  }
  return failureMessage || "Device setup failed. Restart setup and try again.";
}

function provisioningErrorMessage(err: unknown): string {
  if (err instanceof BleProvisioningError) {
    return friendlyProvisioningErrorMessage(err);
  }
  return "PlantLab could not finish setup. Try again or use compatibility setup.";
}

function friendlyProvisioningErrorMessage(error: BleProvisioningError): string {
  switch (error.code) {
    case "no_devices":
      return "No nearby PlantLab found. Hold the setup button for 5 seconds until the light blinks, then try again.";
    case "bluetooth_off":
      return "Turn on Bluetooth to find PlantLab, then try again.";
    case "permission_denied":
      return "Bluetooth permission is needed to set up PlantLab from the app.";
    case "connect_failed":
    case "read_failed":
    case "write_failed":
    case "scan_failed":
    case "scan_notify_failed":
    case "scan_request_failed":
      return "Connection to PlantLab was interrupted. Keep your phone nearby and try again.";
    case "wifi_connect_failed":
      return "PlantLab could not connect to your Wi-Fi. Check your password and try again.";
    case "wifi_connect_timeout":
      return "PlantLab could not join Wi-Fi before the timeout. Move it closer to the router and try again.";
    case "wifi_network_not_found":
      return "PlantLab could not find that Wi-Fi network. Choose a nearby 2.4 GHz network or type the name again.";
    case "provisioning_timeout":
      return "PlantLab is taking longer than expected. Keep it powered on and try again.";
    case "identity_mismatch":
      return "This is not the PlantLab selected for recovery. Choose the matching device.";
    case "busy":
      return "PlantLab is busy. Wait a moment and try again.";
    default:
      return error.message.replace(/\bBLE\b/g, "PlantLab").replace(/\bSoftAP\b/g, "compatibility setup").replace(/\bsetup token\b/g, "secure setup");
  }
}

function isWifiCredentialProvisioningError(err: unknown): boolean {
  return (
    err instanceof BleProvisioningError &&
    ["wifi_connect_failed", "wifi_connect_timeout", "wifi_network_not_found"].includes(err.code)
  );
}

function isNotFoundApiError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 404;
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
