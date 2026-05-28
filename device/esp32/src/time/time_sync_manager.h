#pragma once

#include <Arduino.h>
#include <stddef.h>
#include <time.h>

namespace plantlab {
namespace time_sync {

enum class TimeSyncStatus {
  kUnsynchronized,
  kSynchronizing,
  kSynchronized,
  kSyncFailed,
};

void begin();
void service(bool wifi_connected, unsigned long now_ms);

TimeSyncStatus status();
const char* statusName();
bool synchronized();
uint32_t syncAttemptCount();

bool currentUtcIso8601(char* buffer, size_t buffer_size);
String currentUtcIso8601();
bool lastSyncUtcIso8601(char* buffer, size_t buffer_size);
String lastSyncUtcIso8601();

void resetForTesting();
void setSynchronizedTimeForTesting(time_t utc_time);

}  // namespace time_sync
}  // namespace plantlab
