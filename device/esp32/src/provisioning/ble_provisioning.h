#pragma once

#include <freertos/FreeRTOS.h>
#include <freertos/portmacro.h>

#include <memory>
#include <stddef.h>
#include <string>

#include "provisioning/provisioning_payload.h"

class NimBLECharacteristic;
class NimBLEServer;
class NimBLEService;

namespace plantlab {

constexpr const char* kBleProvisioningServiceUuid = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901";
constexpr const char* kBleProvisioningWriteCharacteristicUuid =
    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902";
constexpr const char* kBleProvisioningStatusCharacteristicUuid =
    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903";
constexpr const char* kBleProvisioningWifiNetworksCharacteristicUuid =
    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a904";
constexpr const char* kBleProvisioningWifiScanControlCharacteristicUuid =
    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a905";
constexpr const char* kBleProvisioningDeviceIdentityCharacteristicUuid =
    "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a906";

enum class BleWifiScanCommand {
  kNone = 0,
  kStart,
  kPage,
};

struct BleWifiScanRequest {
  BleWifiScanCommand command = BleWifiScanCommand::kNone;
  size_t cursor = 0;
};

class BleProvisioningServiceServerCallbacks;
class BleProvisioningServiceWriteCallbacks;
class BleProvisioningServiceWifiScanControlCallbacks;

class BleProvisioningService {
 public:
  BleProvisioningService();
  ~BleProvisioningService();

  bool begin(
      const std::string& advertised_name,
      const char* fallback_platform_url,
      const char* device_identity_json);
  void stop();
  bool active() const;
  bool connected() const;

  bool hasPendingResult() const;
  ProvisioningParseResult takePendingResult();
  void setStatus(ProvisioningState state, ProvisioningParseError error = ProvisioningParseError::kNone);
  void setAcceptingWrites(bool accepting);
  void setWifiNetworksJson(const std::string& wifi_networks_json, bool notify = true);
  bool hasPendingWifiScanRequest() const;
  BleWifiScanRequest takePendingWifiScanRequest();

 private:
  friend class BleProvisioningServiceServerCallbacks;
  friend class BleProvisioningServiceWriteCallbacks;
  friend class BleProvisioningServiceWifiScanControlCallbacks;

  void handleWrite(const std::string& value);
  void handleWifiScanControlWrite(const std::string& value);
  void handleConnect();
  void handleDisconnect();
  void publishStatus(bool notify);

  bool active_ = false;
  bool connected_ = false;
  bool pending_result_ready_ = false;
  bool pending_wifi_scan_request_ready_ = false;
  bool accepting_writes_ = true;
  std::string fallback_platform_url_;
  ProvisioningState state_ = ProvisioningState::PROVISIONING_BLE;
  ProvisioningParseError last_error_ = ProvisioningParseError::kNone;
  ProvisioningParseResult pending_result_;
  BleWifiScanRequest pending_wifi_scan_request_;
  mutable portMUX_TYPE pending_lock_ = portMUX_INITIALIZER_UNLOCKED;
  mutable portMUX_TYPE wifi_scan_lock_ = portMUX_INITIALIZER_UNLOCKED;
  NimBLEServer* server_ = nullptr;
  NimBLEService* service_ = nullptr;
  NimBLECharacteristic* write_characteristic_ = nullptr;
  NimBLECharacteristic* status_characteristic_ = nullptr;
  NimBLECharacteristic* wifi_networks_characteristic_ = nullptr;
  NimBLECharacteristic* wifi_scan_control_characteristic_ = nullptr;
  NimBLECharacteristic* device_identity_characteristic_ = nullptr;
  std::unique_ptr<BleProvisioningServiceServerCallbacks> server_callbacks_;
  std::unique_ptr<BleProvisioningServiceWriteCallbacks> write_callbacks_;
  std::unique_ptr<BleProvisioningServiceWifiScanControlCallbacks> wifi_scan_control_callbacks_;
};

}  // namespace plantlab
