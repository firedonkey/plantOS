from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADD_DEVICE_SCREEN = REPO_ROOT / "platform/mobile/src/screens/AddDeviceScreen.tsx"
BLE_PROVISIONING = REPO_ROOT / "platform/mobile/src/ble/bleProvisioning.ts"
BLE_PROVISIONING_PAYLOAD = REPO_ROOT / "platform/mobile/src/ble/bleProvisioningPayload.ts"
MOBILE_DEVICES_API = REPO_ROOT / "platform/mobile/src/api/devices.ts"
MOBILE_APP_CONFIG = REPO_ROOT / "platform/mobile/app.json"
ESP32_MAIN = REPO_ROOT / "device/esp32/src/main.cpp"
ESP32_BLE_PROVISIONING = REPO_ROOT / "device/esp32/src/provisioning/ble_provisioning.cpp"
ESP32_BLE_PROVISIONING_HEADER = REPO_ROOT / "device/esp32/src/provisioning/ble_provisioning.h"


def read_mobile_source(path: Path) -> str:
    assert path.exists(), f"missing mobile source: {path}"
    return path.read_text(encoding="utf-8")


def read_source(path: Path) -> str:
    assert path.exists(), f"missing source: {path}"
    return path.read_text(encoding="utf-8")


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    while True:
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    next_index = index + 1
                    while next_index < len(source) and source[next_index].isspace():
                        next_index += 1
                    if next_index < len(source) and source[next_index] == "{":
                        brace = next_index
                        break
                    return source[start : index + 1]
        else:
            break
    raise AssertionError(f"could not extract function for signature: {signature}")


def test_mobile_wifi_dropdown_uses_ble_not_softap_networks_endpoint():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)
    ble_helper = read_mobile_source(BLE_PROVISIONING)

    assert "loadBleWifiNetworks" in screen
    assert "readBleWifiNetworksFromDevice" in screen
    assert "Scan nearby 2.4 GHz Wi-Fi" in screen
    assert "http://10.42.0.1:8080/wifi/networks" not in screen
    assert '"/wifi/networks"' not in screen
    assert "http://10.42.0.1:8080/wifi/networks" not in ble_helper
    assert '"/wifi/networks"' not in ble_helper


def test_mobile_ble_helper_reads_wifi_networks_characteristic():
    source = read_mobile_source(BLE_PROVISIONING)

    assert (
        'BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a904"'
        in source
    )
    assert (
        'BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a905"'
        in source
    )
    assert "monitorCharacteristicForService" in source
    assert "writeCharacteristicWithResponseForService" in source
    assert "readCharacteristicForService" in source
    assert "BLE_PROVISIONING_SERVICE_UUID" in source
    assert "BLE_PROVISIONING_WIFI_NETWORKS_CHARACTERISTIC_UUID" in source
    assert "BLE_PROVISIONING_WIFI_SCAN_CONTROL_CHARACTERISTIC_UUID" in source
    assert "JSON.parse(payload)" in source
    assert "network.ssid.trim()" in source
    assert "network.rssi > existing.rssi" in source
    assert "wifi_scan_start" in source
    assert "wifi_scan_page" in source
    assert "Type the SSID manually" in source


def test_mobile_ble_helper_reads_device_identity_characteristic():
    source = read_mobile_source(BLE_PROVISIONING)
    read_identity = extract_function(source, "export async function readBleDeviceIdentity")
    parse_identity = extract_function(source, "function parseBleDeviceIdentityPayload")

    assert (
        'BLE_PROVISIONING_DEVICE_IDENTITY_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a906"'
        in source
    )
    assert "readCharacteristicForService" in read_identity
    assert "BLE_PROVISIONING_DEVICE_IDENTITY_CHARACTERISTIC_UUID" in read_identity
    assert "parseBleDeviceIdentityPayload(decodeBase64Utf8(characteristic.value))" in read_identity
    assert "identity_empty" in read_identity
    assert "identity_unavailable" in read_identity
    assert "Restart BLE setup on the device" in parse_identity
    assert "Update the device firmware" in parse_identity
    assert "device_id" in parse_identity
    assert "hardware_device_id" in parse_identity
    assert "software_version" in parse_identity
    assert "ble_name" in parse_identity
    assert "hardwareDeviceId = stringField(body.hardware_device_id) || deviceId" in parse_identity
    assert "invalid_identity" in parse_identity


