import logging
from typing import Any

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
        state_file: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        dry_run: bool = True,
        hardware_version: str = "raspberry_pi_3",
        software_version: str = "0.1.0",
        capabilities: dict[str, Any] | None = None,
        hotspot_password: str = "plantlabsetup",
    ):
        self.backend_url = backend_url.rstrip("/")
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

    def factory_reset(self) -> None:
        logger.warning("factory reset requested; deleting provisioning state")
        self.store.delete()
        self._set_state(ProvisioningState.FACTORY_RESET)

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
                setup = backend.create_setup_code(
                    serial_number=payload.serial_number,
                    device_name=payload.device_name or None,
                    location=payload.location or None,
                )
                claim_token = str(setup["setup_code"])

            registration = backend.register_device(
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
