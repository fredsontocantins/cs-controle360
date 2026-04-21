"""Load and normalize the homologation and customization data."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Union

import pandas as pd

CUSTOMIZATION_COLUMN_MAPPING: Sequence[tuple[str, str]] = [
    ("ID", "source_id"),
    ("No. Proposta", "proposal"),
    ("PROPOSTA", "proposal"),
    ("Assunto", "subject"),
    ("ASSUNTO", "subject"),
    ("Cliente", "client"),
    ("Cliente ", "client"),
    ("Módulo", "module"),
    ("MÓDULO", "module"),
    ("Responsável Atual", "owner"),
    ("RECEB.", "received_at"),
    ("Dt recebimento", "received_at"),
    ("Data de Envio", "sent_at"),
    ("APROVADO", "approved_at"),
    ("DURAÇÃO", "duration"),
    ("ESTIMADO", "estimated_finish"),
    ("Qtde PF", "pf"),
    ("PF", "pf"),
    ("Valor", "value"),
    ("VALOR", "value"),
    ("Situação ", "status"),
    ("SITUAÇÃO", "status"),
    ("Observação", "observations"),
    ("Observações", "observations"),
    ("OBSERVAÇÕES", "observations"),
    ("Link Proposta ", "proposal_link"),
    ("Link OS ", "work_order_link"),
    ("SOLICITAÇÃO DE ORÇAMENTO", "budget_request"),
    ("PROPOSTA.1", "proposal_file"),
    ("ORDEM DE SERVIÇO", "work_order_file"),
    ("FATURADO", "invoiced"),
]

CUSTOMIZATION_LINK_FIELDS = {
    "proposal_link",
    "work_order_link",
    "budget_request",
    "proposal_file",
    "work_order_file",
}

CUSTOMIZATION_STAGE_SPECS = [
    {"sheet": "Em Elaboração", "stage": "em_elaboracao", "header": 0, "key": "No. Proposta"},
    {"sheet": "Em Aprovação", "stage": "em_aprovacao", "header": 0, "key": "No. Proposta"},
    {
        "sheet": "Aprovadas",
        "stage": "aprovadas",
        "header": 1,
        "key": "No.  Proposta",
    },
    {
        "sheet": "Propostas Aprovadas SC",
        "stage": "aprovadas_sc",
        "header": 2,
        "key": "PROPOSTA",
    },
]

HOMOLOGATION_COLUMN_MAP = {
    "Status": "status",
    "DATA DO CHECK": "check_date",
    "OBSERVAÇÃO": "observation",
    "MÓDULOS": "module",
    "Última Versão (Confluence)": "latest_version",
    "Versão Homologação": "homologation_version",
    "Versão Produção": "production_version",
    "Homologado": "homologated",
    "Apresentação cliente": "client_presentation",
    "Aplicado": "applied",
}


def _serialize_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return float(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return text or None


def _prune_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep: List[str] = []
    for col in df.columns:
        if not isinstance(col, str):
            continue
        clean = col.strip()
        if not clean:
            continue
        if clean.startswith("Unnamed"):
            continue
        if re.fullmatch(r"\d{4}-\d{2}", clean):
            continue
        if re.fullmatch(r"\d+(\.\d+)?", clean):
            continue
        keep.append(col)
    return df.loc[:, keep]


def load_homologation(filepath: Union[str, Path]) -> List[Dict[str, Any]]:
    filepath = Path(filepath)
    df = pd.read_excel(filepath, sheet_name="2026", header=3)
    df = df.dropna(subset=["Status"], how="all")
    monthly_cols = [
        col
        for col in df.columns
        if isinstance(col, str) and col.lower().startswith("vers")
    ]
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        record: Dict[str, Any] = {}
        for raw_col, alias in HOMOLOGATION_COLUMN_MAP.items():
            if raw_col not in row.index:
                continue
            value = _serialize_value(row[raw_col])
            if value is not None:
                record[alias] = value
        monthly_versions: Dict[str, Any] = {}
        for col in monthly_cols:
            value = _serialize_value(row[col])
            if value is not None:
                label = col.replace("Versão ", "").strip()
                monthly_versions[label] = value
        record["monthly_versions"] = monthly_versions
        records.append(record)
    return records


def load_customizations(filepath: Union[str, Path]) -> List[Dict[str, Any]]:
    filepath = Path(filepath)
    workbook = pd.ExcelFile(filepath)
    proposals: List[Dict[str, Any]] = []
    for spec in CUSTOMIZATION_STAGE_SPECS:
        sheet = spec["sheet"]
        if sheet not in workbook.sheet_names:
            continue
        df = pd.read_excel(filepath, sheet_name=sheet, header=spec["header"])
        df = _prune_columns(df)
        df = df.dropna(how="all")
        key_column = spec["key"]
        for _, row in df.iterrows():
            if key_column not in row.index:
                continue
            key_value = row[key_column]
            if pd.isna(key_value):
                continue
            key_serialized = _serialize_value(key_value)
            if isinstance(key_serialized, str) and key_serialized.lower().startswith("selecione"):
                continue
            entry: Dict[str, Any] = {"stage": spec["stage"], "source_sheet": sheet}
            links: Dict[str, Any] = {}
            for column, canonical in CUSTOMIZATION_COLUMN_MAPPING:
                if column not in row.index:
                    continue
                value = _serialize_value(row[column])
                if value is None:
                    continue
                if canonical in CUSTOMIZATION_LINK_FIELDS:
                    links[canonical] = value
                else:
                    entry[canonical] = value
            if links:
                entry["links"] = links
            proposals.append(entry)
    return proposals


def build_control_snapshot(
    homologation_file: Union[str, Path],
    customization_file: Union[str, Path],
) -> Dict[str, Any]:
    homopath = Path(homologation_file)
    custompath = Path(customization_file)
    return {
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": {
            "homologation": str(homopath.resolve()),
            "customization": str(custompath.resolve()),
        },
        "homologation": load_homologation(homopath),
        "customizations": load_customizations(custompath),
    }
