import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


logger = logging.getLogger(__name__)


CommandRunner = Callable[[list[str], int], subprocess.CompletedProcess]


@dataclass
class WiFiStatus:
    ok: bool
    stage: str
    message: str
    attempts: int = 0
    details: dict = field(default_factory=dict)


@dataclass
class WiFiNetwork:
    ssid: str
    signal: int | None = None
    security: str | None = None


class WiFiConnectionLayer:
    """Small Raspberry Pi Wi-Fi layer.

    The default implementation writes a wpa_supplicant-style network block,
    restarts networking, and checks connectivity. All shell command execution
    is isolated in `_run()` so the commands can be replaced later.
    """

    def __init__(
        self,
        *,
        config_path: str | Path = "/etc/wpa_supplicant/wpa_supplicant.conf",
        dry_run: bool = True,
        retries: int = 3,
        connect_timeout_seconds: int = 45,
        connectivity_host: str = "8.8.8.8",
        mode: str = "networkmanager",
        runner: CommandRunner | None = None,
    ):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.retries = retries
        self.connect_timeout_seconds = connect_timeout_seconds
        self.connectivity_host = connectivity_host
        self.mode = mode
        self.runner = runner or self._default_runner

    def scan_networks(self) -> WiFiStatus:
        """Scan nearby Wi-Fi networks and return a de-duplicated SSID list.

        Scanning is read-only, so it still runs in dry-run mode. Dry-run only
        skips operations that write credentials or restart networking.
        """
        scanners = [
            self._scan_with_nmcli,
            self._scan_with_iwlist,
        ]
        errors = []
        for scanner in scanners:
            status = scanner()
            if status.ok:
                return status
            errors.append(status.details)

        return WiFiStatus(
            ok=False,
            stage="wifi_scan",
            message="Could not scan Wi-Fi networks.",
            details={"errors": errors},
        )

    def credentials_exist(self, ssid: str | None = None) -> WiFiStatus:
        """Check whether Wi-Fi credentials are already present on disk."""
        if not self.config_path.exists():
            return WiFiStatus(
                ok=False,
                stage="credentials_check",
                message=f"Wi-Fi config does not exist: {self.config_path}",
            )

        try:
            text = self.config_path.read_text(encoding="utf-8")
        except OSError as exc:
            return WiFiStatus(
                ok=False,
                stage="credentials_check",
                message=f"Could not read Wi-Fi config: {exc}",
            )

        has_network_block = "network={" in text and "ssid=" in text
        if ssid:
            has_network_block = has_network_block and f'ssid="{_escape_wpa_value(ssid)}"' in text

        return WiFiStatus(
            ok=has_network_block,
            stage="credentials_check",
            message="Wi-Fi credentials found." if has_network_block else "Wi-Fi credentials not found.",
        )

    def write_credentials(self, ssid: str, password: str) -> WiFiStatus:
        """Write credentials through an atomic temp-file replacement."""
        if not ssid.strip():
            return WiFiStatus(
                ok=False,
                stage="write_credentials",
                message="Wi-Fi SSID is required.",
            )

        config_text = self._build_config(ssid=ssid.strip(), password=password)
        if self.dry_run:
            logger.info("[dry-run] would write Wi-Fi credentials to %s", self.config_path)
            return WiFiStatus(
                ok=True,
                stage="write_credentials",
                message="Dry-run Wi-Fi credentials write succeeded.",
                details={"config_path": str(self.config_path)},
            )

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=str(self.config_path.parent),
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(config_text)

            os.chmod(temp_path, 0o600)
            temp_path.replace(self.config_path)
            return WiFiStatus(
                ok=True,
                stage="write_credentials",
                message="Wi-Fi credentials written.",
                details={"config_path": str(self.config_path)},
            )
        except OSError as exc:
            return WiFiStatus(
                ok=False,
                stage="write_credentials",
                message=f"Could not write Wi-Fi credentials: {exc}",
            )

    def restart_networking(self) -> WiFiStatus:
        """Restart common Raspberry Pi Wi-Fi services."""
        commands = [
            ["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"],
            ["sudo", "systemctl", "restart", "wpa_supplicant"],
            ["sudo", "systemctl", "restart", "dhcpcd"],
        ]

        if self.dry_run:
            logger.info("[dry-run] would restart networking services")
            return WiFiStatus(
                ok=True,
                stage="restart_networking",
                message="Dry-run networking restart succeeded.",
            )

        errors = []
        for command in commands:
            result = self._run(command, timeout=20)
            if result.returncode == 0:
                return WiFiStatus(
                    ok=True,
                    stage="restart_networking",
                    message=f"Networking restarted using: {' '.join(command)}",
                )
            errors.append(
                {
                    "command": command,
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                }
            )

        return WiFiStatus(
            ok=False,
            stage="restart_networking",
            message="Could not restart Wi-Fi networking.",
            details={"errors": errors},
        )

    def test_connectivity(self, timeout_seconds: int | None = None) -> WiFiStatus:
        """Poll until the Pi can reach the internet or timeout expires."""
        timeout = timeout_seconds or self.connect_timeout_seconds
        deadline = time.monotonic() + timeout
        attempts = 0

        if self.dry_run:
            logger.info("[dry-run] would test internet connectivity")
            return WiFiStatus(
                ok=True,
                stage="connectivity_check",
                message="Dry-run internet connectivity check succeeded.",
                attempts=1,
            )

        while time.monotonic() < deadline:
            attempts += 1
            result = self._run(
                ["ping", "-c", "1", "-W", "2", self.connectivity_host],
                timeout=5,
            )
            if result.returncode == 0:
                return WiFiStatus(
                    ok=True,
                    stage="connectivity_check",
                    message="Internet connectivity confirmed.",
                    attempts=attempts,
                )
            time.sleep(2)

        return WiFiStatus(
            ok=False,
            stage="connectivity_check",
            message="Internet connectivity check timed out.",
            attempts=attempts,
        )

    def connect(self, ssid: str, password: str) -> WiFiStatus:
        """Write credentials, restart networking, and wait for connectivity."""
        if self.mode == "networkmanager":
            return self.connect_with_networkmanager(ssid, password)

        last_status = WiFiStatus(
            ok=False,
            stage="connect",
            message="Wi-Fi connection was not attempted.",
        )

        for attempt in range(1, self.retries + 1):
            logger.info("Wi-Fi connect attempt %s/%s ssid=%s", attempt, self.retries, ssid)

            write_status = self.write_credentials(ssid, password)
            if not write_status.ok:
                write_status.attempts = attempt
                return write_status

            restart_status = self.restart_networking()
            if not restart_status.ok:
                restart_status.attempts = attempt
                last_status = restart_status
                continue

            connectivity_status = self.test_connectivity()
            connectivity_status.attempts = attempt
            if connectivity_status.ok:
                return connectivity_status

            last_status = connectivity_status

        return WiFiStatus(
            ok=False,
            stage=last_status.stage,
            message=f"Wi-Fi connection failed after {self.retries} attempt(s): {last_status.message}",
            attempts=self.retries,
            details=last_status.details,
        )

    def connect_with_networkmanager(self, ssid: str, password: str) -> WiFiStatus:
        """Connect using NetworkManager and nmcli."""
        last_status = WiFiStatus(
            ok=False,
            stage="networkmanager_connect",
            message="NetworkManager Wi-Fi connection was not attempted.",
        )

        for attempt in range(1, self.retries + 1):
            logger.info("NetworkManager Wi-Fi connect attempt %s/%s ssid=%s", attempt, self.retries, ssid)

            status = self._nmcli_connect(ssid, password)
            status.attempts = attempt
            if not status.ok:
                last_status = status
                time.sleep(2)
                continue

            connectivity_status = self.test_connectivity()
            connectivity_status.attempts = attempt
            if connectivity_status.ok:
                return connectivity_status

            last_status = connectivity_status

        return WiFiStatus(
            ok=False,
            stage=last_status.stage,
            message=f"Wi-Fi connection failed after {self.retries} attempt(s): {last_status.message}",
            attempts=self.retries,
            details=last_status.details,
        )

    def _build_config(self, *, ssid: str, password: str) -> str:
        escaped_ssid = _escape_wpa_value(ssid)
        if password:
            escaped_password = _escape_wpa_value(password)
            key_line = f'    psk="{escaped_password}"'
        else:
            key_line = "    key_mgmt=NONE"

        return (
            "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
            "update_config=1\n"
            "country=US\n"
            "\n"
            "network={\n"
            f'    ssid="{escaped_ssid}"\n'
            f"{key_line}\n"
            "}\n"
        )

    def _run(self, command: list[str], timeout: int) -> subprocess.CompletedProcess:
        return self.runner(command, timeout)

    def _scan_with_nmcli(self) -> WiFiStatus:
        result = self._run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
            timeout=20,
        )
        if result.returncode != 0:
            return WiFiStatus(
                ok=False,
                stage="wifi_scan",
                message="nmcli scan failed.",
                details={"command": "nmcli", "stderr": result.stderr},
            )

        networks = []
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if not parts or not parts[0].strip():
                continue
            ssid = parts[0].strip()
            signal = _parse_int(parts[1]) if len(parts) > 1 else None
            security = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
            networks.append(WiFiNetwork(ssid=ssid, signal=signal, security=security))

        return _network_status(networks, source="nmcli")

    def _nmcli_connect(self, ssid: str, password: str) -> WiFiStatus:
        if not ssid.strip():
            return WiFiStatus(
                ok=False,
                stage="networkmanager_connect",
                message="Wi-Fi SSID is required.",
            )

        if self.dry_run:
            logger.info("[dry-run] would connect with NetworkManager to ssid=%s", ssid)
            return WiFiStatus(
                ok=True,
                stage="networkmanager_connect",
                message="Dry-run NetworkManager Wi-Fi connect succeeded.",
            )

        command = ["sudo", "nmcli", "dev", "wifi", "connect", ssid]
        if password:
            command.extend(["password", password])

        result = self._run(command, timeout=60)
        if result.returncode != 0:
            return WiFiStatus(
                ok=False,
                stage="networkmanager_connect",
                message="NetworkManager could not connect to Wi-Fi.",
                details={"stderr": result.stderr, "stdout": result.stdout},
            )

        return WiFiStatus(
            ok=True,
            stage="networkmanager_connect",
            message="NetworkManager connected to Wi-Fi.",
        )


    def _scan_with_iwlist(self) -> WiFiStatus:
        result = self._run(["sudo", "iwlist", "wlan0", "scan"], timeout=30)
        if result.returncode != 0:
            return WiFiStatus(
                ok=False,
                stage="wifi_scan",
                message="iwlist scan failed.",
                details={"command": "iwlist", "stderr": result.stderr},
            )

        networks = []
        current_ssid = None
        current_signal = None
        current_security = None

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if line.startswith("Cell "):
                if current_ssid:
                    networks.append(
                        WiFiNetwork(
                            ssid=current_ssid,
                            signal=current_signal,
                            security=current_security,
                        )
                    )
                current_ssid = None
                current_signal = None
                current_security = None
            elif "ESSID:" in line:
                current_ssid = line.split("ESSID:", 1)[1].strip().strip('"')
            elif "Quality=" in line:
                current_signal = _parse_quality(line)
            elif "Encryption key:" in line:
                current_security = "secured" if "on" in line.lower() else "open"

        if current_ssid:
            networks.append(
                WiFiNetwork(
                    ssid=current_ssid,
                    signal=current_signal,
                    security=current_security,
                )
            )

        return _network_status(networks, source="iwlist")

    @staticmethod
    def _default_runner(command: list[str], timeout: int) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                args=command,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "command timed out",
            )


def _escape_wpa_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _parse_quality(line: str) -> int | None:
    try:
        quality = line.split("Quality=", 1)[1].split(" ", 1)[0]
        numerator, denominator = quality.split("/", 1)
        return round((int(numerator) / int(denominator)) * 100)
    except (IndexError, ValueError, ZeroDivisionError):
        return None


def _network_status(networks: list[WiFiNetwork], source: str) -> WiFiStatus:
    unique = {}
    for network in networks:
        if not network.ssid:
            continue
        existing = unique.get(network.ssid)
        if existing is None or (network.signal or 0) > (existing.signal or 0):
            unique[network.ssid] = network

    sorted_networks = sorted(
        unique.values(),
        key=lambda network: network.signal if network.signal is not None else -1,
        reverse=True,
    )

    return WiFiStatus(
        ok=True,
        stage="wifi_scan",
        message=f"Found {len(sorted_networks)} Wi-Fi network(s).",
        details={
            "source": source,
            "networks": [
                {
                    "ssid": network.ssid,
                    "signal": network.signal,
                    "security": network.security,
                }
                for network in sorted_networks
            ],
        },
    )
