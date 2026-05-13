#pragma once

#include <memory>
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

class BleProvisioningServiceServerCallbacks;
class BleProvisioningServiceWriteCallbacks;

class BleProvisioningService {
 public:
  BleProvisioningService();
  ~BleProvisioningService();

  bool begin(const std::string& advertised_name, const char* fallback_platform_url);
  void stop();
  bool active() const;
  bool connected() const;

  bool hasPendingResult() const;
  ProvisioningParseResult takePendingResult();
  void setStatus(ProvisioningState state, ProvisioningParseError error = ProvisioningParseError::kNone);

 private:
  friend class BleProvisioningServiceServerCallbacks;
  friend class BleProvisioningServiceWriteCallbacks;

  void handleWrite(const std::string& value);
  void handleConnect();
  void handleDisconnect();
  void publishStatus(bool notify);

  bool active_ = false;
  bool connected_ = false;
  bool pending_result_ready_ = false;
  std::string fallback_platform_url_;
  ProvisioningState state_ = ProvisioningState::PROVISIONING_BLE;
  ProvisioningParseError last_error_ = ProvisioningParseError::kNone;
  ProvisioningParseResult pending_result_;
  NimBLEServer* server_ = nullptr;
  NimBLEService* service_ = nullptr;
  NimBLECharacteristic* write_characteristic_ = nullptr;
  NimBLECharacteristic* status_characteristic_ = nullptr;
  std::unique_ptr<BleProvisioningServiceServerCallbacks> server_callbacks_;
  std::unique_ptr<BleProvisioningServiceWriteCallbacks> write_callbacks_;
};

}  // namespace plantlab
