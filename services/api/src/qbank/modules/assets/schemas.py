from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AssetOut(BaseModel):
    """A stored picture. Its bytes are read from ``/api/v1/assets/{id}/content``."""

    id: UUID
    kind: Literal["IMAGE"]
    content_type: Literal["image/png", "image/jpeg", "image/webp"]
    width: int = Field(description="Pixels, after the picture was cleaned and re-encoded")
    height: int
    byte_size: int
    created_at: datetime