def test_mobile_ble_provisioning_uses_write_and_status_characteristics():
    source = read_mobile_source(BLE_PROVISIONING)
    payload = read_mobile_source(BLE_PROVISIONING_PAYLOAD)

    assert (
        'BLE_PROVISIONING_WRITE_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902"'
        in source
    )
    assert (
        'BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903"'
        in source
    )
    assert "provisionDeviceOverBle" in source
    assert "buildBleProvisioningPayload(input)" in source
    assert "monitorCharacteristicForService" in source
    assert "BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID" in source
    assert "writeCharacteristicWithResponseForService" in source
    assert "BLE_PROVISIONING_WRITE_CHARACTERISTIC_UUID" in source
    assert "parseBleProvisioningStatus" in source
    assert "PROVISIONING_SUCCESS" in payload
    assert "PROVISIONING_FAILED" in payload
    assert "provisioning_timeout" in source


def test_mobile_ble_provisioning_status_lifecycle_cleans_up_safely():
    source = read_mobile_source(BLE_PROVISIONING)
    provision = extract_function(source, "export async function provisionDeviceOverBle")
    waiter = extract_function(source, "function createProvisioningStatusWaiter")

    waiter_index = provision.index("createProvisioningStatusWaiter")
    initial_read_index = provision.index("readInitialProvisioningStatus")
    write_index = provision.index("writeCharacteristicWithResponseForService")
    mark_written_index = provision.index("waitForStatus.markWritten()")
    await_status_index = provision.index("return await waitForStatus.promise")
    assert waiter_index < initial_read_index < write_index < mark_written_index < await_status_index
    assert "encodeUtf8ToBase64(payload)" in provision
    assert "waitForStatus?.cleanup()" in provision
    assert "connectedDevice.cancelConnection()" in provision

    assert "device.monitorCharacteristicForService" in waiter
    assert "BLE_PROVISIONING_STATUS_CHARACTERISTIC_UUID" in waiter
    assert "writeCompleted = true" in waiter
    assert "if (!value || settled || !writeCompleted)" in waiter
    assert "readCharacteristicForService" in waiter
    assert "setInterval(pollStatus, BLE_PROVISIONING_STATUS_POLL_MS)" in waiter
    assert "new BleProvisioningError(\"provisioning_timeout\"" in waiter
    assert "subscription.remove()" in waiter
    assert "isBleProvisioningSuccess(status)" in waiter
    assert "isBleProvisioningFailure(status)" in waiter


def test_mobile_ble_provisioning_payload_is_compact_and_token_safe():
    payload = read_mobile_source(BLE_PROVISIONING_PAYLOAD)

    assert "plantlab_token" in payload
    assert "platform_url" in payload
    assert "backend_url" in payload
    assert '"device_token"' not in payload
    assert '"device_access_token"' not in payload
    assert "JSON.stringify(payload)" in payload
    assert "payloadBytes: 768" in payload
    assert "encodeUtf8ToBase64" in payload
    assert "decodeBase64Utf8" in payload
    assert "maskSecret" in payload


def test_mobile_ble_scan_subscribes_before_request_and_times_out_safely():
    source = read_mobile_source(BLE_PROVISIONING)
    scan_payload = extract_function(source, "function requestBleWifiScanPayload")

    subscribe_index = scan_payload.index("device.monitorCharacteristicForService")
    write_index = scan_payload.index("writeCharacteristicWithResponseForService")
    assert subscribe_index < write_index
    assert "commandWritten = true" in scan_payload
    assert "setInterval" in scan_payload
    assert "readCharacteristicForService" in scan_payload
    assert "DEFAULT_WIFI_SCAN_TIMEOUT_MS" in scan_payload
    assert "subscription.remove()" in scan_payload
    assert 'parsed.status === "idle" || parsed.status === "scanning"' in scan_payload
    assert 'parsed.status === "error"' in scan_payload
    assert 'parsed.status === "timeout"' in scan_payload
    assert 'parsed.cursor !== request.expectedCursor' in scan_payload


def test_mobile_ble_scan_rejects_stale_scan_ids():
    source = read_mobile_source(BLE_PROVISIONING)

    assert "scanId: number | null" in source
    assert 'scanId: typeof body.scan_id === "number"' in source
    assert "readBleWifiNetworksSnapshotScanId(device)" in source
    assert "minimumScanId: baselineScanId" in source
    assert "parsed.scanId > request.minimumScanId" in source
    assert "nextCursor !== null && scanId === null" in source
    assert "expectedScanId: scanId" in source
    assert "pageCommand.scan_id = scanId" in source
    assert "parsed.scanId !== request.expectedScanId" in source


