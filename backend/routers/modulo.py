"""Módulo API router."""

from fastapi import APIRouter, HTTPException
from typing import List

from ..models import modulo
from ..schemas import modulo as schema

router = APIRouter(prefix="/modulo", tags=["modulo"])


@router.get("", response_model=List[dict])
async def list_modulos():
    """List all modules."""
    return modulo.list_modulo()


@router.get("/{entity_id}", response_model=dict)
async def get_modulo(entity_id: int):
    """Get a single module by ID."""
    result = modulo.get_modulo(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return result


@router.post("", response_model=dict)
async def create_modulo(data: schema.ModuloCreate):
    """Create a new module."""
    entity_id = modulo.insert_modulo(data.model_dump())
    return modulo.get_modulo(entity_id)


@router.put("/{entity_id}", response_model=dict)
async def update_modulo(entity_id: int, data: schema.ModuloUpdate):
    """Update an existing module."""
    success = modulo.update_modulo(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return modulo.get_modulo(entity_id)


@router.delete("/{entity_id}")
async def delete_modulo(entity_id: int):
    """Delete a module."""
    success = modulo.delete_modulo(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return {"status": "deleted"}