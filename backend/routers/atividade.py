"""Atividade API router — fully independent module."""

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
from ..response import ok, ok_list, ok_deleted

MODULE = "atividade"
router = APIRouter(prefix="/atividade", tags=["atividade"])


@router.get("/stats")
async def get_stats():
    items = atividade.list_atividade()
    total = len(items)
    by_tipo: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_owner: dict[str, int] = {}
    for item in items:
        t = item.get("tipo") or "sem_tipo"
        by_tipo[t] = by_tipo.get(t, 0) + 1
        s = item.get("status") or "sem_status"
        by_status[s] = by_status.get(s, 0) + 1
        o = item.get("owner") or item.get("executor") or "sem_responsavel"
        by_owner[o] = by_owner.get(o, 0) + 1
    return ok(
        {"total": total, "by_tipo": by_tipo, "by_status": by_status, "by_owner": by_owner},
        module=MODULE,
    )


@router.get("/catalogos")
async def list_catalogos():
    return ok(
        {"owners": list_activity_owners(), "statuses": list_activity_statuses()},
        module=MODULE,
    )


@router.post("/catalogos/owners")
async def create_catalog_owner(data: schema.ActivityOwnerCreate):
    try:
        owner_id = insert_activity_owner(data.name.strip(), data.sort_order, data.is_active)
        return ok({"id": owner_id}, module=MODULE, meta={"action": "created"})
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar responsável: {exc}") from exc


@router.put("/catalogos/owners/{owner_id}")
async def edit_catalog_owner(owner_id: int, data: schema.ActivityOwnerUpdate):
    success = update_activity_owner(owner_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    return ok(None, module=MODULE, meta={"action": "updated"})


@router.delete("/catalogos/owners/{owner_id}")
async def remove_catalog_owner(owner_id: int):
    success = delete_activity_owner(owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    return ok_deleted(module=MODULE)


@router.post("/catalogos/statuses")
async def create_catalog_status(data: schema.ActivityStatusCreate):
    try:
        status_id = insert_activity_status(
            data.key.strip(), data.label.strip(), (data.hint or "").strip(),
            data.sort_order, data.is_active,
        )
        return ok({"id": status_id}, module=MODULE, meta={"action": "created"})
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar status: {exc}") from exc


@router.put("/catalogos/statuses/{status_id}")
async def edit_catalog_status(status_id: int, data: schema.ActivityStatusUpdate):
    success = update_activity_status(status_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    return ok(None, module=MODULE, meta={"action": "updated"})


@router.delete("/catalogos/statuses/{status_id}")
async def remove_catalog_status(status_id: int):
    success = delete_activity_status(status_id)
    if not success:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    return ok_deleted(module=MODULE)


@router.get("")
async def list_atividades(release_id: Optional[int] = None):
    if release_id:
        return ok_list(atividade.list_by_release(release_id), module=MODULE)
    return ok_list(atividade.list_atividade(), module=MODULE)


@router.get("/{entity_id}")
async def get_atividade(entity_id: int):
    result = atividade.get_atividade(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return ok(result, module=MODULE)


@router.post("")
async def create_atividade(data: schema.AtividadeCreate):
    try:
        entity_id = atividade.insert_atividade(data.model_dump())
        return ok(atividade.get_atividade(entity_id), module=MODULE, meta={"action": "created"})
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao salvar atividade: {exc}") from exc


@router.put("/{entity_id}")
async def update_atividade(entity_id: int, data: schema.AtividadeUpdate):
    try:
        success = atividade.update_atividade(entity_id, data.model_dump(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        return ok(atividade.get_atividade(entity_id), module=MODULE, meta={"action": "updated"})
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao atualizar atividade: {exc}") from exc


@router.patch("/{entity_id}/status")
async def update_atividade_status(entity_id: int, status: str):
    success = atividade.update_atividade(entity_id, {"status": status})
    if not success:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return ok(atividade.get_atividade(entity_id), module=MODULE, meta={"action": "status_updated"})


@router.delete("/{entity_id}")
async def delete_atividade(entity_id: int):
    success = atividade.delete_atividade(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return ok_deleted(module=MODULE)
