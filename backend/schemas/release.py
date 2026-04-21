"""Release Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class ReleaseBase(BaseModel):
    module: Optional[str] = None
    module_id: Optional[int] = None
    release_name: Optional[str] = None
    version: Optional[str] = None
    applies_on: Optional[str] = None
    notes: Optional[str] = None
    client: Optional[str] = None
    pdf_path: Optional[str] = None
    client_id: Optional[int] = None
    created_at: Optional[str] = None


class ReleaseCreate(ReleaseBase):
    pass


class ReleaseUpdate(BaseModel):
    module: Optional[str] = None
    module_id: Optional[int] = None
    release_name: Optional[str] = None
    version: Optional[str] = None
    applies_on: Optional[str] = None
    notes: Optional[str] = None
    client: Optional[str] = None
    pdf_path: Optional[str] = None
    client_id: Optional[int] = None