import logging
import time
from typing import Any

import requests

from .backend import BackendRegistrationClient
from .device_identity import stable_device_id
from .network import NetworkManager
from .state import ProvisioningState
from .storage import ProvisioningStore
from .web import LocalSetupServer, ProvisioningPayload


logger = logging.getLogger(__name__)


class ProvisioningService:
    def __init__(
        self,
        *,
        backend_url: str,
        platform_url: str | None,
        state_file: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        dry_run: bool = True,
        hardware_version: str = "raspberry_pi_3",
        software_version: str = "0.1.0",
        capabilities: dict[str, Any] | None = None,
        hotspot_password: str = "plantlabsetup",
        backend_retry_attempts: int = 12,
        backend_retry_delay_seconds: float = 5.0,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.platform_url = platform_url.rstrip("/") if platform_url else None
        self.host = host
        self.port = port
        self.hardware_version = hardware_version
        self.software_version = software_version
        self.capabilities = capabilities or {
            "camera": True,
            "pump": True,
            "moisture_sensor": True,
            "light_control": True,
        }
        self.store = ProvisioningStore(state_file)
        self.network = NetworkManager(dry_run=dry_run, hotspot_password=hotspot_password)
        self.backend = BackendRegistrationClient(self.backend_url)
        self.backend_retry_attempts = max(1, int(backend_retry_attempts))
        self.backend_retry_delay_seconds = max(0.0, float(backend_retry_delay_seconds))

    def run(self) -> None:
        if self.store.is_provisioned():
            logger.info("device is already provisioned")
            return

        logger.info("device is not provisioned; entering SoftAP setup flow")
        self._set_state(ProvisioningState.AP_MODE)
        self.network.start_softap(ssid="PlantLab-Setup")

        server = LocalSetupServer(
            host=self.host,
            port=self.port,
            backend_url=self.backend_url,
            network_manager=self.network,
        )
        try:
            server.start()
            logger.info("open http://192.168.4.1 or http://<pi-ip>:%s to provision", self.port)
            payload = server.wait_for_payload()
        finally:
            server.shutdown()
            server.join(timeout=5)

        self._handle_payload(payload)

    def factory_reset(self, *, forget_wifi: bool = True) -> None:
        logger.warning("factory reset requested")
        data = self.store.load()
        platform_device_id = data.get("platform_device_id")
        device_access_token = data.get("device_access_token")
        platform_url = data.get("platform_url") or self.platform_url
        wifi_ssid = data.get("wifi_ssid", "")

        if platform_url and platform_device_id and device_access_token:
            try:
                self.backend.factory_reset_device(
                    platform_url=platform_url,
                    platform_device_id=int(platform_device_id),
                    device_access_token=str(device_access_token),
                )
                logger.info("backend ownership released for platform_device_id=%s", platform_device_id)
            except Exception as exc:
                logger.warning("backend factory reset cleanup failed: %s", exc)
        else:
            logger.info("backend cleanup skipped; provisioning record is incomplete")

        if forget_wifi and wifi_ssid:
            status = self.network.forget_wifi(str(wifi_ssid))
            if status.ok:
                logger.info("forgot Wi-Fi profile for ssid=%s", wifi_ssid)
            else:
                logger.warning("could not forget Wi-Fi profile: %s", status.message)
        elif wifi_ssid:
            logger.info("preserving Wi-Fi profile for ssid=%s during reprovision pre-reset", wifi_ssid)

        self.store.delete()
        logger.info("local provisioning state deleted; device is ready as a new device")

    def _handle_payload(self, payload: ProvisioningPayload) -> None:
        device_id = stable_device_id()
        self._set_state(
            ProvisioningState.CREDENTIALS_RECEIVED,
            device_id=device_id,
            backend_url=payload.backend_url,
            wifi_ssid=payload.ssid,
            wifi_password=payload.password,
            claim_token=payload.claim_token,
            hardware_version=self.hardware_version,
            software_version=self.software_version,
            capabilities=self.capabilities,
            last_error=None,
        )

        try:
            self.network.stop_softap()

            self._set_state(ProvisioningState.WIFI_CONNECTING)
            wifi_status = self.network.connect_wifi(payload.ssid, payload.password)
            if not wifi_status.ok:
                logger.error("Wi-Fi connection failed: %s details=%s", wifi_status.message, wifi_status.details)
                raise RuntimeError(wifi_status.message)

            self._set_state(ProvisioningState.BACKEND_REGISTERING)
            backend = BackendRegistrationClient(payload.backend_url)
            claim_token = payload.claim_token
            if not claim_token:
                logger.info(
                    "creating setup code after Wi-Fi reconnect for serial_number=%s",
                    payload.serial_number,
                )
                setup = self._with_backend_retries(
                    "setup code creation",
                    backend.create_setup_code,
                    serial_number=payload.serial_number,
                    device_name=payload.device_name or None,
                    location=payload.location or None,
                )
                claim_token = str(setup["setup_code"])

            registration = self._with_backend_retries(
                "device registration",
                backend.register_device,
                device_id=device_id,
                claim_token=claim_token,
                hardware_version=self.hardware_version,
                software_version=self.software_version,
                capabilities=self.capabilities,
            )

            self._set_state(
                ProvisioningState.ONLINE,
                platform_device_id=registration.get("platform_device_id"),
                device_access_token=registration["device_access_token"],
                device_name=registration.get("device_name"),
                platform_url=self.platform_url,
                claim_token=None,
                last_error=None,
            )
            logger.info("provisioning complete; device is online")
        except Exception as exc:
            logger.exception("provisioning failed")
            self._set_state(ProvisioningState.ERROR, last_error=str(exc))
            raise

    def _set_state(self, state: ProvisioningState, **changes) -> None:
        logger.info("provisioning state -> %s", state.value)
        self.store.update(provisioning_state=state.value, **changes)

    def _with_backend_retries(self, action_label: str, operation, **kwargs):
        last_error: Exception | None = None
        for attempt in range(1, self.backend_retry_attempts + 1):
            try:
                if attempt > 1:
                    logger.info(
                        "retrying %s attempt %s/%s",
                        action_label,
                        attempt,
                        self.backend_retry_attempts,
                    )
                return operation(**kwargs)
            except Exception as exc:
                last_error = exc
                if not self._is_retryable_backend_error(exc):
                    raise
                if attempt >= self.backend_retry_attempts:
                    break
                logger.warning(
                    "%s failed on attempt %s/%s: %s; retrying in %.1fs",
                    action_label,
                    attempt,
                    self.backend_retry_attempts,
                    exc,
                    self.backend_retry_delay_seconds,
                )
                time.sleep(self.backend_retry_delay_seconds)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _is_retryable_backend_error(error: Exception) -> bool:
        if isinstance(error, (requests.ConnectionError, requests.Timeout)):
            return True
        if isinstance(error, requests.HTTPError) and error.response is not None:
            return error.response.status_code >= 500 or error.response.status_code == 429
        return False
