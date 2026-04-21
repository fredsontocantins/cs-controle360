"""Configuration for CS-Controle 360."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "controle360.db"

UPLOADS_DIR = BASE_DIR / "static" / "uploads"

API_KEY = os.getenv("CS_API_KEY", "cs-secret")
AUTH_ENABLED = os.getenv("CS_ADMIN_AUTH_ENABLED", "0") == "1"

# Table names
TABLE_HOMOLOGACAO = "homologacao"
TABLE_CUSTOMIZACAO = "customizations"
TABLE_ATIVIDADE = "activities"
TABLE_RELEASE = "releases"
TABLE_CLIENTE = "clients"
TABLE_MODULO = "modules"
TABLE_PLAYBOOK = "playbooks"
TABLE_REPORT_CYCLE = "report_cycles"

# Activity types
TIPO_NOVA_FUNCIONALIDADE = "nova_funcionalidade"
TIPO_CORRECAO_BUG = "correcao_bug"
TIPO_MELHORIA = "melhoria"

TIPO_OPTIONS = [TIPO_NOVA_FUNCIONALIDADE, TIPO_CORRECAO_BUG, TIPO_MELHORIA]

# Activity statuses for the Kanban board
STATUS_BACKLOG = "backlog"
STATUS_EM_ANDAMENTO = "em_andamento"
STATUS_EM_REVISAO = "em_revisao"
STATUS_CONCLUIDA = "concluida"
STATUS_BLOQUEADA = "bloqueada"

STATUS_OPTIONS = [
    STATUS_BACKLOG,
    STATUS_EM_ANDAMENTO,
    STATUS_EM_REVISAO,
    STATUS_CONCLUIDA,
    STATUS_BLOQUEADA,
]
