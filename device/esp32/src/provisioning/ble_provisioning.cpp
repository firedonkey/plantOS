#include "provisioning/ble_provisioning.h"

#include <NimBLEDevice.h>

#include "provisioning/wifi_networks_payload.h"

namespace plantlab {
namespace {

std::string statusJson(ProvisioningState state, ProvisioningParseError error, bool accepting_writes) {
  std::string json = "{\"state\":\"";
  json += provisioningStateName(state);
  json += "\",\"ready\":";
  json += state == ProvisioningState::PROVISIONING_BLE && accepting_writes ? "true" : "false";
  if (error != ProvisioningParseError::kNone) {
    json += ",\"error\":\"";
    json += provisioningParseErrorCode(error);
    json += "\"";
  }
  if (state == ProvisioningState::PROVISIONING_SUCCESS) {
    json += ",\"rebooting\":true";
  }
  json += "}";
  return json;
}

bool containsCommand(const std::string& value, const char* command) {
  return value.find(command) != std::string::npos;
}

size_t parseCursor(const std::string& value) {
  const size_t key = value.find("\"cursor\"");
  if (key == std::string::npos) {
    return 0;
  }
  const size_t separator = value.find(':', key);
  if (separator == std::string::npos) {
    return 0;
  }
  size_t index = separator + 1;
  while (index < value.length() && (value[index] == ' ' || value[index] == '\t')) {
    ++index;
  }
  size_t cursor = 0;
  while (index < value.length() && value[index] >= '0' && value[index] <= '9') {
    cursor = cursor * 10 + static_cast<size_t>(value[index] - '0');
    ++index;
  }
  return cursor;
}

}  // namespace

class BleProvisioningServiceServerCallbacks : public NimBLEServerCallbacks {
 public:
  explicit BleProvisioningServiceServerCallbacks(BleProvisioningService* owner) : owner_(owner) {}

  void onConnect(NimBLEServer* server) override {
    (void)server;
    owner_->handleConnect();
  }

  void onDisconnect(NimBLEServer* server) override {
    (void)server;
    owner_->handleDisconnect();
  }

 private:
  BleProvisioningService* owner_;
};

class BleProvisioningServiceWriteCallbacks : public NimBLECharacteristicCallbacks {
 public:
  explicit BleProvisioningServiceWriteCallbacks(BleProvisioningService* owner) : owner_(owner) {}

  void onWrite(NimBLECharacteristic* characteristic) override {
    owner_->handleWrite(characteristic->getValue());
  }

 private:
  BleProvisioningService* owner_;
};

class BleProvisioningServiceWifiScanControlCallbacks : public NimBLECharacteristicCallbacks {
 public:
  explicit BleProvisioningServiceWifiScanControlCallbacks(BleProvisioningService* owner) : owner_(owner) {}

  void onWrite(NimBLECharacteristic* characteristic) override {
    owner_->handleWifiScanControlWrite(characteristic->getValue());
  }

 private:
  BleProvisioningService* owner_;
};

BleProvisioningService::BleProvisioningService() = default;
BleProvisioningService::~BleProvisioningService() {
  stop();
}

bool BleProvisioningService::begin(const std::string& advertised_name, const char* fallback_platform_url) {
  if (active_) {
    return true;
  }

  fallback_platform_url_ = fallback_platform_url == nullptr ? "" : fallback_platform_url;
  state_ = ProvisioningState::PROVISIONING_BLE;
  last_error_ = ProvisioningParseError::kNone;
  accepting_writes_ = true;
  pending_result_ready_ = false;
  pending_wifi_scan_request_ready_ = false;
  connected_ = false;

  NimBLEDevice::init(advertised_name);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);

  server_ = NimBLEDevice::createServer();
  if (server_ == nullptr) {
    return false;
  }
  server_callbacks_.reset(new BleProvisioningServiceServerCallbacks(this));
  server_->setCallbacks(server_callbacks_.get());

