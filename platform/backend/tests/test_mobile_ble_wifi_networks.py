from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADD_DEVICE_SCREEN = REPO_ROOT / "platform/mobile/src/screens/AddDeviceScreen.tsx"
BLE_PROVISIONING = REPO_ROOT / "platform/mobile/src/ble/bleProvisioning.ts"
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
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"could not extract function for signature: {signature}")


def test_mobile_wifi_dropdown_uses_ble_not_softap_networks_endpoint():
    screen = read_mobile_source(ADD_DEVICE_SCREEN)
    ble_helper = read_mobile_source(BLE_PROVISIONING)

    assert "loadBleWifiNetworks" in screen
    assert "readBleWifiNetworksFromDevice" in screen
    assert "Load nearby Wi-Fi over BLE" in screen
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


def test_mobile_ble_scan_subscribes_before_request_and_times_out_safely():
    source = read_mobile_source(BLE_PROVISIONING)

    subscribe_index = source.index("device.monitorCharacteristicForService")
    write_index = source.index("writeCharacteristicWithResponseForService")
    assert subscribe_index < write_index
    assert "commandWritten = true" in source
    assert "setInterval" in source
    assert "readCharacteristicForService" in source
    assert "DEFAULT_WIFI_SCAN_TIMEOUT_MS" in source
    assert "subscription.remove()" in source
    assert 'parsed.status === "idle" || parsed.status === "scanning"' in source
    assert 'parsed.status === "error"' in source
    assert 'parsed.status === "timeout"' in source
    assert 'parsed.cursor !== request.expectedCursor' in source


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

    assert 'requestBleWifiScanPayload(device, { command: "wifi_scan_start" }, { expectedCursor: 0, minimumScanId: baselineScanId })' in source
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
    assert "Type Wi-Fi name manually" in screen
    assert "Existing Wi-Fi setup fallback" in screen
    assert "Open PlantLab-Setup page" in screen
    assert "openSoftApSetup" in screen
    assert "loadDeviceWifiNetworks" in screen
    assert "Scanning nearby Wi-Fi..." in screen
    assert "5 GHz-only networks will not appear" in screen


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


def test_firmware_ble_scan_is_on_demand_async_and_timeout_guarded():
    source = read_source(ESP32_MAIN)
    start_ble = extract_function(source, "bool startBleProvisioningMode()")
    start_scan = extract_function(source, "void startBleWifiScan(unsigned long now)")
    service_scan = extract_function(source, "void serviceBleWifiScan(unsigned long now)")

    assert "scanNearbyWifiNetworks(" not in start_ble
    assert "publishBleWifiScanStatus(plantlab::kBleWifiScanStatusIdle)" in start_ble
    assert "WiFi.mode(WIFI_OFF)" in start_ble
    assert "WiFi.scanNetworks(true, true)" in start_scan
    assert "++g_ble_wifi_scan_id" in start_scan
    assert "publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning)" in start_scan
    assert "request.command == plantlab::BleWifiScanCommand::kStart" in service_scan
    assert "request.command == plantlab::BleWifiScanCommand::kPage" in service_scan
    assert "kBleWifiScanTimeoutMs" in service_scan
    assert "plantlab::kBleWifiScanStatusTimeout" in service_scan
    assert "WiFi.scanComplete()" in service_scan
    assert "publishBleWifiScanPage(request.cursor)" in service_scan
