"""CLI helpers for the CS control tracker."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Union

import typer

from .loader import build_control_snapshot

app = typer.Typer(help="Process the homologação/customização workbooks for the CS team.")

STAGE_LABELS = {
    "em_elaboracao": "Em Elaboração",
    "em_aprovacao": "Em Aprovação",
    "aprovadas": "Aprovadas",
    "aprovadas_sc": "Propostas Aprovadas (SC)",
}


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def _human_currency(value: float) -> str:
    return f"R$ {value:,.2f}"


def _print_summary(snapshot: Dict[str, Any]) -> None:
    homologation = snapshot["homologation"]
    customizations = snapshot["customizations"]

    typer.echo(f"Homologation entries: {len(homologation)}")
    status_counts = Counter(entry.get("status") or "Sem status" for entry in homologation)
    for status, count in status_counts.most_common():
        typer.echo(f" - {status}: {count}")

    pending = [
        entry
        for entry in homologation
        if not entry.get("homologated")
        or str(entry.get("homologated")).lower() != "sim"
    ]
    if pending:
        snippet = ", ".join(
            str(entry.get("module", "módulo não informado"))
            for entry in pending[:4]
        )
        typer.echo(f"Pending homologation: {len(pending)} modules (e.g. {snippet})")

    typer.echo("")
    typer.echo("Customização pipeline:")
    stage_totals: Dict[str, Dict[str, float]] = {}
    for entry in customizations:
        stage = entry["stage"]
        totals = stage_totals.setdefault(stage, {"count": 0.0, "value": 0.0, "pf": 0.0})
        totals["count"] += 1
        totals["value"] += _to_number(entry.get("value"))
        totals["pf"] += _to_number(entry.get("pf"))

    for stage in STAGE_LABELS:
        totals = stage_totals.get(stage)
        label = STAGE_LABELS[stage]
        if not totals:
            continue
        typer.echo(
            f" - {label}: {int(totals['count'])} propostas / {int(totals['pf'])} PF / {_human_currency(totals['value'])}"
        )

    for stage in ("em_elaboracao", "em_aprovacao"):
        rows = [r for r in customizations if r["stage"] == stage]
        if not rows:
            continue
        typer.echo(f"\nTop {STAGE_LABELS[stage]}:")
        for row in rows[:3]:
            proposal = row.get("proposal") or row.get("source_id") or "nº desconhecido"
            client = row.get("client") or "cliente não informado"
            module = row.get("module") or "módulo indefinido"
            typer.echo(f"   • {proposal} [{module}] para {client}")


@app.command()
def export(
    homologacao_file: Path = Path("Controle de Homologação.xlsx"),
    customization_file: Path = Path("modelo Customização.xlsx"),
    output: Path = Path("control_snapshot.json"),
) -> None:
    """Generate a JSON snapshot that the CS system can consume."""
    snapshot = build_control_snapshot(homologacao_file, customization_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"Wrote {output}")


@app.command()
def summary(
    homologacao_file: Path = Path("Controle de Homologação.xlsx"),
    customization_file: Path = Path("modelo Customização.xlsx"),
) -> None:
    """Print a quick overview of the consolidated control data."""
    snapshot = build_control_snapshot(homologacao_file, customization_file)
    _print_summary(snapshot)


if __name__ == "__main__":
    app()
