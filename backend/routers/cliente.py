"""Cliente API router — fully independent module."""

from fastapi import APIRouter, HTTPException
from typing import List

from ..models import cliente
from ..schemas import cliente as schema
from ..response import ok, ok_list, ok_deleted

MODULE = "cliente"
router = APIRouter(prefix="/cliente", tags=["cliente"])


@router.get("/stats")
async def get_stats():
    items = cliente.list_cliente()
    total = len(items)
    by_segment: dict[str, int] = {}
    for item in items:
        s = item.get("segment") or "sem_segmento"
        by_segment[s] = by_segment.get(s, 0) + 1
    return ok({"total": total, "by_segment": by_segment}, module=MODULE)


@router.get("")
async def list_clientes():
    return ok_list(cliente.list_cliente(), module=MODULE)


@router.get("/{entity_id}")
async def get_cliente(entity_id: int):
    result = cliente.get_cliente(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return ok(result, module=MODULE)


@router.post("")
async def create_cliente(data: schema.ClienteCreate):
    entity_id = cliente.insert_cliente(data.model_dump())
    return ok(cliente.get_cliente(entity_id), module=MODULE, meta={"action": "created"})


@router.put("/{entity_id}")
async def update_cliente(entity_id: int, data: schema.ClienteUpdate):
    success = cliente.update_cliente(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return ok(cliente.get_cliente(entity_id), module=MODULE, meta={"action": "updated"})


@router.delete("/{entity_id}")
async def delete_cliente(entity_id: int):
    success = cliente.delete_cliente(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return ok_deleted(module=MODULE)
