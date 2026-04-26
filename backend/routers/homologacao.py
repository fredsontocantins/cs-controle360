"""Homologação API router — fully independent module."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from ..models import homologacao
from ..schemas import homologacao as schema
from ..response import ok, ok_list, ok_deleted

MODULE = "homologacao"
router = APIRouter(prefix="/homologacao", tags=["homologacao"])


@router.get("/stats")
async def get_stats():
    items = homologacao.list_homologacao()
    total = len(items)
    by_status: dict[str, int] = {}
    by_module: dict[str, int] = {}
    for item in items:
        s = item.get("status") or "sem_status"
        by_status[s] = by_status.get(s, 0) + 1
        m = item.get("module") or "sem_modulo"
        by_module[m] = by_module.get(m, 0) + 1
    return ok(
        {"total": total, "by_status": by_status, "by_module": by_module},
        module=MODULE,
    )


@router.get("")
async def list_homologacoes():
    return ok_list(homologacao.list_homologacao(), module=MODULE)


@router.get("/{entity_id}")
async def get_homologacao(entity_id: int):
    result = homologacao.get_homologacao(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return ok(result, module=MODULE)


@router.post("")
async def create_homologacao(data: schema.HomologacaoCreate):
    entity_id = homologacao.insert_homologacao(data.model_dump())
    return ok(homologacao.get_homologacao(entity_id), module=MODULE, meta={"action": "created"})


@router.put("/{entity_id}")
async def update_homologacao(entity_id: int, data: schema.HomologacaoUpdate):
    success = homologacao.update_homologacao(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return ok(homologacao.get_homologacao(entity_id), module=MODULE, meta={"action": "updated"})


@router.delete("/{entity_id}")
async def delete_homologacao(entity_id: int):
    success = homologacao.delete_homologacao(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Homologação não encontrada")
    return ok_deleted(module=MODULE)
