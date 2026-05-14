#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace plantlab {

constexpr size_t kBleWifiNetworksMaxJsonLength = 200;

struct WifiNetworkOption {
  WifiNetworkOption() = default;
  WifiNetworkOption(const std::string& ssid_value, int rssi_value) : ssid(ssid_value), rssi(rssi_value) {}

  std::string ssid;
  int rssi = -127;
};

constexpr const char* kBleWifiScanStatusIdle = "idle";
constexpr const char* kBleWifiScanStatusScanning = "scanning";
constexpr const char* kBleWifiScanStatusReady = "ready";
constexpr const char* kBleWifiScanStatusEmpty = "empty";
constexpr const char* kBleWifiScanStatusError = "error";
constexpr const char* kBleWifiScanStatusTimeout = "timeout";

std::string buildBleWifiNetworksJson(
    const std::vector<WifiNetworkOption>& options,
    uint32_t scan_id,
    size_t cursor,
    size_t max_bytes = kBleWifiNetworksMaxJsonLength);

std::string buildBleWifiNetworksJson(
    const std::vector<WifiNetworkOption>& options,
    size_t max_bytes = kBleWifiNetworksMaxJsonLength);

std::string buildBleWifiNetworksStatusJson(
    const char* status,
    uint32_t scan_id,
    size_t total = 0,
    size_t max_bytes = kBleWifiNetworksMaxJsonLength);

}  // namespace plantlab
