"""Atividade API router."""

import sqlite3

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from ..models import atividade
from ..models.activity_catalog import (
    delete_activity_owner,
    delete_activity_status,
    insert_activity_owner,
    insert_activity_status,
    list_activity_owners,
    list_activity_statuses,
    update_activity_owner,
    update_activity_status,
)
from ..schemas import atividade as schema

router = APIRouter(prefix="/atividade", tags=["atividade"])


@router.get("/catalogos")
async def list_catalogos():
    """List predefined activity owners and statuses."""
    return {
        "owners": list_activity_owners(),
        "statuses": list_activity_statuses(),
    }


@router.post("/catalogos/owners")
async def create_catalog_owner(data: schema.ActivityOwnerCreate):
    try:
        owner_id = insert_activity_owner(data.name.strip(), data.sort_order, data.is_active)
        return {"status": "created", "id": owner_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar responsável: {exc}") from exc


@router.put("/catalogos/owners/{owner_id}")
async def edit_catalog_owner(owner_id: int, data: schema.ActivityOwnerUpdate):
    success = update_activity_owner(owner_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    return {"status": "updated"}


@router.delete("/catalogos/owners/{owner_id}")
async def remove_catalog_owner(owner_id: int):
    success = delete_activity_owner(owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    return {"status": "deleted"}


@router.post("/catalogos/statuses")
async def create_catalog_status(data: schema.ActivityStatusCreate):
    try:
        status_id = insert_activity_status(
            data.key.strip(),
            data.label.strip(),
            (data.hint or "").strip(),
            data.sort_order,
            data.is_active,
        )
        return {"status": "created", "id": status_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar status: {exc}") from exc


@router.put("/catalogos/statuses/{status_id}")
async def edit_catalog_status(status_id: int, data: schema.ActivityStatusUpdate):
    success = update_activity_status(status_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    return {"status": "updated"}


@router.delete("/catalogos/statuses/{status_id}")
async def remove_catalog_status(status_id: int):
    success = delete_activity_status(status_id)
    if not success:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    return {"status": "deleted"}


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
