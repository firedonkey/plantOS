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
