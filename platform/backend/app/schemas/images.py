from datetime import datetime

from pydantic import BaseModel

from app.contracts import CameraRole


class ImageRead(BaseModel):
    id: int
    device_id: int
    source_hardware_device_id: str | None = None
    camera_role: CameraRole | None = None
    path: str
    timestamp: datetime

    model_config = {"from_attributes": True}
