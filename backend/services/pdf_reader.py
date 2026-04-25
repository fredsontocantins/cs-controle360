"""PDF Reader Service - Extracts structured data from release note PDFs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


@dataclass
class AtividadeData:
    """Structured activity data extracted from PDF."""
    title: str
    tipo: str  # nova_funcionalidade, correcao_bug, melhoria
    ticket: str
    descricao_erro: str
    resolucao: str
    status: str = "backlog"


class PDFReaderService:
    """Extracts structured data from release note PDFs.

    This service uses pdfplumber to read text from PDF files and then parses
    it to extract structured activity data such as tickets, types, and
    descriptions.

    Expected PDF format (per line):
    - Ticket number: HOM-1234, BUG-567, etc.
    - Type: Nova Funcionalidade / Correção de Bug / Melhoria
    - Description: What was wrong or what was added
    - Resolution: How it was resolved
    """

    # Regex patterns for ticket detection
    TICKET_PATTERNS = [
        r'\b([A-Z]{2,}-\d+)\b',  # Standard PROJECT-1234
        r'\b(#[0-9]+)\b',        # #1234
        r'(\[[A-Z]{2,}-\d+\])', # [PROJECT-1234]
    ]

    # Keywords for type classification
    TIPO_KEYWORDS = {
        "correcao_bug": [
            "bug", "erro", "correção", "correcao", "fix", "defeito",
            "problema", "falha", "incorreto", "não funciona", "nao funciona"
        ],
        "nova_funcionalidade": [
            "nova funcionalidade", "new feature", "funcionalidade", "feature",
            "novo", "nova", "implementação", "implementacao", "adicionado"
        ],
        "melhoria": [
            "melhoria", "improvement", "otimização", "otimizacao", "refatora",
            "refatoração", "ajuste", "tuning", "performance", "melhorar"
        ],
    }

    def __init__(self):
        self.ticket_regex = re.compile('|'.join(self.TICKET_PATTERNS), re.IGNORECASE)

    def extract(self, pdf_path: str) -> List[AtividadeData]:
        """Extract activities from a PDF file."""
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF extraction. Install with: pip install pdfplumber")

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        activities = []
        text_blocks = self._extract_text_blocks(str(path))

        for block in text_blocks:
            activity = self._parse_block(block)
            if activity:
                activities.append(activity)

        return activities

    def _extract_text_blocks(self, pdf_path: str) -> List[str]:
        """Extract text blocks from PDF using pdfplumber."""
        blocks = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Split by lines and clean up
                    lines = text.split('\n')
                    current_block = []

                    for line in lines:
                        line = line.strip()
                        if not line:
                            if current_block:
                                blocks.append('\n'.join(current_block))
                                current_block = []
                        else:
                            current_block.append(line)

                    if current_block:
                        blocks.append('\n'.join(current_block))

        return blocks

    def _parse_block(self, block: str) -> Optional[AtividadeData]:
        """Parse a text block into structured activity data."""
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            return None

        # Extract ticket
        ticket = self._extract_ticket(block)
        if not ticket:
            ticket = f"PDF-{hashlib.md5(block.encode('utf-8')).hexdigest()[:8].upper()}"

        # Classify type
        tipo = self._classify_tipo(block)

        # Extract description and resolution
        descricao_erro, resolucao = self._extract_description_resolution(lines)
        title = self._build_title(ticket, tipo, descricao_erro)

        return AtividadeData(
            title=title,
            tipo=tipo,
            ticket=ticket,
            descricao_erro=descricao_erro,
            resolucao=resolucao,
            status="backlog"
        )

    def _extract_ticket(self, text: str) -> Optional[str]:
        """Extract ticket number from text."""
        match = self.ticket_regex.search(text)
        if match:
            return match.group(1).upper()
        return None

    def _classify_tipo(self, text: str) -> str:
        """Classify the activity type based on keywords."""
        text_lower = text.lower()

        # Check for bug/correction first (most specific)
        for keyword in self.TIPO_KEYWORDS["correcao_bug"]:
            if keyword in text_lower:
                return "correcao_bug"

        # Check for new functionality
        for keyword in self.TIPO_KEYWORDS["nova_funcionalidade"]:
            if keyword in text_lower:
                return "nova_funcionalidade"

        # Check for improvement
        for keyword in self.TIPO_KEYWORDS["melhoria"]:
            if keyword in text_lower:
                return "melhoria"

        # Default to improvement if no clear match
        return "melhoria"

    def _extract_description_resolution(self, lines: List[str]) -> tuple[str, str]:
        """Extract description and resolution from lines."""
        descricao_parts = []
        resolucao_parts = []
        in_resolution = False

        skip_keywords = ["ticket", "tipo", "descrição", "resolução", "problema", "solução"]

        for line in lines:
            line_lower = line.lower()

            # Skip header lines
            if any(kw in line_lower for kw in skip_keywords):
                if "resolu" in line_lower or "solu" in line_lower:
                    in_resolution = True
                continue

            # Check for resolution markers
            if any(marker in line_lower for marker in ["resolvido", "correção", "fix", "foi corrigido", "foi ajustado"]):
                in_resolution = True
                continue

            if in_resolution:
                resolucao_parts.append(line)
            else:
                # Skip very short lines that might be noise
                if len(line) > 5:
                    descricao_parts.append(line)

        descricao = " ".join(descricao_parts[:3])  # Limit to first 3 meaningful lines
        resolucao = " ".join(resolucao_parts[:3])

        return descricao or "Não disponível", resolucao or "Não disponível"

    def _build_title(self, ticket: str, tipo: str, descricao: str) -> str:
        """Build a concise title for the activity."""
        tipo_label = {
            "nova_funcionalidade": "Funcionalidade",
            "correcao_bug": "Correção",
            "melhoria": "Melhoria",
        }.get(tipo, "Atividade")
        base = descricao if descricao and descricao != "Não disponível" else ticket
        base = re.sub(r"\s+", " ", base).strip()
        if len(base) > 80:
            base = f"{base[:77].rstrip()}..."
        return f"{tipo_label} - {base}" if base else f"{tipo_label} - {ticket}"

    def extract_and_save(self, pdf_path: str, release_id: int) -> List[int]:
        """Extract activities from PDF and save to database.

        Returns list of created activity IDs.
        """
        from ..models.atividade import insert_atividade

        activities = self.extract(pdf_path)
        activity_ids = []

        for activity in activities:
            data = {
                "title": activity.title,
                "release_id": release_id,
                "tipo": activity.tipo,
                "ticket": activity.ticket,
                "descricao_erro": activity.descricao_erro,
                "resolucao": activity.resolucao,
                "status": activity.status,
            }
            activity_id = insert_atividade(data)
            activity_ids.append(activity_id)

        return activity_ids
