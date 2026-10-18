from typing import Literal

from pydantic import BaseModel


class LiveStatus(BaseModel):
    status: Literal["ok"]


class ReadyStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unavailable"]
    migrations: Literal["ok", "pending", "unknown"]