def test_mobile_ble_scan_pages_and_normalizes_networks():
    source = read_mobile_source(BLE_PROVISIONING)

    assert 'requestBleWifiScanPayload(device, { command: "wifi_scan_start" }, { expectedCursor: 0, minimumScanId: baselineScanId ?? 0 })' in source
    assert "requestBleWifiScanPayload(device, pageCommand, { expectedCursor: nextCursor, expectedScanId: scanId })" in source
    assert "mergeBleWifiNetworks([...networks, ...parsed.networks])" in source
    assert "network.ssid.trim()" in source
    assert "Number.isFinite(network.rssi)" in source
    assert "network.rssi > existing.rssi" in source
    assert "return rightRssi - leftRssi" in source
    assert 'nextCursor: typeof body.next_cursor === "number"' in source


def test_mobile_add_device_keeps_manual_and_softap_fallbacks_separate():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)

    assert "My Wi-Fi is not listed" in screen
    assert "Your 2.4 GHz Wi-Fi name" in screen
    assert "Existing Wi-Fi setup fallback" in screen
    assert "Open PlantLab-Setup page" in screen
    assert "openSoftApSetup" in screen
    assert "loadDeviceWifiNetworks" in screen
    assert "Scanning nearby Wi-Fi networks..." in screen
    assert "PlantLab can only join 2.4 GHz Wi-Fi" in screen
    assert "No 2.4 GHz networks were reported by this device. You can still type your Wi-Fi name." in screen
    assert "PlantLab can only join 2.4 GHz Wi-Fi. If your network is not listed, type its name." in screen


def test_mobile_add_device_uses_in_app_ble_provisioning_as_primary_flow():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)

    assert "const canConfirmWifiDetails = wifiSsid.trim().length > 0 && wifiPassword.length > 0" in screen
    assert (
        "const canProvisionOverBle = Boolean(handoff?.setupToken && blePlatformUrl && canConfirmWifiDetails && !isProvisioningOverBle && !isWaitingForOnline)"
        in screen
    )
    assert 'label={isProvisioningOverBle ? "Confirming..." : "Confirm"}' in screen
    assert "Send provisioning over BLE" not in screen
    assert "provisionDeviceOverBle" in screen
    assert "setupToken: handoff.setupToken" in screen
    assert "platformUrl: blePlatformUrl" in screen
    assert "backendUrl: handoff.provisioningApiUrl" in screen
    assert "Retry BLE provisioning" in screen
    assert "maskSecret(handoff.setupToken)" not in screen
    assert 'label="Home Wi-Fi password"' in screen
    assert "secureTextEntry" in screen
    assert "wifiPassword" not in extract_function(screen, "function provisioningErrorMessage")
    assert "Share.share" not in screen
    assert "Show BLE write instructions" not in screen
    assert "Setup token: {handoff.setupToken}" not in screen
    assert "Expo Go does not write BLE characteristics directly" not in screen
    assert "Debug fallback: nRF Connect" not in screen


def test_mobile_add_device_simplifies_onboarding_and_keeps_password_local():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)
    submit = extract_function(screen, "async function onSubmit")
    create_claim = extract_function(screen, "async function createClaimTokenFromBleDevice")

    assert 'const DEFAULT_DEVICE_NAME = "Smart Planter"' in screen
    assert "placeholder={DEFAULT_DEVICE_NAME}" in screen
    assert "Leave blank to use {DEFAULT_DEVICE_NAME}." in screen
    assert "deviceName: deviceName.trim() || DEFAULT_DEVICE_NAME" in submit
    assert "deviceName: deviceName.trim() || DEFAULT_DEVICE_NAME" in create_claim
    assert 'label="Device location"' not in screen
    assert "setLocation" not in screen
    assert "location:" not in submit
    assert "location:" not in create_claim
    assert "const [wifiPassword, setWifiPassword] = useState(\"\")" in screen
    assert "Enter the Wi-Fi password for this network." in screen
    assert "AsyncStorage" not in screen


