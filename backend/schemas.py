"""Pydantic schemas for the CS control API."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class HomologationBase(BaseModel):
    module: str = Field(..., example="Catálogo")
    status: Optional[str] = Field(None, example="Em Andamento")
    check_date: Optional[str] = Field(None, example="2026-03-26")
    observation: Optional[str] = None
    latest_version: Optional[str] = Field(None, example="3.45.0")
    homologation_version: Optional[str] = Field(None, example="3.45.0")
    production_version: Optional[str] = Field(None, example="3.17.0")
    homologated: Optional[str] = Field(None, example="Não")
    client_presentation: Optional[str] = None
    applied: Optional[str] = Field(None, example="Pendente")
    monthly_versions: Dict[str, str] = {}
    requested_production_date: Optional[str] = Field(
        None, example="2026-04-01", description="Data solicitada para subir em produção"
    )
    production_date: Optional[str] = Field(
        None, example="2026-04-05", description="Data em que efetivamente subiu em produção"
    )


class HomologationCreate(HomologationBase):
    pass


class HomologationUpdate(BaseModel):
    module: Optional[str]
    status: Optional[str]
    check_date: Optional[str]
    observation: Optional[str]
    latest_version: Optional[str]
    homologation_version: Optional[str]
    production_version: Optional[str]
    homologated: Optional[str]
    client_presentation: Optional[str]
    applied: Optional[str]
    monthly_versions: Optional[Dict[str, str]]


class CustomizationBase(BaseModel):
    stage: str = Field(..., example="em_elaboracao")
    proposal: str = Field(..., example="008/2025")
    subject: Optional[str] = None
    client: Optional[str] = None
    module: Optional[str] = None
    owner: Optional[str] = None
    received_at: Optional[str] = Field(None, example="2025-09-09")
    status: Optional[str] = None
    pf: Optional[float] = None
    value: Optional[float] = None
    observations: Optional[str]
    pdf_path: Optional[str] = None


class ReleaseBase(BaseModel):
    module: str = Field(..., example="Catálogo")
    release_name: str = Field(..., example="Release 3.45")
    version: Optional[str] = Field(None, example="3.45.0")
    applies_on: Optional[str] = Field(None, example="2026-04-15")
    notes: Optional[str] = Field(None, example="Novas validações do fluxo X.")
    pdf_path: Optional[str] = None
    created_at: Optional[str] = None


class ReleaseCreate(ReleaseBase):
    pass


class ReleaseUpdate(BaseModel):
    module: Optional[str]
    release_name: Optional[str]
    version: Optional[str]
    applies_on: Optional[str]
    notes: Optional[str]
    pdf_path: Optional[str]


class ClientBase(BaseModel):
    name: str = Field(..., example="ACME Corp")
    segment: Optional[str] = Field(None, example="Varejo")
    owner: Optional[str] = Field(None, example="Equipe CS")
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str]
    segment: Optional[str]
    owner: Optional[str]
    notes: Optional[str]


class CustomizationCreate(CustomizationBase):
    pass


class CustomizationUpdate(BaseModel):
    stage: Optional[str]
    proposal: Optional[str]
    subject: Optional[str]
    client: Optional[str]
    module: Optional[str]
    owner: Optional[str]
    received_at: Optional[str]
    status: Optional[str]
    pf: Optional[float]
    value: Optional[float]
    observations: Optional[str]
    pdf_path: Optional[str]


class ModuleBase(BaseModel):
    name: str = Field(..., example="Catálogo")
    description: Optional[str] = None
    owner: Optional[str] = None


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    owner: Optional[str]
