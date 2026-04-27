#pragma once

#include <stdint.h>

constexpr uint32_t ESPNOW_TEST_MAGIC = 0x504C4142;  // "PLAB"
constexpr uint8_t ESPNOW_TEST_VERSION = 1;

enum class EspNowMessageKind : uint8_t {
  kCommand = 1,
  kAck = 2,
  kHealthReport = 3,
};

enum class EspNowCommandType : uint8_t {
  kCaptureImage = 1,
  kProvisionStart = 2,
  kHealthCheck = 3,
};

enum class EspNowAckStatus : uint8_t {
  kOk = 0,
  kUnsupported = 1,
  kBusy = 2,
  kFailed = 3,
};

// Single fixed-size packet for all test messages.
// Field usage depends on message kind:
// - COMMAND: command + request_id are required.
// - ACK: command + request_id + ack_status.
// - HEALTH_REPORT: request_id (correlates to health command), health fields.
struct __attribute__((packed)) EspNowPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t kind;
  uint8_t command;
  uint8_t ack_status;
  uint32_t request_id;
  uint32_t timestamp_ms;
  uint32_t value_u32_1;
  uint32_t value_u32_2;
};
