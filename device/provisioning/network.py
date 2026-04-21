import logging
import subprocess

from .wifi import WiFiConnectionLayer, WiFiStatus


logger = logging.getLogger(__name__)


class NetworkManager:
    """Network command wrapper.

    Dry-run mode is the default so the provisioning flow can be tested without
    changing the Pi network stack. Real mode uses NetworkManager/nmcli because
    the current Raspberry Pi image runs NetworkManager.
    """

    def __init__(
        self,
        dry_run: bool = True,
        connect_timeout_seconds: int = 45,
        hotspot_password: str = "plantlabsetup",
    ):
        self.dry_run = dry_run
        self.connect_timeout_seconds = connect_timeout_seconds
        self.hotspot_password = hotspot_password
        self.wifi = WiFiConnectionLayer(
            dry_run=dry_run,
            connect_timeout_seconds=connect_timeout_seconds,
            mode="networkmanager",
        )

    def start_softap(self, ssid: str = "PlantLab-Setup") -> None:
        logger.info("starting SoftAP ssid=%s dry_run=%s", ssid, self.dry_run)
        self._run(
            [
                "sudo",
                "nmcli",
                "dev",
                "wifi",
                "hotspot",
                "ifname",
                "wlan0",
                "ssid",
                ssid,
                "password",
                self.hotspot_password,
            ],
            dry_run_message="NetworkManager hotspot start skipped",
        )

    def stop_softap(self) -> None:
        logger.info("stopping SoftAP dry_run=%s", self.dry_run)
        self._run(
            ["sudo", "nmcli", "connection", "down", "Hotspot"],
            dry_run_message="NetworkManager hotspot stop skipped",
        )

    def connect_wifi(self, ssid: str, password: str) -> WiFiStatus:
        logger.info("connecting to Wi-Fi ssid=%s dry_run=%s", ssid, self.dry_run)
        return self.wifi.connect(ssid, password)

    def scan_wifi_networks(self) -> WiFiStatus:
        logger.info("scanning Wi-Fi networks dry_run=%s", self.dry_run)
        return self.wifi.scan_networks()

    def _run(self, command: list[str], dry_run_message: str | None = None) -> None:
        if self.dry_run:
            logger.info("[dry-run] %s", dry_run_message or " ".join(command))
            return

        logger.info("running command: %s", " ".join(command))
        subprocess.run(command, check=True)
