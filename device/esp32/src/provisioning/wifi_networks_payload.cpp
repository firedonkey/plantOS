#include "provisioning/wifi_networks_payload.h"

#include <ArduinoJson.h>

#include <algorithm>

namespace plantlab {
namespace {

std::string trim(const std::string& value) {
  const size_t start = value.find_first_not_of(" \t\r\n");
  if (start == std::string::npos) {
    return "";
  }
  const size_t end = value.find_last_not_of(" \t\r\n");
  return value.substr(start, end - start + 1);
}

std::vector<WifiNetworkOption> normalizeNetworks(const std::vector<WifiNetworkOption>& options) {
  std::vector<WifiNetworkOption> networks;
  for (const WifiNetworkOption& option : options) {
    const std::string ssid = trim(option.ssid);
    if (ssid.empty()) {
      continue;
    }
    auto existing = std::find_if(
        networks.begin(),
        networks.end(),
        [&ssid](const WifiNetworkOption& network) { return network.ssid == ssid; });
    if (existing == networks.end()) {
      networks.push_back(WifiNetworkOption{ssid, option.rssi});
    } else if (option.rssi > existing->rssi) {
      existing->rssi = option.rssi;
    }
  }
  std::sort(
      networks.begin(),
      networks.end(),
      [](const WifiNetworkOption& left, const WifiNetworkOption& right) {
        if (left.rssi == right.rssi) {
          return left.ssid < right.ssid;
        }
        return left.rssi > right.rssi;
      });
  return networks;
}

std::string serializePayload(
    const std::vector<WifiNetworkOption>& networks,
    const char* status,
    uint32_t scan_id,
    size_t cursor,
    size_t total,
    size_t next_cursor,
    bool truncated) {
  JsonDocument payload;
  payload["source"] = "esp32-ble";
  payload["scan_id"] = scan_id;
  payload["status"] = status;
  JsonArray items = payload["networks"].to<JsonArray>();
  for (const WifiNetworkOption& network : networks) {
    JsonObject item = items.add<JsonObject>();
    item["ssid"] = network.ssid;
    item["rssi"] = network.rssi;
  }
  payload["count"] = items.size();
  payload["total"] = total;
  payload["cursor"] = cursor;
  if (next_cursor > 0 && next_cursor < total) {
    payload["next_cursor"] = next_cursor;
  } else {
    payload["next_cursor"] = nullptr;
  }
  payload["truncated"] = truncated;

  std::string body;
  serializeJson(payload, body);
  return body;
}

}  // namespace

std::string buildBleWifiNetworksJson(
    const std::vector<WifiNetworkOption>& options,
    uint32_t scan_id,
    size_t cursor,
    size_t max_bytes) {
  const std::vector<WifiNetworkOption> normalized = normalizeNetworks(options);
  std::vector<WifiNetworkOption> included;
  const size_t total = normalized.size();
  const char* status = total == 0 ? kBleWifiScanStatusEmpty : kBleWifiScanStatusReady;
  size_t next_cursor = cursor;
  bool truncated = cursor < total;

  for (size_t index = cursor; index < total; ++index) {
    const WifiNetworkOption& network = normalized[index];
    std::vector<WifiNetworkOption> candidate = included;
    candidate.push_back(network);
    const size_t candidate_next_cursor = index + 1;
    const bool would_truncate = candidate_next_cursor < total;
    const std::string candidate_json =
        serializePayload(candidate, status, scan_id, cursor, total, candidate_next_cursor, would_truncate);
    if (candidate_json.size() > max_bytes) {
      truncated = true;
      break;
    }
    included = candidate;
    next_cursor = candidate_next_cursor;
    truncated = would_truncate;
  }

  std::string body = serializePayload(included, status, scan_id, cursor, total, next_cursor, truncated);
  if (body.size() <= max_bytes || included.empty()) {
    return body;
  }

  while (!included.empty() && body.size() > max_bytes) {
    included.pop_back();
    next_cursor = cursor + included.size();
    body = serializePayload(included, status, scan_id, cursor, total, next_cursor, true);
  }
  return body;
}

std::string buildBleWifiNetworksJson(const std::vector<WifiNetworkOption>& options, size_t max_bytes) {
  return buildBleWifiNetworksJson(options, 0, 0, max_bytes);
}

std::string buildBleWifiNetworksStatusJson(
    const char* status,
    uint32_t scan_id,
    size_t total,
    size_t max_bytes) {
  const std::vector<WifiNetworkOption> networks;
  std::string body = serializePayload(networks, status, scan_id, 0, total, 0, false);
  if (body.size() <= max_bytes) {
    return body;
  }
  return "{\"source\":\"esp32-ble\",\"status\":\"error\",\"networks\":[],\"count\":0,\"total\":0,\"truncated\":false}";
}

}  // namespace plantlab
