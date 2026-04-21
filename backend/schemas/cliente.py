"""Cliente Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    name: Optional[str] = None
    segment: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    name: Optional[str] = None
    segment: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None