"""Generic PDF intelligence extraction and reporting."""

from __future__ import annotations

import html as html_lib
import hashlib
import json
import re
import subprocess
import tempfile
import textwrap
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import UPLOADS_DIR, logger
from ..models.atividade import list_atividade
from ..models.customizacao import list_customizacao
from ..models.homologacao import list_homologacao
from ..models.modulo import list_modulo
from ..models.playbook import list_playbooks
from ..models.pdf_document import count_documents, find_document_by_hash, get_document, list_documents, update_document
from ..models.release import list_release
from ..models.report_cycle import get_active_cycle
from fpdf import FPDF
from pypdf import PdfReader

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None


STOPWORDS = {
    "para", "com", "uma", "que", "das", "dos", "nas", "nos", "por", "em", "de",
    "da", "do", "o", "a", "e", "ou", "um", "uma", "ao", "à", "as", "os", "na",
    "no", "se", "foi", "ser", "são", "esta", "este", "isso", "essa", "esse",
    "the", "and", "of", "to", "in", "on", "for", "with", "by", "from",
}


@dataclass
class PdfIntelligence:
    scope_type: str
    scope_id: Optional[int]
    scope_label: Optional[str]
    filename: str
    pdf_path: str
    page_count: int
    word_count: int
    character_count: int
    ticket_count: int
    version_count: int
    date_count: int
    themes: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    problem_solution_pairs: List[Dict[str, Any]]
    knowledge_terms: List[Dict[str, Any]]
    action_items: List[str]
    recommendations: List[str]
    summary: str
    extracted_text: str
    generated_at: str


