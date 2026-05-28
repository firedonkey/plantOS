from __future__ import annotations


SUPPORTED_SCENARIOS = {
    "normal": "No failure injection; useful for explicit config files.",
    "unstable_wifi": "Randomly drops some heartbeat, diagnostics, and poll cycles.",
    "ota_failure": "Fails OTA during validation with checksum_mismatch.",
    "ota_checksum_failure": "Alias for OTA checksum validation failure.",
    "ota_download_failure": "Fails OTA during download.",
    "ota_install_failure": "Fails OTA during install.",
    "ota_timeout": "Fails OTA with timeout.",
    "ota_rollback": "Reports a rolled_back OTA state during install.",
    "camera_disconnect": "Marks master camera runtime as offline/degraded.",
    "camera_flapping": "Alternates camera node status between online and offline.",
    "reboot_loop": "Periodically resets simulator uptime and increments reboot counter.",
    "heartbeat_timeout": "Suppresses heartbeat emissions.",
    "slow_command_ack": "Delays command ACKs.",
    "command_failure": "Fails all non-ACK command executions.",
    "low_memory": "Reports low free heap and degraded memory diagnostics.",
    "image_upload_failure": "Skips image uploads and reports image upload failures.",
}


def describe_scenarios() -> str:
    return "\n".join(f"- {name}: {description}" for name, description in sorted(SUPPORTED_SCENARIOS.items()))
