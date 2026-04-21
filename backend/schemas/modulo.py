"""Módulo Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class ModuloBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[str] = None


class ModuloCreate(ModuloBase):
    pass


class ModuloUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None