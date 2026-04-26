import argparse

from actuators.pump import Pump
from config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the water pump relay for a short manual test.")
    parser.add_argument("--config", default="config.yaml", help="Path to device config YAML.")
    parser.add_argument("--seconds", type=int, help="Pump run time for this test.")
    args = parser.parse_args()

    config = load_config(args.config)
    hardware_mock = bool(config.get("hardware", {}).get("mock_mode", True))
    actuator_config = config.get("actuators", {})
    pump_config = actuator_config.get("pump", {})
    active_high = bool(actuator_config.get("relay_active_high", True))
    seconds = int(args.seconds or pump_config.get("run_seconds", 2))

    if seconds < 1 or seconds > 30:
        raise SystemExit("Use --seconds from 1 to 30 for a safe manual pump test.")

    pump = Pump(pump_config, active_high=active_high, mock_mode=hardware_mock)
    print(
        "Pump test: "
        f"mock_mode={hardware_mock}, "
        f"relay_active_high={active_high}, "
        f"gpio_pin={pump_config.get('gpio_pin')}, "
        f"seconds={seconds}"
    )

    try:
        pump.run_for(seconds)
        print("Pump test complete.")
    except Exception as exc:
        raise SystemExit(f"Pump test failed: {exc}") from exc
    finally:
        pump.close()


if __name__ == "__main__":
    main()
