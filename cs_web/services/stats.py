"""Service for generating statistics and summaries for the dashboard."""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import Any, Dict, List

from cs_web import db

STAGE_LABELS = {
    "em_elaboracao": "Em Elaboração",
    "em_aprovacao": "Em Aprovação",
    "aprovadas": "Aprovadas",
    "aprovadas_sc": "Propostas Aprovadas (SC)",
}


def build_stage_summary(customizations: list[dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for entry in customizations:
        stage = entry.get("stage") or "unknown"
        totals = summary.setdefault(
            stage,
            {"label": STAGE_LABELS.get(stage, stage), "count": 0, "value": 0.0, "pf": 0.0},
        )
        totals["count"] += 1
        totals["value"] += float(entry.get("value") or 0)
        totals["pf"] += float(entry.get("pf") or 0)
    return summary


def build_homologated_chart(homologations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distribution of homologação status (Sim / Não / Pendente)."""
    buckets: Dict[str, int] = {"Sim": 0, "Não": 0, "Pendente": 0}
    for entry in homologations:
        value = (entry.get("homologated") or "").strip() or "Pendente"
        buckets[value] = buckets.get(value, 0) + 1
    return [{"label": label, "value": count} for label, count in buckets.items()]


def build_stage_chart(customizations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Customization funnel by stage, respecting STAGE_LABELS order."""
    counts: Dict[str, int] = {key: 0 for key in STAGE_LABELS}
    for entry in customizations:
        stage = entry.get("stage") or ""
        if stage in counts:
            counts[stage] += 1
    return [
        {"label": STAGE_LABELS[stage], "value": counts[stage]}
        for stage in STAGE_LABELS
    ]


def build_releases_chart(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Number of releases per month over the last 6 months (including current)."""
    today = date.today()
    months: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for _ in range(6):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    buckets: Dict[tuple[int, int], int] = {key: 0 for key in months}
    for entry in releases:
        for field in ("released_at", "created_at", "applied_at"):
            raw = entry.get(field)
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
            key = (parsed.year, parsed.month)
            if key in buckets:
                buckets[key] += 1
            break

    month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return [
        {"label": f"{month_names[m - 1]}/{y % 100:02d}", "value": buckets[(y, m)]}
        for (y, m) in months
    ]


def module_label(entry: dict[str, Any]) -> str:
    label = (entry.get("module") or "").strip()
    if label:
        return label
    module_id = entry.get("module_id")
    if module_id:
        module = db.modules.get(module_id)
        if module:
            return module.get("name") or "Sem módulo"
    return "Sem módulo"


def build_module_summary(
    homologations: list[dict[str, Any]],
    customizations: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> List[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    catalog = [module.get("name") for module in db.modules.list() if module.get("name")]
    for name in catalog:
        summary.setdefault(name, {"label": name, "homologations": 0, "customizations": 0, "releases": 0})

    def increment(label: str, kind: str) -> None:
        node = summary.setdefault(label, {"label": label, "homologations": 0, "customizations": 0, "releases": 0})
        node[kind] += 1

    for entry in homologations:
        label = module_label(entry)
        increment(label, "homologations")
    for entry in customizations:
        label = module_label(entry)
        increment(label, "customizations")
    for entry in releases:
        label = entry.get("module") or module_label(entry)
        increment(label, "releases")

    result = sorted(summary.values(), key=lambda item: (-(item["homologations"] + item["customizations"] + item["releases"]), item["label"]))
    for record in result:
        record["total"] = record["homologations"] + record["customizations"] + record["releases"]
    return result


def client_label(entry: dict[str, Any], client_lookup: dict[int, dict[str, Any]]) -> str:
    client_id = entry.get("client_id") or None
    if client_id:
        client = client_lookup.get(client_id)
        if client:
            return client.get("name") or "Sem cliente"
    return entry.get("client") or "Sem cliente"


def build_client_summary(
    clients: list[dict[str, Any]],
    homologations: list[dict[str, Any]],
    customizations: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> List[dict[str, Any]]:
    lookup = {client["id"]: client for client in clients}
    summary: dict[str, dict[str, Any]] = {}
    for client in clients:
        summary.setdefault(
            client["name"],
            {"name": client["name"], "homologations": 0, "customizations": 0, "releases": 0},
        )

    def increment(key: str, kind: str) -> None:
        node = summary.setdefault(key, {"name": key, "homologations": 0, "customizations": 0, "releases": 0})
        node[kind] += 1

    for record in homologations:
        label = client_label(record, lookup)
        increment(label, "homologations")
    for record in customizations:
        label = client_label(record, lookup)
        increment(label, "customizations")
    for record in releases:
        label = client_label(record, lookup)
        increment(label, "releases")

    return sorted(summary.values(), key=lambda item: (item["name"] or "").lower())


def get_meta_snapshot() -> Dict[str, Any]:
    return {
        "built_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": "Banco SQLite interno",
    }
