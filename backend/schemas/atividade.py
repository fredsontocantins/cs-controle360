"""Atividade Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class AtividadeBase(BaseModel):
    title: Optional[str] = None
    release_id: Optional[int] = None
    owner: Optional[str] = None
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
    tipo: Optional[str] = None
    ticket: Optional[str] = None
    descricao_erro: Optional[str] = None
    resolucao: Optional[str] = None
    status: Optional[str] = None
