import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .state import ProvisioningState


class ProvisioningStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "provisioning_state": ProvisioningState.FACTORY_RESET.value,
            }

        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f"{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            json.dump(data, file, indent=2, sort_keys=True)
            file.write("\n")
            temp_path = Path(file.name)

        os.chmod(temp_path, 0o600)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, self.path)

    def update(self, **changes) -> dict[str, Any]:
        data = self.load()
        data.update(changes)
        self.save(data)
        return data

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def is_provisioned(self) -> bool:
        data = self.load()
        return bool(
            data.get("device_id")
            and data.get("backend_url")
            and data.get("device_access_token")
            and data.get("provisioning_state") == ProvisioningState.ONLINE.value
        )
