from __future__ import annotations

from .simulator_device import SimulatedDeviceNode


class SimulatedMasterNode(SimulatedDeviceNode):
    """ESP32-S3 master node simulator.

    The master handles plant runtime state and can also act as the camera
    gateway, matching the current ESP-NOW product topology.
    """
