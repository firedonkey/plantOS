from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from tools.simulator.scenarios import describe_scenarios
    from tools.simulator.simulator_events import SimulatorApiError
    from tools.simulator.simulator_config import load_config_from_args, parse_args
    from tools.simulator.simulator_runtime import SimulatorRuntime
else:
    from .scenarios import describe_scenarios
    from .simulator_events import SimulatorApiError
    from .simulator_config import load_config_from_args, parse_args
    from .simulator_runtime import SimulatorRuntime


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[simulator] %(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.scenario == ["help"]:
        print(describe_scenarios())
        return 0
    try:
        config = load_config_from_args(args)
        if not config.nodes:
            raise SystemExit("No simulator nodes configured.")
        asyncio.run(SimulatorRuntime(config).run())
    except SimulatorApiError as exc:
        print(_friendly_api_error(exc), file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Simulator configuration error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Simulator stopped.", file=sys.stderr)
        return 130
    return 0


def _friendly_api_error(error: SimulatorApiError) -> str:
    if error.status == 401:
        return (
            "Simulator authentication failed.\n"
            "- Use the device api_token, not a web login token or setup code.\n"
            "- Confirm --device-id matches that token's device row.\n"
            "- For local Docker, run: docker exec -it plantlab-local-postgres "
            "psql -U plantlab_user -d plantlab -c \"select id, name, api_token from devices order by id;\""
        )
    if error.status == 403:
        return "Simulator request was forbidden. Check that --device-id matches the device API token."
    if error.status == 404:
        return f"Simulator backend object was not found while calling {error.path}. Check device id and registered hardware node ids."
    if error.status == 422:
        return f"Simulator request was rejected by backend validation while calling {error.path}: {error.message}"
    if error.status is None:
        return (
            f"Could not reach the PlantLab backend while calling {error.path}: {error.message}\n"
            "Start the local Docker backend first: docker compose -f platform/infra/docker/docker-compose.local.yml up --build"
        )
    return str(error)


if __name__ == "__main__":
    raise SystemExit(main())