class PDFIntelligenceService:
    """Extracts structured intelligence from any uploaded PDF."""

    CONFIDENTIAL_TAG = "Classificação: Confidencial | Uso restrito ao cliente"

    TICKET_PATTERNS = [
        r"([A-Z]{2,}-\d{2,})",
        r"(\d{4,6})",
    ]

    TOPIC_KEYWORDS: Dict[str, List[str]] = {
        "Performance": ["performance", "lentidão", "lento", "cache", "query", "consulta", "otimiza"],
        "Qualidade": ["erro", "falha", "bug", "defeito", "correção", "correcao"],
        "Fluxo": ["fluxo", "status", "encaminhamento", "recebimento", "finalização", "cancelamento"],
        "Cadastro": ["cadastro", "cadastrar", "salvar", "duplicidade", "inserção"],
        "Busca": ["busca", "filtro", "autocomplete", "pesquisa", "seleção", "selecionar"],
        "Visual": ["visual", "layout", "estilo", "destaque", "cor", "tela", "card"],
        "Documento": ["pdf", "documento", "relatório", "relatorio", "anexo", "upload"],
        "Integração": ["integra", "api", "pncp", "notificação", "notificacao", "sincron"],
        "Auditoria": ["auditoria", "histórico", "historico", "rastreabilidade", "usuário", "usuario"],
        "Validação": ["validação", "validacao", "obrigatoriedade", "regra", "impedindo", "bloqueando"],
    }

    SECTION_KEYWORDS: Dict[str, List[str]] = {
        "problema": ["problema", "erros", "erro", "falha", "bug", "incidente", "não funciona", "nao funciona"],
        "solucao": ["solução", "solucao", "corrigido", "correção", "correcao", "ajuste", "implementado", "tratativa"],
        "impacto": ["impacto", "efeito", "resultado", "consequência", "consequencia", "alcance"],
        "objetivo": ["objetivo", "propósito", "proposito", "finalidade", "meta"],
        "escopo": ["escopo", "abrangência", "abrangencia", "módulo", "modulo", "processo"],
        "howto": ["how to", "como fazer", "passo a passo", "procedimento", "tutorial"],
        "checklist": ["checklist", "pré-requisitos", "pre-requisitos", "validação", "validacao"],
        "observacoes": ["observação", "observacao", "observações", "observacoes", "nota", "comentário", "comentario"],
        "beneficio": ["benefício", "beneficio", "vantagem", "ganho", "melhoria"],
    }

    def _file_hash(self, path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _file_size(self, path: str) -> int:
        return Path(path).stat().st_size

    def refresh_application_context(self) -> Dict[str, Any]:
        """Collect context from all analyzed PDF documents to build a global application knowledge base."""
        docs = list_documents()
        analyzed_docs = [d for d in docs if d.get("analysis_state") == "analyzed" and d.get("summary_json")]

        all_themes = []
        all_pairs = []
        all_knowledge = []
        all_recommendations = []
        all_tickets = set()

        for d in analyzed_docs:
            summary = json.loads(d["summary_json"])
            all_themes.extend(summary.get("themes", []))
            all_pairs.extend(summary.get("problem_solution_pairs", []))
            all_knowledge.extend(summary.get("knowledge_terms", []))
            all_recommendations.extend(summary.get("recommendations", []))

            text = summary.get("extracted_text", "")
            for pattern in self.TICKET_PATTERNS:
                all_tickets.update(re.findall(pattern, text))

        # Consolidate themes
        theme_counts = Counter([t["label"] for t in all_themes])
        top_themes = [{"label": label, "count": count} for label, count in theme_counts.most_common(10)]

        # Consolidate pairs and knowledge
        consolidated_pairs = self._deduplicate_items(all_pairs, "problem")
        consolidated_knowledge = self._deduplicate_items(all_knowledge, "term")

        # Build predictions based on frequent themes/problems
        predictions = []
        for theme in top_themes:
            if theme["count"] >= 3:
                predictions.append({
                    "type": "recurrent_theme",
                    "label": theme["label"],
                    "confidence": min(0.9, 0.4 + (theme["count"] * 0.1)),
                    "message": f"O tema '{theme['label']}' é recorrente (frequência: {theme['count']}). Recomenda-se revisão de fluxos relacionados."
                })

        return {
            "total_documents": len(docs),
            "analyzed_count": len(analyzed_docs),
            "top_themes": top_themes,
            "problem_solution_pairs": consolidated_pairs[:20],
            "knowledge_base": consolidated_knowledge[:20],
            "predictions": predictions,
            "detected_tickets": sorted(list(all_tickets))[:100],
            "last_updated": datetime.utcnow().isoformat()
        }

    def _deduplicate_items(self, items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for item in items:
            val = str(item.get(key, "")).strip().lower()
            if val and val not in seen:
                seen.add(val)
                unique.append(item)
        return unique

    def extract_text(self, pdf_path: str) -> str:
        """Extract plain text from PDF using multiple strategies."""
        text = ""
        # Strategy 1: pdfplumber (best for tables/layout)
        if pdfplumber:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception:
                pass

        # Strategy 2: pypdf (fallback)
        if not text.strip():
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception:
                pass

        return text.strip()

    def infer_allocation(
        self,
        pdf_path: str,
        filename: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        scope_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Heuristically infer where this PDF belongs if scope is not provided."""
        if scope_type and scope_id:
            return {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "scope_label": scope_label or f"{scope_type} #{scope_id}",
                "allocation_method": "manual"
            }

        # Try to infer from filename
        fname = filename.lower()

        # 1. Check releases
        releases = list_release()
        for rel in releases:
            v = str(rel.get("version", "")).lower()
            if v and v in fname:
                return {
                    "scope_type": "release",
                    "scope_id": rel["id"],
                    "scope_label": f"Release {rel.get('version')}",
                    "allocation_method": "filename_match"
                }

        # 2. Check modules
        modules = list_modulo()
        for mod in modules:
            name = str(mod.get("name", "")).lower()
            if name and name in fname:
                return {
                    "scope_type": "module",
                    "scope_id": mod["id"],
                    "scope_label": f"Módulo {mod.get('name')}",
                    "allocation_method": "filename_match"
                }

        # 3. Check customizations
        customs = list_customizacao()
        for c in customs:
            prop = str(c.get("proposal", "")).lower()
            if prop and prop in fname:
                return {
                    "scope_type": "customization",
                    "scope_id": c["id"],
                    "scope_label": f"Customização {c.get('proposal')}",
                    "allocation_method": "filename_match"
                }

        return {
            "scope_type": "global",
            "scope_id": None,
            "scope_label": "Painel Geral",
            "allocation_method": "default"
        }

    def analyze_pdf(
        self,
        pdf_path: str,
        filename: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        scope_label: Optional[str] = None,
    ) -> tuple[PdfIntelligence, Dict[str, Any]]:
        logger.info(f"Iniciando análise de PDF: {filename} ({pdf_path})")
        allocation = self.infer_allocation(
            pdf_path=pdf_path,
            filename=filename,
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
        )

        text = self.extract_text(pdf_path)
        if not text:
            # Fallback text if extraction fails completely
            text = f"Conteúdo do arquivo {filename}. Não foi possível extrair texto legível."

        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        words = [w for w in re.findall(r"\w+", text.lower()) if w not in STOPWORDS and len(w) > 2]

        # Identify themes based on keywords
        themes = []
        for label, keywords in self.TOPIC_KEYWORDS.items():
            count = sum(1 for k in keywords if k in text.lower())
            if count > 0:
                themes.append({"label": label, "relevance": count})
        themes = sorted(themes, key=lambda x: x["relevance"], reverse=True)

        # Identify sections
        sections = []
        for label, keywords in self.SECTION_KEYWORDS.items():
            for k in keywords:
                if k in text.lower():
                    sections.append({"label": label, "keyword": k})
                    break

        # Problem/Solution extraction (simple regex-based pattern matching)
        pairs = []
        problem_matches = re.findall(r"(?:problema|erro|falha):\s*(.*?)(?:\.|\n|$)", text, re.IGNORECASE)
        solution_matches = re.findall(r"(?:solução|solucao|correção|correcao):\s*(.*?)(?:\.|\n|$)", text, re.IGNORECASE)

        for i in range(min(len(problem_matches), len(solution_matches))):
            p = problem_matches[i].strip()
            s = solution_matches[i].strip()
            if p and s:
                pairs.append({"problem": p[:200], "solution": s[:200]})

        # Action items & Recommendations
        action_items = re.findall(r"(?:ação|acao|atividade|tarefa):\s*(.*?)(?:\.|\n|$)", text, re.IGNORECASE)
        recommendations = re.findall(r"(?:recomenda-se|sugestão|sugestao):\s*(.*?)(?:\.|\n|$)", text, re.IGNORECASE)

        # Count technical identifiers
        tickets = set()
        for pattern in self.TICKET_PATTERNS:
            tickets.update(re.findall(pattern, text))

        versions = set(re.findall(r"v\d+\.\d+\.\d+", text.lower()))
        dates = set(re.findall(r"\d{2}/\d{2}/\d{4}", text))

        intelligence = PdfIntelligence(
            scope_type=allocation["scope_type"],
            scope_id=allocation["scope_id"],
            scope_label=allocation["scope_label"],
            filename=filename,
            pdf_path=pdf_path,
            page_count=page_count,
            word_count=len(text.split()),
            character_count=len(text),
            ticket_count=len(tickets),
            version_count=len(versions),
            date_count=len(dates),
            themes=themes[:5],
            sections=sections,
            problem_solution_pairs=pairs[:5],
            knowledge_terms=[], # Future expansion
            action_items=[a.strip() for a in action_items if a.strip()][:5],
            recommendations=[r.strip() for r in recommendations if r.strip()][:5],
            summary=textwrap.shorten(text.replace("\n", " "), width=500, placeholder="..."),
            extracted_text=text,
            generated_at=datetime.utcnow().isoformat()
        )

        return intelligence, allocation

    def build_payload(self, intel: PdfIntelligence) -> Dict[str, Any]:
        """Convert intelligence dataclass to a JSON-ready dict for database storage."""
        return {
            "scope_type": intel.scope_type,
            "scope_id": intel.scope_id,
            "scope_label": intel.scope_label,
            "filename": intel.filename,
            "pdf_path": intel.pdf_path,
            "stats": {
                "pages": intel.page_count,
                "words": intel.word_count,
                "characters": intel.character_count,
                "tickets": intel.ticket_count,
                "versions": intel.version_count,
                "dates": intel.date_count,
            },
            "themes": intel.themes,
            "sections": intel.sections,
            "problem_solution_pairs": intel.problem_solution_pairs,
            "knowledge_terms": intel.knowledge_terms,
            "action_items": intel.action_items,
            "recommendations": intel.recommendations,
            "summary": intel.summary,
            "extracted_text": intel.extracted_text,
            "generated_at": intel.generated_at
        }

    def render_pdf_with_chrome(self, html: str, output_path: str) -> bool:
        """Render HTML to PDF using system tools (e.g. Chrome/Puppeteer/fpdf2)."""
        # For simplicity in this demo, we use fpdf2 to create a simple document
        # In production, this would use a headless browser for pixel-perfect HTML rendering
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Clean HTML tags for simple PDF text
            clean_text = re.sub(r'<[^>]+>', '', html)
            pdf.multi_cell(0, 10, clean_text)
            pdf.output(output_path)
            return True
        except Exception:
            return False

    def process_pending_documents(self) -> int:
        """Find documents needing analysis and process them."""
        docs = list_documents()
        pending = [d for d in docs if d.get("analysis_state") == "pending"]

        count = 0
        for d in pending:
            full_path = UPLOADS_DIR / Path(d["pdf_path"]).name
            if not full_path.exists():
                continue

            try:
                intel, allocation = self.analyze_pdf(
                    str(full_path),
                    d["filename"],
                    scope_type=d.get("scope_type"),
                    scope_id=d.get("scope_id"),
                    scope_label=d.get("scope_label")
                )
                payload = self.build_payload(intel)
                payload["analysis_state"] = "analyzed"
                payload["allocation_method"] = allocation.get("allocation_method", "re-processed")

                update_document(d["id"], {
                    "analysis_state": "analyzed",
                    "summary_json": json.dumps(payload, ensure_ascii=False),
                    "last_analyzed_at": datetime.utcnow().isoformat(),
                    "last_analyzed_hash": self._file_hash(str(full_path))
                })
                count += 1
            except Exception:
                update_document(d["id"], {"analysis_state": "error"})

        return count