  service_ = server_->createService(kBleProvisioningServiceUuid);
  if (service_ == nullptr) {
    stop();
    return false;
  }

  write_characteristic_ = service_->createCharacteristic(
      kBleProvisioningWriteCharacteristicUuid,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  status_characteristic_ = service_->createCharacteristic(
      kBleProvisioningStatusCharacteristicUuid,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  wifi_networks_characteristic_ = service_->createCharacteristic(
      kBleProvisioningWifiNetworksCharacteristicUuid,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  wifi_scan_control_characteristic_ = service_->createCharacteristic(
      kBleProvisioningWifiScanControlCharacteristicUuid,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  if (write_characteristic_ == nullptr || status_characteristic_ == nullptr ||
      wifi_networks_characteristic_ == nullptr || wifi_scan_control_characteristic_ == nullptr) {
    stop();
    return false;
  }

  write_callbacks_.reset(new BleProvisioningServiceWriteCallbacks(this));
  wifi_scan_control_callbacks_.reset(new BleProvisioningServiceWifiScanControlCallbacks(this));
  write_characteristic_->setCallbacks(write_callbacks_.get());
  wifi_scan_control_characteristic_->setCallbacks(wifi_scan_control_callbacks_.get());
  wifi_networks_characteristic_->setValue(buildBleWifiNetworksStatusJson(kBleWifiScanStatusIdle, 0));
  publishStatus(false);

  service_->start();
  NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(kBleProvisioningServiceUuid);
  advertising->setScanResponse(true);
  advertising->start();

  active_ = true;
  return true;
}

void BleProvisioningService::stop() {
  if (!active_ && server_ == nullptr) {
    return;
  }

  NimBLEDevice::getAdvertising()->stop();
  NimBLEDevice::deinit(true);
  active_ = false;
  connected_ = false;
  accepting_writes_ = false;
  portENTER_CRITICAL(&pending_lock_);
  pending_result_ready_ = false;
  pending_result_ = ProvisioningParseResult{};
  portEXIT_CRITICAL(&pending_lock_);
  portENTER_CRITICAL(&wifi_scan_lock_);
  pending_wifi_scan_request_ready_ = false;
  pending_wifi_scan_request_ = BleWifiScanRequest{};
  portEXIT_CRITICAL(&wifi_scan_lock_);
  server_ = nullptr;
  service_ = nullptr;
  write_characteristic_ = nullptr;
  status_characteristic_ = nullptr;
  wifi_networks_characteristic_ = nullptr;
  wifi_scan_control_characteristic_ = nullptr;
  server_callbacks_.reset();
  write_callbacks_.reset();
  wifi_scan_control_callbacks_.reset();
}

bool BleProvisioningService::active() const {
  return active_;
}

bool BleProvisioningService::connected() const {
  return connected_;
}

bool BleProvisioningService::hasPendingResult() const {
  portENTER_CRITICAL(&pending_lock_);
  const bool ready = pending_result_ready_;
  portEXIT_CRITICAL(&pending_lock_);
  return ready;
}

ProvisioningParseResult BleProvisioningService::takePendingResult() {
  bool status_changed = false;
  portENTER_CRITICAL(&pending_lock_);
  const ProvisioningParseResult result = pending_result_;
  if (provisioningShouldStopAcceptingWritesOnTake(
          pending_result_ready_,
          result.ok,
          accepting_writes_)) {
    accepting_writes_ = false;
    status_changed = true;
  }
  pending_result_ready_ = false;
  pending_result_ = ProvisioningParseResult{};
  portEXIT_CRITICAL(&pending_lock_);
  if (status_changed) {
    publishStatus(true);
  }
  return result;
}

void BleProvisioningService::setStatus(ProvisioningState state, ProvisioningParseError error) {
  state_ = state;
  last_error_ = error;
  publishStatus(true);
}

void BleProvisioningService::setAcceptingWrites(bool accepting) {
  portENTER_CRITICAL(&pending_lock_);
  accepting_writes_ = accepting;
  portEXIT_CRITICAL(&pending_lock_);
  publishStatus(true);
}

void BleProvisioningService::setWifiNetworksJson(const std::string& wifi_networks_json, bool notify) {
  if (wifi_networks_characteristic_ == nullptr) {
    return;
  }
  wifi_networks_characteristic_->setValue(wifi_networks_json);
  if (notify) {
    wifi_networks_characteristic_->notify();
  }
}

bool BleProvisioningService::hasPendingWifiScanRequest() const {
  portENTER_CRITICAL(&wifi_scan_lock_);
  const bool ready = pending_wifi_scan_request_ready_;
  portEXIT_CRITICAL(&wifi_scan_lock_);
  return ready;
}

BleWifiScanRequest BleProvisioningService::takePendingWifiScanRequest() {
  portENTER_CRITICAL(&wifi_scan_lock_);
  const BleWifiScanRequest request = pending_wifi_scan_request_;
  pending_wifi_scan_request_ready_ = false;
  pending_wifi_scan_request_ = BleWifiScanRequest{};
  portEXIT_CRITICAL(&wifi_scan_lock_);
  return request;
}

void BleProvisioningService::handleWrite(const std::string& value) {
  portENTER_CRITICAL(&pending_lock_);
  const bool pending = pending_result_ready_;
  const bool accepting = accepting_writes_;
  portEXIT_CRITICAL(&pending_lock_);

  ProvisioningParseError error = provisioningWriteRejectionError(state_, pending, accepting);
  if (error != ProvisioningParseError::kNone) {
    setStatus(state_, error);
    return;
  }

  ProvisioningParseResult result = parseBleProvisioningPayload(
      value.c_str(),
      value.length(),
      fallback_platform_url_.c_str());

  portENTER_CRITICAL(&pending_lock_);
  error = provisioningWriteRejectionError(state_, pending_result_ready_, accepting_writes_);
  if (error == ProvisioningParseError::kNone) {
    pending_result_ = result;
    pending_result_ready_ = true;
    result = pending_result_;
  } else {
    result = ProvisioningParseResult{};
    result.error = error;
  }
  portEXIT_CRITICAL(&pending_lock_);

  if (result.error == ProvisioningParseError::kBusy ||
      result.error == ProvisioningParseError::kAlreadyCommitted) {
    setStatus(state_, result.error);
    return;
  }
  if (!result.ok) {
    setStatus(provisioningStateAfterInvalidPayload(), result.error);
  }
}

void BleProvisioningService::handleWifiScanControlWrite(const std::string& value) {
  BleWifiScanRequest request;
  if (containsCommand(value, "wifi_scan_start")) {
    request.command = BleWifiScanCommand::kStart;
    request.cursor = 0;
  } else if (containsCommand(value, "wifi_scan_page")) {
    request.command = BleWifiScanCommand::kPage;
    request.cursor = parseCursor(value);
  } else {
    return;
  }

  portENTER_CRITICAL(&wifi_scan_lock_);
  pending_wifi_scan_request_ = request;
  pending_wifi_scan_request_ready_ = true;
  portEXIT_CRITICAL(&wifi_scan_lock_);
}

void BleProvisioningService::handleConnect() {
  connected_ = true;
  publishStatus(true);
}

void BleProvisioningService::handleDisconnect() {
  connected_ = false;
  if (active_) {
    NimBLEDevice::startAdvertising();
  }
}

void BleProvisioningService::publishStatus(bool notify) {
  if (status_characteristic_ == nullptr) {
    return;
  }
  const std::string json = statusJson(state_, last_error_, accepting_writes_);
  status_characteristic_->setValue(json);
  if (notify) {
    status_characteristic_->notify();
  }
}

}  // namespace plantlab