def test_mobile_add_device_waits_for_online_status_after_ble_provisioning():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)
    send_over_ble = extract_function(screen, "async function sendProvisioningOverBle")
    wait_online = extract_function(screen, "async function waitForProvisionedDeviceOnline")
    source = read_mobile_source(MOBILE_DEVICES_API)

    assert 'type AddDeviceStep = "find_device" | "wifi_provisioning" | "waiting_online"' in screen
    assert "const ONLINE_POLL_INTERVAL_MS = 2000" in screen
    assert "const ONLINE_POLL_TIMEOUT_MS = 90000" in screen
    assert "await waitForProvisionedDeviceOnline(device)" in send_over_ble
    assert 'setStep("waiting_online")' in wait_online
    assert "const expectedDeviceId = handoff.expectedDeviceId ?? device?.identity?.hardwareDeviceId" in wait_online
    assert "expectImage: false" in wait_online
    assert "result.status.deviceId && (result.status.online || result.status.ready)" in wait_online
    assert "router.replace(`/(app)/devices/${result.status.deviceId}?setup=complete`)" in wait_online
    assert "We could not confirm your Smart Planter is online yet." in screen
    assert "Retry online check" in screen
    assert "Retry provisioning" in screen
    assert "Connecting your Smart Planter... This may take a moment." in screen
    assert "getSetupStatus" in source
    assert 'params.set("expected_device_id", expectedDeviceId)' in source
    assert "online: response.online ?? false" in source


def test_mobile_add_device_ble_identity_replaces_required_serial_in_normal_flow():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)
    start_identity = extract_function(screen, "async function startBleIdentityOnboarding")
    create_claim = extract_function(screen, "async function createClaimTokenFromBleDevice")

    assert "Find PlantLab device" in screen
    assert "showSerialFallback" in screen
    assert "Use this only when BLE setup cannot find or read the device." in screen
    assert "Verify serial and create setup token" in screen
    assert "scanForBleProvisioningDevices()" in start_identity
    assert "devices.length > 1" in start_identity
    assert 'setBleDevicePickerMode("identity")' in start_identity
    assert "await createClaimTokenFromBleDevice(devices[0])" in start_identity
    assert "readBleDeviceIdentity(device.id)" in create_claim
    assert "requestDeviceClaimToken" in create_claim
    assert "deviceIdentity: identity" in create_claim
    assert "void loadSelectedBleDeviceWifiNetworks(deviceWithIdentity)" in create_claim
    assert "serialNumber" not in create_claim


def test_mobile_setup_handoff_maps_ble_provisioning_urls():
    source = read_mobile_source(MOBILE_DEVICES_API)

    assert "requestDeviceClaimToken" in source
    assert "platform_url?: string | null" in source
    assert "provisioning_api_url: string" in source
    assert "expected_device_id?: string | null" in source
    assert "platformUrl?: string" in source
    assert "provisioningApiUrl?: string" in source
    assert "expectedDeviceId?: string" in source
    assert "platformUrl: created.platform_url ?? undefined" in source
    assert "provisioningApiUrl: created.provisioning_api_url ?? undefined" in source
    assert "expectedDeviceId: created.expected_device_id ?? input.deviceIdentity.hardwareDeviceId" in source
    assert 'device_id: input.deviceIdentity.deviceId' in source
    assert 'hardware_device_id: input.deviceIdentity.hardwareDeviceId' in source


def test_mobile_ios_bluetooth_permission_mentions_provisioning():
    app_config = read_source(MOBILE_APP_CONFIG)

    assert "find and provision PlantLab devices" in app_config
    assert "read nearby Wi-Fi network names" not in app_config


def test_firmware_ble_scan_control_characteristic_contract():
    source = read_source(ESP32_BLE_PROVISIONING)
    header = read_source(ESP32_BLE_PROVISIONING_HEADER)

    assert 'kBleProvisioningWifiNetworksCharacteristicUuid =\n    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a904"' in header
    assert 'kBleProvisioningWifiScanControlCharacteristicUuid =\n    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a905"' in header
    assert "NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY" in source
    assert "NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR" in source
    assert "BleProvisioningServiceWifiScanControlCallbacks" in source
    assert "handleWifiScanControlWrite" in source
    assert "wifi_scan_start" in source
    assert "wifi_scan_page" in source
    assert "parseCursor(value)" in source
    assert "pending_wifi_scan_request_ready_ = true" in source


