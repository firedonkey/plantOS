#include "provisioning/ble_provisioning.h"

#include <NimBLEDevice.h>

namespace plantlab {
namespace {

std::string statusJson(ProvisioningState state, ProvisioningParseError error) {
  std::string json = "{\"state\":\"";
  json += provisioningStateName(state);
  json += "\",\"ready\":";
  json += state == ProvisioningState::PROVISIONING_BLE ? "true" : "false";
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
  pending_result_ready_ = false;
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
  if (write_characteristic_ == nullptr || status_characteristic_ == nullptr) {
    stop();
    return false;
  }

  write_callbacks_.reset(new BleProvisioningServiceWriteCallbacks(this));
  write_characteristic_->setCallbacks(write_callbacks_.get());
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
  server_ = nullptr;
  service_ = nullptr;
  write_characteristic_ = nullptr;
  status_characteristic_ = nullptr;
  server_callbacks_.reset();
  write_callbacks_.reset();
}

bool BleProvisioningService::active() const {
  return active_;
}

bool BleProvisioningService::connected() const {
  return connected_;
}

bool BleProvisioningService::hasPendingResult() const {
  return pending_result_ready_;
}

ProvisioningParseResult BleProvisioningService::takePendingResult() {
  pending_result_ready_ = false;
  return pending_result_;
}

void BleProvisioningService::setStatus(ProvisioningState state, ProvisioningParseError error) {
  state_ = state;
  last_error_ = error;
  publishStatus(true);
}

void BleProvisioningService::handleWrite(const std::string& value) {
  pending_result_ = parseBleProvisioningPayload(
      value.c_str(),
      value.length(),
      fallback_platform_url_.c_str());
  pending_result_ready_ = true;
  if (!pending_result_.ok) {
    setStatus(provisioningStateAfterInvalidPayload(), pending_result_.error);
  }
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
  const std::string json = statusJson(state_, last_error_);
  status_characteristic_->setValue(json);
  if (notify) {
    status_characteristic_->notify();
  }
}

}  // namespace plantlab
