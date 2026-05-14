from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


RPI_ROOT = Path(__file__).resolve().parent
CANONICAL_PROVISIONING_API_URL = "https://plantlab-provision-api-418533861080.us-central1.run.app"
PLATFORM_URL = "https://marspotatolab.com"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _install_gpio_stub(monkeypatch) -> None:
    gpio = types.ModuleType("RPi.GPIO")
    gpio.BCM = "BCM"
    gpio.BOTH = "BOTH"
    gpio.HIGH = 1
    gpio.IN = "IN"
    gpio.LOW = 0
    gpio.OUT = "OUT"
    gpio.PUD_UP = "PUD_UP"
    gpio.add_event_detect = lambda *args, **kwargs: None
    gpio.cleanup = lambda *args, **kwargs: None
    gpio.input = lambda *args, **kwargs: gpio.HIGH
    gpio.output = lambda *args, **kwargs: None
    gpio.remove_event_detect = lambda *args, **kwargs: None
    gpio.setmode = lambda *args, **kwargs: None
    gpio.setup = lambda *args, **kwargs: None
    gpio.setwarnings = lambda *args, **kwargs: None

    rpi = types.ModuleType("RPi")
    rpi.GPIO = gpio
    monkeypatch.setitem(sys.modules, "RPi", rpi)
    monkeypatch.setitem(sys.modules, "RPi.GPIO", gpio)


def test_gcp_config_separates_platform_and_provisioning_urls(monkeypatch):
    monkeypatch.syspath_prepend(str(RPI_ROOT))
    from config import load_config

    config = load_config(RPI_ROOT / "config.gcp.yaml")

    assert config["platform"]["url"] == PLATFORM_URL
    assert config["provisioning"]["backend_url"] == CANONICAL_PROVISIONING_API_URL
    assert config["provisioning"]["backend_url"] != config["platform"]["url"]


def test_provision_entrypoint_defaults_to_provisioning_api(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(RPI_ROOT))
    monkeypatch.delenv("PLANTLAB_PROVISIONING_API_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_BACKEND_URL", raising=False)

    module = _load_module("plantlab_test_provision_entrypoint", RPI_ROOT / "provision.py")
    captured_kwargs = {}

    class FakeProvisioningService:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def run(self):
            captured_kwargs["ran"] = True

    monkeypatch.setattr(module, "ProvisioningService", FakeProvisioningService)
    monkeypatch.setattr(
        module,
        "load_config",
        lambda path: {
            "platform": {"url": PLATFORM_URL},
            "provisioning": {
                "state_file": str(tmp_path / "device_config.json"),
                "network_dry_run": True,
            },
        },
    )
    monkeypatch.setattr(sys, "argv", ["provision.py", "--config", str(tmp_path / "config.yaml")])

    module.main()

    assert captured_kwargs["backend_url"] == CANONICAL_PROVISIONING_API_URL
    assert captured_kwargs["platform_url"] == PLATFORM_URL
    assert captured_kwargs["ran"] is True


def test_button_controller_defaults_to_provisioning_api(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(RPI_ROOT))
    _install_gpio_stub(monkeypatch)

    module = _load_module(
        "plantlab_test_run_provisioning_service",
        RPI_ROOT / "provisioning" / "run_provisioning_service.py",
    )
    captured_kwargs = {}

    class FakeStore:
        def is_provisioned(self) -> bool:
            return False

    class FakeProvisioningService:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self.store = FakeStore()

    class FakeLedController:
        def __init__(self, pin):
            self.pin = pin

        def set_state(self, state):
            self.state = state

    class FakeButtonHandler:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakePlatformRuntime:
        def __init__(self, config, *, provisioning_state_file):
            self.config = config
            self.provisioning_state_file = provisioning_state_file

        def stop(self):
            pass

    monkeypatch.setattr(module, "ProvisioningService", FakeProvisioningService)
    monkeypatch.setattr(module, "LedController", FakeLedController)
    monkeypatch.setattr(module, "ButtonHandler", FakeButtonHandler)
    monkeypatch.setattr(module, "PlatformRuntime", FakePlatformRuntime)
    monkeypatch.setattr(
        module,
        "load_config",
        lambda path: {
            "platform": {"url": PLATFORM_URL},
            "provisioning": {
                "state_file": str(tmp_path / "device_config.json"),
                "network_dry_run": True,
            },
        },
    )

    module.ProvisioningController(config_path=str(tmp_path / "config.yaml"))

    assert captured_kwargs["backend_url"] == CANONICAL_PROVISIONING_API_URL
    assert captured_kwargs["platform_url"] == PLATFORM_URL


def test_provisioning_docs_do_not_use_platform_url_as_backend_url():
    docs_to_check = [
        RPI_ROOT / "provisioning" / "README.md",
        RPI_ROOT.parents[1] / "docs" / "design" / "provisioning_v1_implementation.md",
    ]

    for path in docs_to_check:
        text = path.read_text(encoding="utf-8")
        assert "backend_url: https://marspotatolab.com" not in text
        assert "--backend-url https://marspotatolab.com" not in text
