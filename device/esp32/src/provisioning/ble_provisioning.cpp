#include "provisioning/ble_provisioning.h"

#include <Arduino.h>
#include <NimBLEDevice.h>

#include <cstring>

#include "provisioning/wifi_networks_payload.h"

namespace plantlab {
namespace {

constexpr TickType_t kBleMutexTimeout = pdMS_TO_TICKS(500);

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

bool takeMutex(SemaphoreHandle_t mutex) {
  return mutex != nullptr && xSemaphoreTake(mutex, kBleMutexTimeout) == pdTRUE;
}

void giveMutex(SemaphoreHandle_t mutex) {
  if (mutex != nullptr) {
    xSemaphoreGive(mutex);
  }
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

bool BleProvisioningService::ensureSynchronization() {
  if (pending_mutex_ == nullptr) {
    pending_mutex_ = xSemaphoreCreateMutex();
  }
  if (wifi_scan_mutex_ == nullptr) {
    wifi_scan_mutex_ = xSemaphoreCreateMutex();
  }
  if (characteristic_mutex_ == nullptr) {
    characteristic_mutex_ = xSemaphoreCreateMutex();
  }
  return pending_mutex_ != nullptr && wifi_scan_mutex_ != nullptr && characteristic_mutex_ != nullptr;
}

bool BleProvisioningService::begin(
    const std::string& advertised_name,
    const char* fallback_platform_url,
    const char* device_identity_json) {
  if (active_) {
    return true;
  }
  if (!ensureSynchronization()) {
    stop();
    return false;
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
  server_->setCallbacks(server_callbacks_.get(), false);

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
  device_identity_characteristic_ = service_->createCharacteristic(
      kBleProvisioningDeviceIdentityCharacteristicUuid,
      NIMBLE_PROPERTY::READ);
  if (write_characteristic_ == nullptr || status_characteristic_ == nullptr ||
      wifi_networks_characteristic_ == nullptr || wifi_scan_control_characteristic_ == nullptr ||
      device_identity_characteristic_ == nullptr) {
    stop();
    return false;
  }

  write_callbacks_.reset(new BleProvisioningServiceWriteCallbacks(this));
  wifi_scan_control_callbacks_.reset(new BleProvisioningServiceWifiScanControlCallbacks(this));
  write_characteristic_->setCallbacks(write_callbacks_.get());
  wifi_scan_control_characteristic_->setCallbacks(wifi_scan_control_callbacks_.get());
  wifi_networks_characteristic_->setValue(buildBleWifiNetworksStatusJson(kBleWifiScanStatusIdle, 0));
  const char* identity_json = device_identity_json == nullptr ? "{}" : device_identity_json;
  device_identity_characteristic_->setValue(
      reinterpret_cast<const uint8_t*>(identity_json),
      strlen(identity_json));
  Serial.printf("[provisioning] BLE identity characteristic loaded len=%u\n", static_cast<unsigned int>(strlen(identity_json)));
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
  if (takeMutex(pending_mutex_)) {
    pending_result_ready_ = false;
    pending_result_ = ProvisioningParseResult{};
    giveMutex(pending_mutex_);
  }
  if (takeMutex(wifi_scan_mutex_)) {
    pending_wifi_scan_request_ready_ = false;
    pending_wifi_scan_request_ = BleWifiScanRequest{};
    giveMutex(wifi_scan_mutex_);
  }
  server_ = nullptr;
  service_ = nullptr;
  write_characteristic_ = nullptr;
  status_characteristic_ = nullptr;
  wifi_networks_characteristic_ = nullptr;
  wifi_scan_control_characteristic_ = nullptr;
  device_identity_characteristic_ = nullptr;
  server_callbacks_.reset();
  write_callbacks_.reset();
  wifi_scan_control_callbacks_.reset();
  if (pending_mutex_ != nullptr) {
    vSemaphoreDelete(pending_mutex_);
    pending_mutex_ = nullptr;
  }
  if (wifi_scan_mutex_ != nullptr) {
    vSemaphoreDelete(wifi_scan_mutex_);
    wifi_scan_mutex_ = nullptr;
  }
  if (characteristic_mutex_ != nullptr) {
    vSemaphoreDelete(characteristic_mutex_);
    characteristic_mutex_ = nullptr;
  }
}

bool BleProvisioningService::active() const {
  return active_;
}

bool BleProvisioningService::connected() const {
  return connected_;
}

bool BleProvisioningService::hasPendingResult() const {
  if (!takeMutex(pending_mutex_)) {
    return false;
  }
  const bool ready = pending_result_ready_;
  giveMutex(pending_mutex_);
  return ready;
}

ProvisioningParseResult BleProvisioningService::takePendingResult() {
  bool status_changed = false;
  ProvisioningParseResult result;
  if (!takeMutex(pending_mutex_)) {
    return result;
  }
  result = pending_result_;
  if (provisioningShouldStopAcceptingWritesOnTake(
          pending_result_ready_,
          result.ok,
          accepting_writes_)) {
    accepting_writes_ = false;
    status_changed = true;
  }
  pending_result_ready_ = false;
  pending_result_ = ProvisioningParseResult{};
  giveMutex(pending_mutex_);
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
  if (takeMutex(pending_mutex_)) {
    accepting_writes_ = accepting;
    giveMutex(pending_mutex_);
  } else {
    accepting_writes_ = accepting;
  }
  publishStatus(true);
}

void BleProvisioningService::setWifiNetworksJson(const std::string& wifi_networks_json, bool notify) {
  if (wifi_networks_characteristic_ == nullptr) {
    return;
  }
  if (!takeMutex(characteristic_mutex_)) {
    return;
  }
  wifi_networks_characteristic_->setValue(
      reinterpret_cast<const uint8_t*>(wifi_networks_json.data()),
      wifi_networks_json.size());
  if (notify) {
    wifi_networks_characteristic_->notify();
  }
  giveMutex(characteristic_mutex_);
}

bool BleProvisioningService::hasPendingWifiScanRequest() const {
  if (!takeMutex(wifi_scan_mutex_)) {
    return false;
  }
  const bool ready = pending_wifi_scan_request_ready_;
  giveMutex(wifi_scan_mutex_);
  return ready;
}

BleWifiScanRequest BleProvisioningService::takePendingWifiScanRequest() {
  BleWifiScanRequest request;
  if (!takeMutex(wifi_scan_mutex_)) {
    return request;
  }
  request = pending_wifi_scan_request_;
  pending_wifi_scan_request_ready_ = false;
  pending_wifi_scan_request_ = BleWifiScanRequest{};
  giveMutex(wifi_scan_mutex_);
  return request;
}

void BleProvisioningService::handleWrite(const std::string& value) {
  if (!takeMutex(pending_mutex_)) {
    setStatus(state_, ProvisioningParseError::kBusy);
    return;
  }
  const bool pending = pending_result_ready_;
  const bool accepting = accepting_writes_;
  giveMutex(pending_mutex_);

  ProvisioningParseError error = provisioningWriteRejectionError(state_, pending, accepting);
  if (error != ProvisioningParseError::kNone) {
    setStatus(state_, error);
    return;
  }

  ProvisioningParseResult result = parseBleProvisioningPayload(
      value.c_str(),
      value.length(),
      fallback_platform_url_.c_str());

  if (!takeMutex(pending_mutex_)) {
    setStatus(state_, ProvisioningParseError::kBusy);
    return;
  }
  error = provisioningWriteRejectionError(state_, pending_result_ready_, accepting_writes_);
  if (error == ProvisioningParseError::kNone) {
    pending_result_ = result;
    pending_result_ready_ = true;
    result = pending_result_;
  } else {
    result = ProvisioningParseResult{};
    result.error = error;
  }
  giveMutex(pending_mutex_);

  if (result.error == ProvisioningParseError::kBusy ||
      result.error == ProvisioningParseError::kAlreadyCommitted) {
    setStatus(state_, result.error);
    return;
  }
  if (!result.ok) {
    setStatus(provisioningStateAfterInvalidPayload(), result.error);
    return;
  }
  setStatus(provisioningStateAfterValidPayload());
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

  if (takeMutex(wifi_scan_mutex_)) {
    pending_wifi_scan_request_ = request;
    pending_wifi_scan_request_ready_ = true;
    giveMutex(wifi_scan_mutex_);
  }
}

void BleProvisioningService::handleConnect() {
  connected_ = true;
  Serial.println("[provisioning] ble_connected");
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
  if (!takeMutex(characteristic_mutex_)) {
    return;
  }
  status_characteristic_->setValue(
      reinterpret_cast<const uint8_t*>(json.data()),
      json.size());
  if (notify) {
    status_characteristic_->notify();
  }
  giveMutex(characteristic_mutex_);
}

}  // namespace plantlab
