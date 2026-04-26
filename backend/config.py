"""Configuration for CS-Controle 360."""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cs_controle_360")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "controle360.db"
DATABASE_URL = os.getenv("DATABASE_URL")

UPLOADS_DIR = BASE_DIR / "static" / "uploads"

# Unsafe defaults that must NOT be used once AUTH_ENABLED is on outside dev.
_INSECURE_SECRET_DEFAULT = "cs-secret"

API_KEY = os.getenv("CS_API_KEY", _INSECURE_SECRET_DEFAULT)
AUTH_ENABLED = os.getenv("CS_ADMIN_AUTH_ENABLED", "1") == "1"
AUTH_SECRET = os.getenv("CS_AUTH_SECRET", API_KEY)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
AUTH_TOKEN_MAX_AGE_SECONDS = int(os.getenv("CS_AUTH_TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 24 * 7)))

# Allow unsafe defaults only in explicit dev mode. Production must export
# CS_API_KEY and CS_AUTH_SECRET or set CS_ALLOW_INSECURE_SECRETS=1 to opt in.
ALLOW_INSECURE_SECRETS = os.getenv("CS_ALLOW_INSECURE_SECRETS", "0") == "1"


def assert_secure_secrets() -> None:
    """Raise if auth is enabled but secrets still use the insecure defaults."""
    if not AUTH_ENABLED or ALLOW_INSECURE_SECRETS:
        return
    if API_KEY == _INSECURE_SECRET_DEFAULT or AUTH_SECRET == _INSECURE_SECRET_DEFAULT:
        raise RuntimeError(
            "CS-Controle 360: authentication is enabled but CS_API_KEY/CS_AUTH_SECRET "
            "are using the insecure default value. Set them explicitly or export "
            "CS_ALLOW_INSECURE_SECRETS=1 for local development."
        )


def parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

CORS_ORIGINS = parse_cors_origins(os.getenv("CS_CORS_ORIGINS")) or DEFAULT_CORS_ORIGINS

# Table names
TABLE_HOMOLOGACAO = "homologacao"
TABLE_CUSTOMIZACAO = "customizations"
TABLE_ATIVIDADE = "activities"
TABLE_RELEASE = "releases"
TABLE_CLIENTE = "clients"
TABLE_MODULO = "modules"
TABLE_ACTIVITY_OWNER = "activity_owners"
TABLE_ACTIVITY_STATUS = "activity_statuses"
TABLE_PLAYBOOK = "playbooks"
TABLE_REPORT_CYCLE = "report_cycles"
TABLE_USER = "users"
TABLE_AUTH_AUDIT = "auth_audit_logs"

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

STATUS_LABELS = {
    STATUS_BACKLOG: "Pendente",
    STATUS_EM_ANDAMENTO: "Em Andamento",
    STATUS_EM_REVISAO: "Em Revisão",
    STATUS_CONCLUIDA: "Concluída",
    STATUS_BLOQUEADA: "Bloqueada",
}

RESET_SAMPLE_DATA_ON_STARTUP = os.getenv("CS_RESET_SAMPLE_DATA_ON_STARTUP", "0") == "1"

def get_structured_logger(name: str):
    """Returns a logger with structured formatting."""
    l = logging.getLogger(name)
    # In a real scenario, we might add a JSON formatter here
    return l
