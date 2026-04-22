"""Atividade Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class AtividadeBase(BaseModel):
    title: Optional[str] = None
    release_id: Optional[int] = None
    owner: Optional[str] = None
    executor: Optional[str] = None
    tipo: Optional[str] = None  # nova_funcionalidade, correcao_bug, melhoria
    ticket: Optional[str] = None
    descricao_erro: Optional[str] = None
    resolucao: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AtividadeCreate(AtividadeBase):
    pass


class AtividadeUpdate(BaseModel):
    title: Optional[str] = None
    release_id: Optional[int] = None
    owner: Optional[str] = None
    executor: Optional[str] = None
    tipo: Optional[str] = None
    ticket: Optional[str] = None
    descricao_erro: Optional[str] = None
    resolucao: Optional[str] = None
    status: Optional[str] = None


class ActivityOwnerCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: int = 1


class ActivityOwnerUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None


class ActivityStatusCreate(BaseModel):
    key: str
    label: str
    hint: Optional[str] = ""
    sort_order: int = 0
    is_active: int = 1


class ActivityStatusUpdate(BaseModel):
    key: Optional[str] = None
    label: Optional[str] = None
    hint: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None
