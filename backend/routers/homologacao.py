"""Homologação API router."""

from fastapi import APIRouter, HTTPException, status
from typing import List

from ..models import homologacao
from ..schemas import homologacao as schema
from ..exceptions import EntityNotFoundError, DatabaseOperationError

router = APIRouter(prefix="/homologacao", tags=["homologacao"])


@router.get("", response_model=List[dict])
async def list_homologacoes():
    """List all homologations."""
    try:
        return homologacao.list_homologacao()
    except DatabaseOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{entity_id}", response_model=dict)
async def get_homologacao(entity_id: int):
    """Get a single homologation by ID."""
    try:
        result = homologacao.get_homologacao(entity_id)
        if not result:
            raise HTTPException(status_code=404, detail="Homologação não encontrada")
        return result
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_homologacao(data: schema.HomologacaoCreate):
    """Create a new homologation."""
    try:
        entity_id = homologacao.insert_homologacao(data.model_dump())
        return homologacao.get_homologacao(entity_id)
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entity_id}", response_model=dict)
async def update_homologacao(entity_id: int, data: schema.HomologacaoUpdate):
    """Update an existing homologation."""
    try:
        success = homologacao.update_homologacao(entity_id, data.model_dump(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Homologação não encontrada ou sem alterações")
        return homologacao.get_homologacao(entity_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homologacao(entity_id: int):
    """Delete a homologation."""
    try:
        success = homologacao.delete_homologacao(entity_id)
        if not success:
            raise HTTPException(status_code=404, detail="Homologação não encontrada")
        return None
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
