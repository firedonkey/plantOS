#include "time/time_sync_manager.h"

#include <stdio.h>

#if defined(ARDUINO_ARCH_ESP32)
#include <esp_sntp.h>
#endif

#include "config.h"

namespace plantlab {
namespace time_sync {
namespace {

constexpr time_t kMinimumValidUtc = 1704067200;  // 2024-01-01T00:00:00Z
constexpr const char* kFallbackTimestamp = "1970-01-01T00:00:00Z";

TimeSyncStatus g_status = TimeSyncStatus::kUnsynchronized;
unsigned long g_attempt_started_at_ms = 0;
unsigned long g_next_retry_at_ms = 0;
uint32_t g_attempt_count = 0;
time_t g_last_sync_utc = 0;
bool g_started_once = false;
bool g_test_time_active = false;
time_t g_test_now_utc = 0;

bool isValidUtc(time_t value) {
  return value >= kMinimumValidUtc;
}

bool formatUtc(time_t value, char* buffer, size_t buffer_size) {
  if (buffer == nullptr || buffer_size < 21 || !isValidUtc(value)) {
    if (buffer != nullptr && buffer_size > 0) {
      buffer[0] = '\0';
    }
    return false;
  }
  struct tm utc_tm {};
  if (gmtime_r(&value, &utc_tm) == nullptr) {
    buffer[0] = '\0';
    return false;
  }
  const size_t written = strftime(buffer, buffer_size, "%Y-%m-%dT%H:%M:%SZ", &utc_tm);
  return written > 0;
}

time_t currentSystemUtc() {
  if (g_test_time_active) {
    return g_test_now_utc;
  }
  time_t now = 0;
  time(&now);
  return now;
}

void startSyncAttempt(unsigned long now_ms) {
  g_status = TimeSyncStatus::kSynchronizing;
  g_attempt_started_at_ms = now_ms;
  ++g_attempt_count;
  g_started_once = true;

#if defined(ARDUINO_ARCH_ESP32)
  configTime(0, 0, PLANTLAB_NTP_SERVER_1, PLANTLAB_NTP_SERVER_2);
  Serial.printf(
      "[time-sync] NTP sync started attempt=%lu servers=%s,%s\n",
      static_cast<unsigned long>(g_attempt_count),
      PLANTLAB_NTP_SERVER_1,
      PLANTLAB_NTP_SERVER_2);
#endif
}

void markSynchronized(time_t now_utc) {
  g_status = TimeSyncStatus::kSynchronized;
  g_last_sync_utc = now_utc;
  g_next_retry_at_ms = 0;
#if defined(ARDUINO_ARCH_ESP32)
  char buffer[32]{};
  if (formatUtc(now_utc, buffer, sizeof(buffer))) {
    Serial.printf("[time-sync] NTP sync success utc=%s\n", buffer);
  } else {
    Serial.println("[time-sync] NTP sync success");
  }
#endif
}

void markFailed(unsigned long now_ms) {
  g_status = TimeSyncStatus::kSyncFailed;
  g_next_retry_at_ms = now_ms + PLANTLAB_NTP_RETRY_INTERVAL_MS;
#if defined(ARDUINO_ARCH_ESP32)
  Serial.printf(
      "[time-sync] NTP sync failed; retry_in_ms=%lu\n",
      static_cast<unsigned long>(PLANTLAB_NTP_RETRY_INTERVAL_MS));
#endif
}

}  // namespace

void begin() {
  g_status = isValidUtc(currentSystemUtc()) ? TimeSyncStatus::kSynchronized : TimeSyncStatus::kUnsynchronized;
  if (g_status == TimeSyncStatus::kSynchronized) {
    g_last_sync_utc = currentSystemUtc();
  }
}

void service(bool wifi_connected, unsigned long now_ms) {
  if (!wifi_connected) {
    return;
  }

  const time_t now_utc = currentSystemUtc();
  if (isValidUtc(now_utc)) {
    if (g_status != TimeSyncStatus::kSynchronized) {
      markSynchronized(now_utc);
    }
    return;
  }

  if (g_status == TimeSyncStatus::kSynchronizing) {
    if (now_ms - g_attempt_started_at_ms >= PLANTLAB_NTP_SYNC_TIMEOUT_MS) {
      markFailed(now_ms);
    }
    return;
  }

  if (!g_started_once || g_status == TimeSyncStatus::kUnsynchronized ||
      (g_status == TimeSyncStatus::kSyncFailed && static_cast<long>(now_ms - g_next_retry_at_ms) >= 0)) {
    startSyncAttempt(now_ms);
  }
}

TimeSyncStatus status() {
  return g_status;
}

const char* statusName() {
  switch (g_status) {
    case TimeSyncStatus::kSynchronizing:
      return "synchronizing";
    case TimeSyncStatus::kSynchronized:
      return "synchronized";
    case TimeSyncStatus::kSyncFailed:
      return "sync_failed";
    case TimeSyncStatus::kUnsynchronized:
    default:
      return "unsynchronized";
  }
}

bool synchronized() {
  return g_status == TimeSyncStatus::kSynchronized && isValidUtc(currentSystemUtc());
}

uint32_t syncAttemptCount() {
  return g_attempt_count;
}

bool currentUtcIso8601(char* buffer, size_t buffer_size) {
  const time_t now_utc = currentSystemUtc();
  if (g_status == TimeSyncStatus::kSynchronized && formatUtc(now_utc, buffer, buffer_size)) {
    return true;
  }
  if (buffer != nullptr && buffer_size > 0) {
    snprintf(buffer, buffer_size, "%s", kFallbackTimestamp);
  }
  return false;
}

String currentUtcIso8601() {
  char buffer[32]{};
  currentUtcIso8601(buffer, sizeof(buffer));
  return String(buffer);
}

bool lastSyncUtcIso8601(char* buffer, size_t buffer_size) {
  return formatUtc(g_last_sync_utc, buffer, buffer_size);
}

String lastSyncUtcIso8601() {
  char buffer[32]{};
  return lastSyncUtcIso8601(buffer, sizeof(buffer)) ? String(buffer) : String("");
}

void resetForTesting() {
  g_status = TimeSyncStatus::kUnsynchronized;
  g_attempt_started_at_ms = 0;
  g_next_retry_at_ms = 0;
  g_attempt_count = 0;
  g_last_sync_utc = 0;
  g_started_once = false;
  g_test_time_active = true;
  g_test_now_utc = 0;
}

void setSynchronizedTimeForTesting(time_t utc_time) {
  g_status = TimeSyncStatus::kSynchronized;
  g_last_sync_utc = utc_time;
  g_test_time_active = true;
  g_test_now_utc = utc_time;
}

}  // namespace time_sync
}  // namespace plantlab
