"""Homologação Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class HomologacaoBase(BaseModel):
    module: Optional[str] = None
    module_id: Optional[int] = None
    status: Optional[str] = None
    check_date: Optional[str] = None
    observation: Optional[str] = None
    latest_version: Optional[str] = None
    homologation_version: Optional[str] = None
    production_version: Optional[str] = None
    homologated: Optional[str] = None
    client_presentation: Optional[str] = None
    applied: Optional[str] = None
    monthly_versions: Optional[Dict[str, Any]] = None
    requested_production_date: Optional[str] = None
    production_date: Optional[str] = None
    client: Optional[str] = None
    client_id: Optional[int] = None


class HomologacaoCreate(HomologacaoBase):
    pass


class HomologacaoUpdate(BaseModel):
    module: Optional[str] = None
    module_id: Optional[int] = None
    status: Optional[str] = None
    check_date: Optional[str] = None
    observation: Optional[str] = None
    latest_version: Optional[str] = None
    homologation_version: Optional[str] = None
    production_version: Optional[str] = None
    homologated: Optional[str] = None
    client_presentation: Optional[str] = None
    applied: Optional[str] = None
    monthly_versions: Optional[Dict[str, Any]] = None
    requested_production_date: Optional[str] = None
    production_date: Optional[str] = None
    client: Optional[str] = None
    client_id: Optional[int] = None