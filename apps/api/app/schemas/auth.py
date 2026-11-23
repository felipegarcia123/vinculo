from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class SessionOut(BaseModel):
    id: str
    name: str
    username: str
    role: Literal["owner", "cashier", "customer"]
    expires_at: datetime | None = None
