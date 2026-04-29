import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


class BackendRegistrationClient:
    def __init__(self, backend_url: str, timeout_seconds: int = 20):
        self.backend_url = backend_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def register_device(
        self,
        *,
        device_id: str,
        claim_token: str,
        hardware_version: str,
        software_version: str,
        capabilities: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "device_id": device_id,
            "claim_token": claim_token,
            "hardware_version": hardware_version,
            "software_version": software_version,
            "capabilities": capabilities,
        }
        logger.info("registering device_id=%s with backend=%s", device_id, self.backend_url)
        response = requests.post(
            f"{self.backend_url}/api/devices/register",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok") or not data.get("device_access_token"):
            raise ValueError(f"backend registration failed: {data}")
        return data

    def create_setup_code(
        self,
        *,
        serial_number: str,
        device_name: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        payload = {"serial_number": serial_number}
        if device_name:
            payload["device_name"] = device_name
        if location:
            payload["location"] = location

        logger.info("creating setup code for serial_number=%s with backend=%s", serial_number, self.backend_url)
        response = requests.post(
            f"{self.backend_url}/api/devices/setup-code",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok") or not data.get("setup_code"):
            raise ValueError(f"setup code creation failed: {data}")
        return data

    def factory_reset_device(
        self,
        *,
        platform_url: str,
        platform_device_id: int,
        device_access_token: str,
    ) -> dict[str, Any]:
        logger.info(
            "requesting backend factory reset for platform_device_id=%s via platform=%s",
            platform_device_id,
            platform_url,
        )
        response = requests.post(
            f"{platform_url.rstrip('/')}/api/devices/{platform_device_id}/factory-reset",
            headers={"X-Device-Token": device_access_token, "Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise ValueError(f"backend factory reset failed: {data}")
        return data
