#include <assert.h>
#include <string.h>

#include "espnow_test_protocol.h"

namespace {
void test_payload_assembly() {
  CameraProvisioningPayload payload{};
  const bool ok = espnow_build_provisioning_payload(
      &payload,
      3,
      2,
      17,
      "PlantLabWiFi",
      "super-secret-pass",
      "https://marspotatolab.com",
      "shared-device-token-123");
  assert(ok);
  assert(payload.config_version == 3);
  assert(payload.camera_node_index == 2);
  assert(payload.platform_device_id == 17);
  assert(strcmp(payload.wifi_ssid, "PlantLabWiFi") == 0);
  assert(strcmp(payload.wifi_password, "super-secret-pass") == 0);
  assert(strcmp(payload.platform_url, "https://marspotatolab.com") == 0);
  assert(strcmp(payload.device_token, "shared-device-token-123") == 0);
  assert(espnow_validate_provisioning_payload(payload));
}

void test_ack_completion() {
  const uint8_t target_mac[6] = {0x24, 0x6F, 0x28, 0xAA, 0xBB, 0xCC};
  CameraProvisioningPayload payload{};
  assert(espnow_build_provisioning_payload(
      &payload,
      1,
      1,
      11,
      "ssid",
      "password",
      "http://192.168.0.55:8000",
      "token-123"));

  MasterProvisioningSession session{};
  espnow_start_provisioning_session(&session, target_mac, 41, payload, 1000, 1500, 3);
  assert(espnow_should_send_provisioning_packet(session));

  EspNowPacket outbound{};
  espnow_build_provisioning_packet(session, 1000, &outbound);
  assert(static_cast<EspNowCommandType>(outbound.command) == EspNowCommandType::kProvisionStart);
  espnow_mark_provisioning_packet_sent(&session, 1000);
  assert(session.state == MasterProvisioningState::kAwaitingAck);
  assert(session.attempts_started == 1);

  EspNowPacket ack{};
  ack.magic = ESPNOW_TEST_MAGIC;
  ack.version = ESPNOW_TEST_VERSION;
  ack.kind = static_cast<uint8_t>(EspNowMessageKind::kAck);
  ack.command = static_cast<uint8_t>(EspNowCommandType::kProvisionStart);
  ack.ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  ack.request_id = 41;
  assert(espnow_handle_provisioning_ack(&session, target_mac, ack));
  assert(session.state == MasterProvisioningState::kSucceeded);
  assert(!session.active);
}

void test_retry_and_timeout() {
  const uint8_t target_mac[6] = {0x24, 0x6F, 0x28, 0xAA, 0xBB, 0xCC};
  CameraProvisioningPayload payload{};
  assert(espnow_build_provisioning_payload(
      &payload,
      1,
      1,
      11,
      "ssid",
      "password",
      "http://192.168.0.55:8000",
      "token-123"));

  MasterProvisioningSession session{};
  espnow_start_provisioning_session(&session, target_mac, 77, payload, 2000, 1000, 3);
  assert(espnow_should_send_provisioning_packet(session));
  espnow_mark_provisioning_packet_sent(&session, 2000);

  espnow_update_provisioning_session(&session, 2500);
  assert(session.state == MasterProvisioningState::kAwaitingAck);

  espnow_update_provisioning_session(&session, 3001);
  assert(session.state == MasterProvisioningState::kAwaitingSend);
  assert(session.send_pending);

  espnow_mark_provisioning_packet_sent(&session, 3001);
  espnow_update_provisioning_session(&session, 4002);
  assert(session.state == MasterProvisioningState::kAwaitingSend);
  espnow_mark_provisioning_packet_sent(&session, 4002);
  espnow_update_provisioning_session(&session, 5003);
  assert(session.state == MasterProvisioningState::kTimedOut);
  assert(!session.active);
  assert(session.final_ack_status == EspNowAckStatus::kFailed);
}
}  // namespace

int main() {
  test_payload_assembly();
  test_ack_completion();
  test_retry_and_timeout();
  return 0;
}
