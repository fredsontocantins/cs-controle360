"""Playbook Pydantic schemas."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PlaybookBase(BaseModel):
    title: Optional[str] = None
    origin: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    source_key: Optional[str] = None
    source_label: Optional[str] = None
    area: Optional[str] = None
    priority_score: Optional[float] = None
    priority_level: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    metrics_json: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None


class PlaybookCreate(PlaybookBase):
    title: str = Field(...)
    origin: str = Field(...)


class PlaybookUpdate(BaseModel):
    title: Optional[str] = None
    area: Optional[str] = None
    priority_score: Optional[float] = None
    priority_level: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    metrics_json: Optional[Dict[str, Any]] = None


class PlaybookGenerateManual(BaseModel):
    title: str = Field(...)
    area: str = Field(default="Operacional")
    objective: Optional[str] = None
    audience: Optional[str] = None
    notes: Optional[str] = None


class PlaybookGenerateRelease(BaseModel):
    release_id: int = Field(...)


class PlaybookStatusUpdate(BaseModel):
    status: str = Field(...)


class ReportCycleCreate(BaseModel):
    scope_type: str = Field(default="reports")
    scope_id: Optional[int] = None
    scope_label: Optional[str] = None
    period_label: Optional[str] = None
    notes: Optional[str] = None


class ReportCycleClose(BaseModel):
    scope_type: str = Field(default="reports")
    scope_id: Optional[int] = None
    notes: Optional[str] = None
    reopen_new: bool = False
    scope_label: Optional[str] = None
    period_label: Optional[str] = None
