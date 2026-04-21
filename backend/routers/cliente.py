"""Cliente API router."""

from fastapi import APIRouter, HTTPException
from typing import List

from ..models import cliente
from ..schemas import cliente as schema

router = APIRouter(prefix="/cliente", tags=["cliente"])


@router.get("", response_model=List[dict])
async def list_clientes():
    """List all clients."""
    return cliente.list_cliente()


@router.get("/{entity_id}", response_model=dict)
async def get_cliente(entity_id: int):
    """Get a single client by ID."""
    result = cliente.get_cliente(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return result


@router.post("", response_model=dict)
async def create_cliente(data: schema.ClienteCreate):
    """Create a new client."""
    entity_id = cliente.insert_cliente(data.model_dump())
    return cliente.get_cliente(entity_id)


@router.put("/{entity_id}", response_model=dict)
async def update_cliente(entity_id: int, data: schema.ClienteUpdate):
    """Update an existing client."""
    success = cliente.update_cliente(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente.get_cliente(entity_id)


@router.delete("/{entity_id}")
async def delete_cliente(entity_id: int):
    """Delete a client."""
    success = cliente.delete_cliente(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"status": "deleted"}