def test_firmware_ble_provisioning_priority_timeout_and_pause_contract():
    source = read_source(ESP32_MAIN)

    assert "constexpr uint32_t kBleProvisioningTimeoutMs = 4UL * 60UL * 1000UL" in source
    assert "return g_provisioning_requested || g_provisioning_mode || g_ble_provisioning.active();" in source
    assert 'Serial.println("[provisioning] provisioning_requested");' in source
    assert 'Serial.println("[provisioning] normal_tasks_paused");' in source
    assert 'Serial.println("[provisioning] normal_tasks_resumed");' in source
    assert 'Serial.println("[provisioning] ble_advertising_started");' in source
    assert 'Serial.println("[provisioning] provisioning_timeout");' in source
    assert "g_provisioning_requested = true;" in source
    assert "pauseNormalTasksForProvisioning();" in source
    assert "resumeNormalTasksAfterProvisioning();" in source

    check_button = extract_function(source, "void checkProvisioningButton() {")
    assert "event == PowerButtonEvent::kLongPress" in check_button
    assert "requestBleProvisioningMode(now)" in check_button

    connect_wifi = extract_function(source, "bool connectToWiFi")
    assert "if (!hasWifiCredentials() || provisioningPriorityActive())" in connect_wifi
    assert "checkProvisioningButton();" in connect_wifi
    assert "if (provisioningPriorityActive())" in connect_wifi
    assert "WiFi.disconnect(false, false);" in connect_wifi

    loop = extract_function(source, "void loop")
    priority_return = loop.index("if (provisioningPriorityActive())")
    command_poll = loop.index("poll_platform_commands(now)")
    capture_schedule = loop.index("pollCameraCaptureSchedule(now)")
    heartbeat = loop.index("send_platform_status(now)")
    reading = loop.index("send_platform_reading(now)")
    assert priority_return < command_poll
    assert priority_return < capture_schedule
    assert priority_return < heartbeat
    assert priority_return < reading


def test_firmware_ble_provisioning_lifecycle_logs_without_secret_values():
    source = read_source(ESP32_MAIN)

    for expected_log in (
        "[provisioning] credentials_received",
        "[provisioning] wifi_connecting ssid=%s",
        "[provisioning] wifi_connected",
        "[provisioning] backend_confirming",
        "[provisioning] device_online_confirmed",
        "[provisioning] provisioning_success",
        "[provisioning] provisioning_failed reason=",
    ):
        assert expected_log in source

    assert "password_len=%u" in source
    assert "claim_present=%u" in source
    assert "device_token_present=%u" in source
    assert "password=%s" not in source
    assert "claim_token=%s" not in source
    assert "device_token=%s" not in source


def test_firmware_ble_identity_characteristic_contract():
    source = read_source(ESP32_BLE_PROVISIONING)
    header = read_source(ESP32_BLE_PROVISIONING_HEADER)
    main = read_source(ESP32_MAIN)

    assert 'kBleProvisioningDeviceIdentityCharacteristicUuid =\n    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a906"' in header
    assert "const char* device_identity_json" in header
    assert "device_identity_characteristic_" in header
    assert "NIMBLE_PROPERTY::READ" in source
    assert "kBleProvisioningDeviceIdentityCharacteristicUuid" in source
    assert "device_identity_characteristic_->setValue" in source
    assert "stableHardwareDeviceId()" in main
    assert "bleProvisioningDeviceName()" in main
    assert '"device_id"' in main
    assert '"hardware_device_id"' in main
    assert '"software_version"' in main
    assert '"ble_name"' in main


def test_firmware_ble_scan_is_on_demand_async_and_timeout_guarded():
    source = read_source(ESP32_MAIN)
    start_ble = extract_function(source, "bool startBleProvisioningMode()")
    start_scan = extract_function(source, "void startBleWifiScan(unsigned long now)")
    start_scan_attempt = extract_function(source, "void startBleWifiScanAttempt(unsigned long now)")
    service_scan = extract_function(source, "void serviceBleWifiScan(unsigned long now)")

    assert "scanNearbyWifiNetworks(" not in start_ble
    assert "publishBleWifiScanStatus(plantlab::kBleWifiScanStatusIdle)" in start_ble
    assert "WiFi.mode(WIFI_OFF)" in start_ble
    assert "++g_ble_wifi_scan_id" in start_scan
    assert "startBleWifiScanAttempt(now)" in start_scan
    assert "WiFi.scanNetworks(true, true)" in start_scan_attempt
    assert "retryBleWifiScan(\"start failed\", now)" in start_scan_attempt
    assert "publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning)" in start_scan_attempt
    assert "request.command == plantlab::BleWifiScanCommand::kStart" in service_scan
    assert "request.command == plantlab::BleWifiScanCommand::kPage" in service_scan
    assert "kBleWifiScanTimeoutMs" in service_scan
    assert "plantlab::kBleWifiScanStatusTimeout" in service_scan
    assert "WiFi.scanComplete()" in service_scan
    assert "publishBleWifiScanPage(request.cursor)" in service_scan
