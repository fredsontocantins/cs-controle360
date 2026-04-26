"""Módulo API router — fully independent module."""

from fastapi import APIRouter, HTTPException
from typing import List

from ..models import modulo
from ..schemas import modulo as schema
from ..response import ok, ok_list, ok_deleted

MODULE = "modulo"
router = APIRouter(prefix="/modulo", tags=["modulo"])


@router.get("/stats")
async def get_stats():
    items = modulo.list_modulo()
    total = len(items)
    by_owner: dict[str, int] = {}
    for item in items:
        o = item.get("owner") or "sem_responsavel"
        by_owner[o] = by_owner.get(o, 0) + 1
    return ok({"total": total, "by_owner": by_owner}, module=MODULE)


@router.get("")
async def list_modulos():
    return ok_list(modulo.list_modulo(), module=MODULE)


@router.get("/{entity_id}")
async def get_modulo(entity_id: int):
    result = modulo.get_modulo(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return ok(result, module=MODULE)


@router.post("")
async def create_modulo(data: schema.ModuloCreate):
    entity_id = modulo.insert_modulo(data.model_dump())
    return ok(modulo.get_modulo(entity_id), module=MODULE, meta={"action": "created"})


@router.put("/{entity_id}")
async def update_modulo(entity_id: int, data: schema.ModuloUpdate):
    success = modulo.update_modulo(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return ok(modulo.get_modulo(entity_id), module=MODULE, meta={"action": "updated"})


@router.delete("/{entity_id}")
async def delete_modulo(entity_id: int):
    success = modulo.delete_modulo(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")
    return ok_deleted(module=MODULE)
