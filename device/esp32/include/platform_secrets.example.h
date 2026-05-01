#pragma once

// Copy this file to platform_secrets.h and fill in real local or cloud values.
// platform_secrets.h is gitignored so device credentials stay local.

#define PLANTLAB_WIFI_SSID ""
#define PLANTLAB_WIFI_PASSWORD ""
#define PLANTLAB_PROVISIONING_API_URL "https://plantlab-provision-api-418533861080.us-central1.run.app"
#define PLANTLAB_PLATFORM_URL "http://192.168.0.42:8000"

#define PLANTLAB_SENSOR_SEND_INTERVAL_MS 10000UL
#define PLANTLAB_COMMAND_POLL_INTERVAL_MS 2000UL
#define PLANTLAB_STATUS_INTERVAL_MS 10000UL
#define PLANTLAB_IMAGE_INTERVAL_MS 15000UL
#define PLANTLAB_WIFI_CONNECT_TIMEOUT_MS 20000UL
