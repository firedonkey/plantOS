from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from .simulator_camera import SimulatedCameraNode
from .simulator_config import SimulatorConfig, SimulatorNodeConfig
from .simulator_device import SimulatedDeviceNode
from .simulator_events import SimulatorApiClient
from .simulator_master import SimulatedMasterNode


logger = logging.getLogger(__name__)


class SimulatorRuntime:
    def __init__(self, config: SimulatorConfig, *, api: SimulatorApiClient | None = None) -> None:
        self.config = config
        self.api = api or SimulatorApiClient(config.base_url)
        self.nodes = [self._build_node(node_config) for node_config in config.nodes]

    async def run(self) -> None:
        logger.info("Starting PlantLab simulator nodes=%s base_url=%s", len(self.nodes), self.config.base_url)
        for node in self.nodes:
            await node.register_node()

        stop_at = time.monotonic() + self.config.run_seconds if self.config.run_seconds else None
        tasks = [asyncio.create_task(self._run_node(node, stop_at)) for node in self.nodes]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def run_once(self) -> None:
        for node in self.nodes:
            await node.register_node()
            await node.send_heartbeat()
            await node.send_sensor_reading()
            await node.send_diagnostics()
            await node.upload_fake_image()
            await node.poll_commands()

    async def _run_node(self, node: SimulatedDeviceNode, stop_at: float | None) -> None:
        last_heartbeat = 0.0
        last_reading = 0.0
        last_image = 0.0
        last_diagnostics = 0.0
        last_poll = 0.0
        while stop_at is None or time.monotonic() < stop_at:
            now = time.monotonic()
            if now - last_heartbeat >= node.config.heartbeat_interval_seconds:
                await node.send_heartbeat()
                last_heartbeat = now
            if now - last_reading >= node.config.sensor_interval_seconds:
                await node.send_sensor_reading()
                last_reading = now
            if now - last_image >= node.config.image_interval_seconds:
                await node.upload_fake_image()
                last_image = now
            if now - last_diagnostics >= node.config.diagnostics_interval_seconds:
                await node.send_diagnostics()
                last_diagnostics = now
            if now - last_poll >= node.config.command_poll_interval_seconds:
                await node.poll_commands()
                last_poll = now
            await asyncio.sleep(0.25)

    def _build_node(self, config: SimulatorNodeConfig) -> SimulatedDeviceNode:
        if config.node_role == "camera":
            return SimulatedCameraNode(config, self.api)
        return SimulatedMasterNode(config, self.api)
