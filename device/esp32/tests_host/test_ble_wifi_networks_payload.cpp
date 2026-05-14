#include <assert.h>
#include <string.h>

#include <string>
#include <vector>

#include "provisioning/wifi_networks_payload.h"

namespace {

size_t find_json_integer(const std::string& json, const char* key) {
  const size_t key_position = json.find(key);
  assert(key_position != std::string::npos);
  size_t position = key_position + strlen(key);
  size_t value = 0;
  while (position < json.size() && json[position] >= '0' && json[position] <= '9') {
    value = value * 10 + static_cast<size_t>(json[position] - '0');
    ++position;
  }
  return value;
}

void test_empty_list() {
  const std::string json = plantlab::buildBleWifiNetworksJson({});
  assert(json.find("\"source\":\"esp32-ble\"") != std::string::npos);
  assert(json.find("\"status\":\"empty\"") != std::string::npos);
  assert(json.find("\"networks\":[]") != std::string::npos);
  assert(json.find("\"count\":0") != std::string::npos);
  assert(json.find("\"total\":0") != std::string::npos);
  assert(json.find("\"truncated\":false") != std::string::npos);
}

void test_normal_list() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"HomeWiFi", -47},
      {"LabWiFi", -62},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  assert(json.find("\"ssid\":\"HomeWiFi\"") != std::string::npos);
  assert(json.find("\"rssi\":-47") != std::string::npos);
  assert(json.find("\"ssid\":\"LabWiFi\"") != std::string::npos);
  assert(json.find("\"count\":2") != std::string::npos);
  assert(json.find("\"truncated\":false") != std::string::npos);
}

void test_blank_ssids_are_excluded() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"  ", -40},
      {" HomeWiFi ", -47},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  assert(json.find("\"ssid\":\"HomeWiFi\"") != std::string::npos);
  assert(json.find("\"count\":1") != std::string::npos);
}

void test_duplicate_ssids_keep_strongest_rssi() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"HomeWiFi", -82},
      {"LabWiFi", -55},
      {"HomeWiFi", -42},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  assert(json.find("\"ssid\":\"HomeWiFi\",\"rssi\":-42") != std::string::npos);
  assert(json.find("\"rssi\":-82") == std::string::npos);
  assert(json.find("\"count\":2") != std::string::npos);
}

void test_networks_are_sorted_by_signal_then_name() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"Zoo", -45},
      {"Alpha", -45},
      {"HomeWiFi", -30},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  const size_t home = json.find("\"ssid\":\"HomeWiFi\"");
  const size_t alpha = json.find("\"ssid\":\"Alpha\"");
  const size_t zoo = json.find("\"ssid\":\"Zoo\"");
  assert(home != std::string::npos);
  assert(alpha != std::string::npos);
  assert(zoo != std::string::npos);
  assert(home < alpha);
  assert(alpha < zoo);
}

void test_json_escapes_ssid_values() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"Home \"Lab\" WiFi", -47},
      {"Backslash\\Network", -51},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  assert(json.find("\"ssid\":\"Home \\\"Lab\\\" WiFi\"") != std::string::npos);
  assert(json.find("\"ssid\":\"Backslash\\\\Network\"") != std::string::npos);
  assert(json.find("\"count\":2") != std::string::npos);
}

void test_status_payloads_are_bounded_and_secret_free() {
  const char* statuses[] = {
      plantlab::kBleWifiScanStatusIdle,
      plantlab::kBleWifiScanStatusScanning,
      plantlab::kBleWifiScanStatusError,
      plantlab::kBleWifiScanStatusTimeout,
  };
  for (const char* status : statuses) {
    const std::string json = plantlab::buildBleWifiNetworksStatusJson(status, 9, 4);
    assert(json.size() <= plantlab::kBleWifiNetworksMaxJsonLength);
    assert(json.find("\"source\":\"esp32-ble\"") != std::string::npos);
    assert(json.find("\"scan_id\":9") != std::string::npos);
    assert(json.find(std::string("\"status\":\"") + status + "\"") != std::string::npos);
    assert(json.find("\"networks\":[]") != std::string::npos);
    assert(json.find("\"total\":4") != std::string::npos);
    assert(json.find("password") == std::string::npos);
    assert(json.find("token") == std::string::npos);
    assert(json.find("claim") == std::string::npos);
    assert(json.find("url") == std::string::npos);
  }
}

void test_truncation_stays_under_limit() {
  std::vector<plantlab::WifiNetworkOption> networks;
  for (int index = 0; index < 20; ++index) {
    networks.push_back({"VeryLongHomeWifiNetworkName" + std::to_string(index), -30 - index});
  }
  const size_t max_bytes = 180;
  const std::string json = plantlab::buildBleWifiNetworksJson(networks, max_bytes);
  assert(json.size() <= max_bytes);
  assert(json.find("\"truncated\":true") != std::string::npos);
}

void test_large_results_page_with_scan_id_and_cursor() {
  std::vector<plantlab::WifiNetworkOption> networks;
  for (int index = 0; index < 14; ++index) {
    networks.push_back({"PlantLabNetwork" + std::to_string(index), -30 - index});
  }

  const size_t max_bytes = 260;
  const std::string first_page = plantlab::buildBleWifiNetworksJson(networks, 42, 0, max_bytes);
  assert(first_page.size() <= max_bytes);
  assert(first_page.find("\"scan_id\":42") != std::string::npos);
  assert(first_page.find("\"status\":\"ready\"") != std::string::npos);
  assert(first_page.find("\"cursor\":0") != std::string::npos);
  assert(first_page.find("\"total\":14") != std::string::npos);
  assert(first_page.find("\"truncated\":true") != std::string::npos);

  const size_t next_cursor = find_json_integer(first_page, "\"next_cursor\":");
  assert(next_cursor > 0);
  assert(next_cursor < networks.size());

  const std::string second_page = plantlab::buildBleWifiNetworksJson(networks, 42, next_cursor, max_bytes);
  assert(second_page.size() <= max_bytes);
  assert(second_page.find("\"scan_id\":42") != std::string::npos);
  assert(second_page.find("\"cursor\":" + std::to_string(next_cursor)) != std::string::npos);
  assert(second_page.find("\"ssid\":\"PlantLabNetwork" + std::to_string(next_cursor) + "\"") != std::string::npos);
}

void test_secret_free_output() {
  const std::vector<plantlab::WifiNetworkOption> networks = {
      {"HomeWiFi", -47},
  };
  const std::string json = plantlab::buildBleWifiNetworksJson(networks);
  assert(json.find("password") == std::string::npos);
  assert(json.find("token") == std::string::npos);
  assert(json.find("claim") == std::string::npos);
  assert(json.find("url") == std::string::npos);
}

}  // namespace

int main() {
  test_empty_list();
  test_normal_list();
  test_blank_ssids_are_excluded();
  test_duplicate_ssids_keep_strongest_rssi();
  test_networks_are_sorted_by_signal_then_name();
  test_json_escapes_ssid_values();
  test_status_payloads_are_bounded_and_secret_free();
  test_truncation_stays_under_limit();
  test_large_results_page_with_scan_id_and_cursor();
  test_secret_free_output();
  return 0;
}
