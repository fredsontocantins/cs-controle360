"""Atividade API router."""

import sqlite3

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from ..models import atividade
from ..schemas import atividade as schema

router = APIRouter(prefix="/atividade", tags=["atividade"])


@router.get("", response_model=List[dict])
async def list_atividades(release_id: Optional[int] = None):
    """List all activities, optionally filtered by release."""
    if release_id:
        return atividade.list_by_release(release_id)
    return atividade.list_atividade()


@router.get("/{entity_id}", response_model=dict)
async def get_atividade(entity_id: int):
    """Get a single activity by ID."""
    result = atividade.get_atividade(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return result


@router.post("", response_model=dict)
async def create_atividade(data: schema.AtividadeCreate):
    """Create a new activity."""
    try:
        entity_id = atividade.insert_atividade(data.model_dump())
        return atividade.get_atividade(entity_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar atividade: {exc}") from exc


@router.put("/{entity_id}", response_model=dict)
async def update_atividade(entity_id: int, data: schema.AtividadeUpdate):
    """Update an existing activity."""
    try:
        success = atividade.update_atividade(entity_id, data.model_dump(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        return atividade.get_atividade(entity_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao atualizar atividade: {exc}") from exc


@router.patch("/{entity_id}/status", response_model=dict)
async def update_atividade_status(entity_id: int, status: str):
    """Update only the status of an activity."""
    success = atividade.update_atividade(entity_id, {"status": status})
    if not success:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return atividade.get_atividade(entity_id)


@router.delete("/{entity_id}")
async def delete_atividade(entity_id: int):
    """Delete an activity."""
    success = atividade.delete_atividade(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return {"status": "deleted"}
