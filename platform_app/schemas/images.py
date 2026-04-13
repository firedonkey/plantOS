from datetime import datetime

from pydantic import BaseModel


class ImageRead(BaseModel):
    id: int
    device_id: int
    path: str
    timestamp: datetime

    model_config = {"from_attributes": True}
