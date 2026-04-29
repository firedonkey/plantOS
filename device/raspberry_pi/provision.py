import argparse
import logging
import os

from config import load_config
from provisioning.service import ProvisioningService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PlantLab Raspberry Pi SoftAP provisioning.")
    parser.add_argument("--config", default="config.gcp.yaml", help="Path to device YAML config.")
    parser.add_argument("--state-file", help="Provisioning JSON config path.")
    parser.add_argument("--backend-url", help="PlantLab backend URL.")
    parser.add_argument("--host", default="0.0.0.0", help="Local setup web server host.")
    parser.add_argument("--port", type=int, default=8080, help="Local setup web server port.")
    parser.add_argument("--real-network", action="store_true", help="Run real network commands instead of dry-run stubs.")
    parser.add_argument("--open-hotspot", action="store_true", help="Create the setup hotspot without a Wi-Fi password.")
    parser.add_argument("--reset", action="store_true", help="Delete local provisioning state before starting.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    provisioning_config = config.get("provisioning", {})
    hotspot_open = args.open_hotspot or bool(provisioning_config.get("open_hotspot", False))
    if hotspot_open:
        hotspot_password = ""
    elif "hotspot_password" in provisioning_config:
        hotspot_password = str(provisioning_config.get("hotspot_password") or "")
    else:
        hotspot_password = "plantlabsetup"
    backend_url = (
        args.backend_url
        or os.getenv("PLANTLAB_BACKEND_URL")
        or provisioning_config.get("backend_url")
        or config.get("platform", {}).get("url")
        or "https://marspotatolab.com"
    )
    state_file = args.state_file or provisioning_config.get("state_file") or "data/provisioning/device_config.json"
    dry_run = not args.real_network and bool(provisioning_config.get("network_dry_run", True))

    service = ProvisioningService(
        backend_url=backend_url,
        platform_url=provisioning_config.get("platform_url") or config.get("platform", {}).get("url"),
        state_file=state_file,
        host=args.host,
        port=args.port,
        dry_run=dry_run,
        hardware_version=str(provisioning_config.get("hardware_version") or "raspberry_pi_3"),
        software_version=str(provisioning_config.get("software_version") or "0.1.0"),
        capabilities=provisioning_config.get("capabilities") or {},
        hotspot_password=hotspot_password,
    )

    if args.reset:
        service.factory_reset()

    service.run()


if __name__ == "__main__":
    main()
