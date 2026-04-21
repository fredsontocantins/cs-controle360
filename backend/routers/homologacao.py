"""Homologação API router."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from ..models import homologacao
from ..schemas import homologacao as schema

router = APIRouter(prefix="/homologacao", tags=["homologacao"])


@router.get("", response_model=List[dict])
async def list_homologacoes():
    """List all homologations."""
    return homologacao.list_homologacao()


@router.get("/{entity_id}", response_model=dict)
async def get_homologacao(entity_id: int):
    """Get a single homologation by ID."""
    result = homologacao.get_homologacao(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return result


@router.post("", response_model=dict)
async def create_homologacao(data: schema.HomologacaoCreate):
    """Create a new homologation."""
    entity_id = homologacao.insert_homologacao(data.model_dump())
    return homologacao.get_homologacao(entity_id)


@router.put("/{entity_id}", response_model=dict)
async def update_homologacao(entity_id: int, data: schema.HomologacaoUpdate):
    """Update an existing homologation."""
    success = homologacao.update_homologacao(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return homologacao.get_homologacao(entity_id)


@router.delete("/{entity_id}")
async def delete_homologacao(entity_id: int):
    """Delete a homologation."""
    success = homologacao.delete_homologacao(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return {"status": "deleted"}