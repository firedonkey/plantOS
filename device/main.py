import argparse

from config import load_config
from services.automation import PlantAutomation
from services.scheduler import run_forever


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the plantOS automation loop.")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--loop-interval", type=int, help="Override app.loop_interval_seconds.")
    parser.add_argument("--capture-interval", type=int, help="Override camera.capture_interval_seconds.")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.loop_interval is not None:
        config.setdefault("app", {})["loop_interval_seconds"] = args.loop_interval
    if args.capture_interval is not None:
        config.setdefault("camera", {})["capture_interval_seconds"] = args.capture_interval

    automation = PlantAutomation(config)
    try:
        if args.once:
            print(automation.run_once())
        else:
            interval = int(config.get("app", {}).get("loop_interval_seconds", 60))
            run_forever(automation, interval)
    finally:
        automation.close()


if __name__ == "__main__":
    main()
