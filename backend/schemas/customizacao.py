"""Customização Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class CustomizacaoBase(BaseModel):
    stage: Optional[str] = None
    proposal: Optional[str] = None
    subject: Optional[str] = None
    client: Optional[str] = None
    module: Optional[str] = None
    module_id: Optional[int] = None
    owner: Optional[str] = None
    received_at: Optional[str] = None
    status: Optional[str] = None
    pf: Optional[float] = None
    value: Optional[float] = None
    observations: Optional[str] = None
    pdf_path: Optional[str] = None
    client_id: Optional[int] = None


class CustomizacaoCreate(CustomizacaoBase):
    pass


class CustomizacaoUpdate(BaseModel):
    stage: Optional[str] = None
    proposal: Optional[str] = None
    subject: Optional[str] = None
    client: Optional[str] = None
    module: Optional[str] = None
    module_id: Optional[int] = None
    owner: Optional[str] = None
    received_at: Optional[str] = None
    status: Optional[str] = None
    pf: Optional[float] = None
    value: Optional[float] = None
    observations: Optional[str] = None
    pdf_path: Optional[str] = None
    client_id: Optional[int] = None