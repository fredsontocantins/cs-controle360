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

from ..config import UPLOADS_DIR
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
        r"\b([A-Z]{2,}-\d{2,})\b",
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
        "dados": ["dados", "indicadores", "métrica", "metricas", "metrics", "sinal"],
    }

    def __init__(self) -> None:
        self.ticket_regex = re.compile("|".join(self.TICKET_PATTERNS), re.IGNORECASE)
        self.version_regex = re.compile(r"v?\d+\.\d+\.\d+")
        self.date_regex = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")

    def _resolve_pdf_path(self, record: Dict[str, Any]) -> str:
        pdf_path = str(UPLOADS_DIR.parent / record["pdf_path"])
        if Path(pdf_path).exists():
            return pdf_path
        return str(Path(record["pdf_path"]))

    def _file_hash(self, pdf_path: str) -> str:
        digest = hashlib.sha256()
        with Path(pdf_path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _file_size(self, pdf_path: str) -> int:
        try:
            return Path(pdf_path).stat().st_size
        except OSError:
            return 0

    def _current_cycle_id(self) -> Optional[int]:
        cycle = get_active_cycle("reports")
        if cycle and cycle.get("status") == "aberto":
            return cycle.get("id")
        return None

    def _normalize_text(self, *parts: str) -> str:
        return " ".join(part for part in parts if part).lower()

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+|\n+", text.replace("\r", "\n"))
        return [part.strip() for part in parts if part and part.strip()]

    def _sanitize_line(self, line: str) -> str:
        return re.sub(r"\s+", " ", line).strip(" \t-•;:|")

    def _extract_knowledge_terms(self, text: str) -> List[Dict[str, Any]]:
        words = [
            word.strip(".,;:()[]{}<>!?\"'").lower()
            for word in re.findall(r"[A-Za-zÀ-ÿ0-9_-]+", text)
        ]
        words = [
            word for word in words
            if len(word) > 3 and word not in STOPWORDS and not word.isdigit()
        ]
        counter = Counter(words)
        return [
            {"term": term, "count": count}
            for term, count in counter.most_common(20)
        ]

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        lines = [self._sanitize_line(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        sections: List[Dict[str, Any]] = []

        for section_name, keywords in self.SECTION_KEYWORDS.items():
            snippets: List[str] = []
            for index, line in enumerate(lines):
                lowered = line.lower()
                if any(keyword in lowered for keyword in keywords):
                    snippet = line
                    if index + 1 < len(lines):
                        next_line = lines[index + 1]
                        if next_line and len(next_line) < 180:
                            snippet = f"{line} {next_line}"
                    if snippet not in snippets:
                        snippets.append(snippet[:240])
                if len(snippets) >= 4:
                    break
            if snippets:
                sections.append(
                    {
                        "section": section_name,
                        "count": len(snippets),
                        "snippets": snippets,
                    }
                )

        return sections

    def _extract_problem_solution_pairs(self, text: str) -> List[Dict[str, Any]]:
        sentences = self._split_sentences(text)
        pairs: List[Dict[str, Any]] = []
        current_problem: Optional[str] = None
        for sentence in sentences:
            lower = sentence.lower()
            if any(marker in lower for marker in ("problema", "erro", "falha", "bug", "incidente", "não funciona", "nao funciona")):
                current_problem = sentence[:260]
                continue
            if any(marker in lower for marker in ("solução", "solucao", "corrig", "ajuste", "implement", "tratativa", "resolvido", "resolve")):
                pairs.append(
                    {
                        "problem": current_problem or "",
                        "solution": sentence[:260],
                    }
                )
                current_problem = None
        if current_problem and not pairs:
            pairs.append({"problem": current_problem[:260], "solution": ""})
        return pairs[:10]

    def infer_allocation(
        self,
        pdf_path: str,
        filename: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        scope_label: Optional[str] = None,
        extracted_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Infer the best destination context for a PDF."""
        if scope_type and scope_type not in {"auto", "global"}:
            return {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "scope_label": scope_label,
                "allocation_method": "explicit",
                "allocation_reason": "Contexto informado manualmente pelo usuário.",
            }

        text = extracted_text
        if text is None:
            try:
                text, _ = self.extract_text(pdf_path)
            except Exception:
                text = ""

        corpus = self._normalize_text(text, filename)
        version_match = self.version_regex.search(corpus)
        ticket_match = self.ticket_regex.search(corpus)
        modules = list_modulo()
        releases = list_release()
        customizacoes = list_customizacao()
        homologacoes = list_homologacao()
        atividades = list_atividade()

        module_match = next(
            (
                module
                for module in modules
                if str(module.get("name") or "").strip() and str(module.get("name")).lower() in corpus
            ),
            None,
        )

        if any(token in corpus for token in ("release", "versão", "versao", "changelog", "nota de release", "notas de release")) or version_match:
            matched_release = None
            if version_match:
                version = version_match.group(0).lstrip("v")
                matched_release = next((release for release in releases if str(release.get("version") or "") == version), None)
            if not matched_release and module_match:
                matched_release = next(
                    (
                        release
                        for release in releases
                        if release.get("module_id") == module_match.get("id")
                        or str(release.get("module") or "").lower() == str(module_match.get("name") or "").lower()
                    ),
                    None,
                )
            matched_release = matched_release or (releases[0] if releases else None)
            label = None
            if matched_release:
                label = matched_release.get("release_name") or matched_release.get("version")
            elif module_match:
                label = module_match.get("name")
            return {
                "scope_type": "release",
                "scope_id": matched_release.get("id") if matched_release else None,
                "scope_label": label or scope_label or "Release auto",
                "allocation_method": "auto_release",
                "allocation_reason": "Documento com sinais de release/notas de versão.",
            }

        if any(token in corpus for token in ("ticket", "erro", "bug", "falha", "backlog", "kanban", "atividade")) or ticket_match:
            matched_activity = None
            if ticket_match:
                ticket = ticket_match.group(0)
                matched_activity = next(
                    (
                        item
                        for item in atividades
                        if str(item.get("ticket") or "").lower() == ticket.lower()
                        or ticket.lower() in str(item.get("descricao_erro") or "").lower()
                        or ticket.lower() in str(item.get("title") or "").lower()
                    ),
                    None,
                )
            matched_activity = matched_activity or (atividades[0] if atividades else None)
            label = None
            if matched_activity:
                label = matched_activity.get("title") or matched_activity.get("ticket")
            elif module_match:
                label = module_match.get("name")
            return {
                "scope_type": "atividade",
                "scope_id": matched_activity.get("id") if matched_activity else None,
                "scope_label": label or scope_label or "Atividade auto",
                "allocation_method": "auto_activity",
                "allocation_reason": "Documento com indícios de atividade, ticket ou bug.",
            }

        if any(token in corpus for token in ("customiza", "proposta", "pf ", "valor", "escopo")):
            matched_customizacao = None
            if module_match:
                matched_customizacao = next(
                    (
                        item
                        for item in customizacoes
                        if str(item.get("module_id") or "") == str(module_match.get("id"))
                        or str(item.get("module") or "").lower() == str(module_match.get("name") or "").lower()
                    ),
                    None,
                )
            matched_customizacao = matched_customizacao or (customizacoes[0] if customizacoes else None)
            label = None
            if matched_customizacao:
                label = matched_customizacao.get("subject") or matched_customizacao.get("proposal")
            elif module_match:
                label = module_match.get("name")
            return {
                "scope_type": "customizacao",
                "scope_id": matched_customizacao.get("id") if matched_customizacao else None,
                "scope_label": label or scope_label or "Customização auto",
                "allocation_method": "auto_customizacao",
                "allocation_reason": "Documento com sinais de proposta/customização.",
            }

        if any(token in corpus for token in ("homolog", "produção", "producao", "validação", "validacao", "checklist")):
            matched_homologacao = None
            if module_match:
                matched_homologacao = next(
                    (
                        item
                        for item in homologacoes
                        if str(item.get("module_id") or "") == str(module_match.get("id"))
                        or str(item.get("module") or "").lower() == str(module_match.get("name") or "").lower()
                    ),
                    None,
                )
            matched_homologacao = matched_homologacao or (homologacoes[0] if homologacoes else None)
            label = None
            if matched_homologacao:
                label = matched_homologacao.get("module") or matched_homologacao.get("client")
            elif module_match:
                label = module_match.get("name")
            return {
                "scope_type": "homologacao",
                "scope_id": matched_homologacao.get("id") if matched_homologacao else None,
                "scope_label": label or scope_label or "Homologação auto",
                "allocation_method": "auto_homologacao",
                "allocation_reason": "Documento com sinais de homologação/validação.",
            }

        return {
            "scope_type": "global",
            "scope_id": None,
            "scope_label": module_match.get("name") if module_match else (scope_label or "Documento global"),
            "allocation_method": "auto_global",
            "allocation_reason": "Documento sem sinal forte de módulo ou situação específica.",
        }

    def should_refresh_document(self, record: Dict[str, Any]) -> bool:
        pdf_path = self._resolve_pdf_path(record)
        if not Path(pdf_path).exists():
            return False

        current_hash = self._file_hash(pdf_path)
        stored_hash = record.get("last_analyzed_hash") or record.get("file_hash")
        if not stored_hash:
            return True
        if stored_hash != current_hash:
            return True

        summary = record.get("summary") or {}
        return not bool(summary)

    def extract_text(self, pdf_path: str) -> tuple[str, int]:
        path = Path(pdf_path)
        pages_text: List[str] = []

        if pdfplumber is not None:
            try:
                with pdfplumber.open(str(path)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        if not page_text:
                            words = page.extract_words() or []
                            page_text = " ".join(word.get("text", "") for word in words)
                        pages_text.append((page_text or "").strip())
                    text = "\n".join(filter(None, pages_text))
                    return text, len(pdf.pages)
            except Exception:
                pages_text = []

        reader = PdfReader(str(path))
        for page in reader.pages:
            pages_text.append((page.extract_text() or "").strip())
        text = "\n".join(filter(None, pages_text))
        return text, len(reader.pages)

    def analyze(
        self,
        pdf_path: str,
        filename: str,
        scope_type: str,
        scope_id: Optional[int] = None,
        scope_label: Optional[str] = None,
    ) -> PdfIntelligence:
        text, page_count = self.extract_text(pdf_path)
        normalized = re.sub(r"\s+", " ", text).strip()
        words = [word.strip(".,;:()[]{}<>!?\"'").lower() for word in normalized.split()]
        words = [word for word in words if len(word) > 2 and word not in STOPWORDS]

        counter = Counter(words)
        top_words = counter.most_common(12)
        ticket_count = len(set(self.ticket_regex.findall(text)))
        version_count = len(set(self.version_regex.findall(text)))
        date_count = len(set(self.date_regex.findall(text)))
        word_count = len(words)
        character_count = len(text)

        themes = self._extract_themes(text, top_words)
        sections = self._extract_sections(text)
        problem_solution_pairs = self._extract_problem_solution_pairs(text)
        knowledge_terms = self._extract_knowledge_terms(text)
        action_items = self._extract_action_items(text)
        recommendations = self._build_recommendations(text, themes, ticket_count, sections, problem_solution_pairs)
        summary = self._build_summary(scope_type, scope_label, page_count, ticket_count, version_count, themes, action_items, sections)

        return PdfIntelligence(
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
            filename=filename,
            pdf_path=pdf_path,
            page_count=page_count,
            word_count=word_count,
            character_count=character_count,
            ticket_count=ticket_count,
            version_count=version_count,
            date_count=date_count,
            themes=themes,
            sections=sections,
            problem_solution_pairs=problem_solution_pairs,
            knowledge_terms=knowledge_terms,
            action_items=action_items,
            recommendations=recommendations,
            summary=summary,
            extracted_text=text[:40000],
            generated_at=datetime.utcnow().isoformat(),
        )

    def analyze_record(self, record: Dict[str, Any]) -> PdfIntelligence:
        """Re-read a stored document from disk and rebuild its intelligence."""
        pdf_path = self._resolve_pdf_path(record)
        return self.analyze(
            pdf_path=pdf_path,
            filename=record.get("filename", Path(pdf_path).name),
            scope_type=record.get("scope_type", "unknown"),
            scope_id=record.get("scope_id"),
            scope_label=record.get("scope_label"),
        )

    def analyze_pdf(
        self,
        pdf_path: str,
        filename: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        scope_label: Optional[str] = None,
    ) -> tuple[PdfIntelligence, Dict[str, Any]]:
        allocation = self.infer_allocation(
            pdf_path=pdf_path,
            filename=filename,
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
        )
        analysis = self.analyze(
            pdf_path=pdf_path,
            filename=filename,
            scope_type=allocation["scope_type"],
            scope_id=allocation.get("scope_id"),
            scope_label=allocation.get("scope_label"),
        )
        return analysis, allocation

    def refresh_document(self, record: Dict[str, Any], cycle_id: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
        """Refresh a stored document summary from the current PDF content."""
        pdf_path = self._resolve_pdf_path(record)
        current_hash = self._file_hash(pdf_path) if Path(pdf_path).exists() else None
        current_size = self._file_size(pdf_path) if Path(pdf_path).exists() else None
        should_refresh = force or self.should_refresh_document(record) or str(record.get("analysis_state") or "").lower() in {"pending", "new", "staged"}
        target_cycle_id = record.get("report_cycle_id") or cycle_id or self._current_cycle_id()

        if should_refresh:
            analysis = self.analyze_record(record)
            payload = self.build_payload(analysis)
            update_document(
                record["id"],
                {
                    "scope_type": payload["scope_type"],
                    "scope_id": payload["scope_id"],
                    "scope_label": payload["scope_label"],
                    "filename": payload["filename"],
                    "pdf_path": payload["pdf_path"],
                    "file_hash": current_hash,
                    "file_size": current_size,
                    "analysis_state": record.get("analysis_state") or "analyzed",
                    "summary_json": payload,
                    "last_analyzed_at": payload["generated_at"],
                    "last_analyzed_hash": current_hash,
                    "report_cycle_id": target_cycle_id,
                },
            )
            refreshed = get_document(record["id"])
            return refreshed or {**record, "summary": payload}

        summary = record.get("summary") or {}
        if current_hash and record.get("file_hash") != current_hash:
            update_document(
                record["id"],
                {
                    "file_hash": current_hash,
                    "file_size": current_size,
                    "analysis_state": record.get("analysis_state") or "analyzed",
                    "last_analyzed_hash": current_hash,
                    "last_analyzed_at": record.get("last_analyzed_at") or datetime.utcnow().isoformat(),
                    "report_cycle_id": target_cycle_id,
                },
            )
            refreshed = get_document(record["id"])
            return refreshed or record

        return record if summary else {**record, "summary": summary}

    def refresh_documents(
        self,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Re-read stored PDFs only when content changed or when required by cycle."""
        refreshed: List[Dict[str, Any]] = []
        records = list_documents(scope_type=scope_type, scope_id=scope_id)
        if cycle_id is not None:
            records = [
                record
                for record in records
                if record.get("report_cycle_id") in (cycle_id, None)
            ]
        for record in records:
            try:
                refreshed.append(self.refresh_document(record, cycle_id=cycle_id))
            except FileNotFoundError:
                continue
        return refreshed

    def process_documents(
        self,
        document_ids: Optional[List[int]] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process pending PDFs and optionally force re-read selected documents."""
        records = list_documents()
        selected_ids = {int(item) for item in (document_ids or [])}
        processed: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []

        for record in records:
            record_id = int(record.get("id") or 0)
            is_selected = record_id in selected_ids
            analysis_state = str(record.get("analysis_state") or "").lower()
            needs_processing = is_selected or self.should_refresh_document(record) or analysis_state in {"pending", "new", "staged"} or not record.get("summary")

            if not needs_processing:
                skipped.append(
                    {
                        "filename": record.get("filename"),
                        "status": "already_analyzed",
                        "message": "Documento já analisado e atualizado.",
                        "document_id": record_id,
                        "scope_type": record.get("scope_type"),
                        "scope_label": record.get("scope_label"),
                    }
                )
                continue

            try:
                processed.append(self.refresh_document(record, cycle_id=cycle_id, force=is_selected))
            except FileNotFoundError:
                skipped.append(
                    {
                        "filename": record.get("filename"),
                        "status": "missing",
                        "message": "Arquivo PDF não encontrado no armazenamento.",
                        "document_id": record_id,
                        "scope_type": record.get("scope_type"),
                        "scope_label": record.get("scope_label"),
                    }
                )

        return {
            "documents": processed,
            "skipped_documents": skipped,
            "messages": [item["message"] for item in skipped],
        }

    def build_predictions(
        self,
        documents: List[Dict[str, Any]],
        activities: Optional[List[Dict[str, Any]]] = None,
        releases: Optional[List[Dict[str, Any]]] = None,
        playbooks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        activities = activities or list_atividade()
        releases = releases or list_release()
        playbooks = playbooks or list_playbooks()

        doc_theme_counter: Counter[str] = Counter()
        doc_section_counter: Counter[str] = Counter()
        problem_cues = 0
        solution_cues = 0
        for doc in documents:
            summary = doc.get("summary") or {}
            for theme in summary.get("themes", []):
                doc_theme_counter[str(theme.get("theme", "Tema"))] += int(theme.get("count") or 0)
            for section in summary.get("sections", []):
                doc_section_counter[str(section.get("section", "secao"))] += int(section.get("count") or 0)
            for pair in summary.get("problem_solution_pairs", []):
                if pair.get("problem"):
                    problem_cues += 1
                if pair.get("solution"):
                    solution_cues += 1

        top_doc_themes = doc_theme_counter.most_common(3)
        top_doc_sections = doc_section_counter.most_common(3)
        open_activities = [
            item for item in activities
            if str(item.get("status", "")).lower() not in {"concluida", "finalizada", "fechado", "closed"}
        ]
        blocked_activities = [
            item for item in activities
            if str(item.get("status", "")).lower() in {"bloqueada", "blocked"}
        ]
        active_releases = [item for item in releases if item.get("id") is not None]
        playbook_areas = {str(item.get("area") or "").strip().lower() for item in playbooks if item.get("area")}
        doc_scopes = Counter(str(doc.get("scope_type") or "global") for doc in documents)

        predictions: List[Dict[str, Any]] = []

        if top_doc_themes:
            theme, count = top_doc_themes[0]
            predictions.append(
                {
                    "type": "tendencia",
                    "title": f"Tendência dominante em {theme}",
                    "detail": f"O tema '{theme}' aparece com recorrência nos PDFs e tende a continuar como foco do próximo ciclo.",
                    "confidence": min(95, 55 + count * 8),
                    "action": f"Priorizar playbooks e relatórios para o tema '{theme}'.",
                }
            )

        if top_doc_sections:
            section, count = top_doc_sections[0]
            label_map = {
                "problema": "Problemas recorrentes",
                "solucao": "Soluções documentadas",
                "impacto": "Impacto operacional",
                "objetivo": "Objetivos do ciclo",
                "escopo": "Escopo e abrangência",
                "howto": "Procedimentos operacionais",
                "checklist": "Checklist de validação",
                "observacoes": "Observações e avisos",
                "beneficio": "Benefícios entregues",
                "dados": "Dados e indicadores",
            }
            predictions.append(
                {
                    "type": "conhecimento",
                    "title": label_map.get(section, section.replace("_", " ").title()),
                    "detail": f"A base local identificou {count} menção(ões) ao bloco '{section}' nos PDFs processados.",
                    "confidence": min(88, 58 + count * 7),
                    "action": "Explorar essas seções para enriquecer relatórios, playbooks e treinamentos.",
                }
            )

        if open_activities:
            by_module: Counter[str] = Counter(str(item.get("module") or item.get("module_name") or "Sem módulo") for item in open_activities)
            module_name, count = by_module.most_common(1)[0]
            predictions.append(
                {
                    "type": "operacional",
                    "title": f"Backlog concentrado em {module_name}",
                    "detail": f"{len(open_activities)} atividade(s) seguem abertas, com concentração em {module_name}.",
                    "confidence": min(90, 50 + count * 10),
                    "action": "Revisar gargalos de execução e reforçar o kanban de acompanhamento.",
                }
            )

        if blocked_activities:
            predictions.append(
                {
                    "type": "risco",
                    "title": "Risco de bloqueio operacional",
                    "detail": f"{len(blocked_activities)} atividade(s) estão bloqueadas e podem afetar entregas do ciclo.",
                    "confidence": min(92, 60 + len(blocked_activities) * 6),
                    "action": "Abrir tratativa imediata para desbloqueio e atualização de status.",
                }
            )

        missing_playbooks = []
        for theme, _count in top_doc_themes:
            if theme.lower() not in playbook_areas:
                missing_playbooks.append(theme)
        if missing_playbooks:
            predictions.append(
                {
                    "type": "conhecimento",
                    "title": "Lacuna de documentação",
                    "detail": f"Os temas {', '.join(missing_playbooks[:3])} aparecem nos PDFs, mas não têm playbook correspondente.",
                    "confidence": 78,
                    "action": "Gerar playbooks automáticos para cobrir a lacuna de conhecimento.",
                }
            )

        if problem_cues and solution_cues:
            predictions.append(
                {
                    "type": "conhecimento",
                    "title": "Correlação problema/solução consolidada",
                    "detail": f"Os PDFs trazem {problem_cues} sinais de problema e {solution_cues} sinais de solução, úteis para padronizar conhecimento.",
                    "confidence": min(90, 62 + min(problem_cues, solution_cues) * 4),
                    "action": "Usar os pares problema/solução para construir playbooks, FAQ e treinamento guiado.",
                }
            )

        if active_releases and doc_scopes.get("release", 0) > 0:
            predictions.append(
                {
                    "type": "release",
                    "title": "Nova release com tendência de suporte",
                    "detail": "Documentos de release e atividades mostram necessidade de acompanhamento próximo das próximas publicações.",
                    "confidence": 72,
                    "action": "Criar playbook por release e reforçar a comunicação com usuários impactados.",
                }
            )

        if not predictions:
            predictions.append(
                {
                    "type": "base",
                    "title": "Base estável para análise",
                    "detail": "Não foram identificados sinais fortes de risco, mas a leitura preditiva deve ser reavaliada a cada novo PDF.",
                    "confidence": 50,
                    "action": "Manter coleta contínua de PDFs e atividades para aumentar a precisão da previsão.",
                }
            )

        return predictions[:6]

    def build_application_context(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate intelligence from every PDF in the application."""
        unique_documents: List[Dict[str, Any]] = []
        seen_hashes: set[str] = set()
        for doc in documents:
            document_hash = str(doc.get("file_hash") or doc.get("last_analyzed_hash") or doc.get("id"))
            if document_hash in seen_hashes:
                continue
            seen_hashes.add(document_hash)
            unique_documents.append(doc)

        totals = {
            "documents": len(unique_documents),
            "pages": 0,
            "words": 0,
            "tickets": 0,
            "versions": 0,
            "dates": 0,
        }
        theme_counter: Counter[str] = Counter()
        scope_counter: Counter[str] = Counter()
        section_counter: Counter[str] = Counter()
        actions: List[str] = []
        recommendations: List[str] = []
        highlights: List[Dict[str, Any]] = []
        knowledge_terms_counter: Counter[str] = Counter()
        problem_solution_examples: List[Dict[str, Any]] = []

        for doc in unique_documents:
            summary = doc.get("summary") or {}
            totals["pages"] += int(summary.get("page_count") or 0)
            totals["words"] += int(summary.get("word_count") or 0)
            totals["tickets"] += int(summary.get("ticket_count") or 0)
            totals["versions"] += int(summary.get("version_count") or 0)
            totals["dates"] += int(summary.get("date_count") or 0)
            scope_counter[str(doc.get("scope_type") or "global")] += 1
            for theme in summary.get("themes", []):
                theme_counter[str(theme.get("theme", "Tema"))] += int(theme.get("count") or 0)
            for section in summary.get("sections", []):
                section_counter[str(section.get("section", "secao"))] += int(section.get("count") or 0)
            for term in summary.get("knowledge_terms", []):
                knowledge_terms_counter[str(term.get("term", ""))] += int(term.get("count") or 0)
            for item in summary.get("action_items", []):
                if item not in actions:
                    actions.append(item)
            for item in summary.get("recommendations", []):
                if item not in recommendations:
                    recommendations.append(item)
            for pair in summary.get("problem_solution_pairs", []):
                if pair.get("problem") or pair.get("solution"):
                    problem_solution_examples.append(
                        {
                            "filename": doc.get("filename"),
                            "problem": pair.get("problem"),
                            "solution": pair.get("solution"),
                        }
                    )
            highlights.append(
                {
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "scope_type": doc.get("scope_type"),
                    "scope_label": doc.get("scope_label"),
                    "summary": summary.get("summary"),
                    "themes": summary.get("themes", [])[:3],
                    "sections": summary.get("sections", [])[:3],
                }
            )

        top_themes = [
            {"theme": theme, "count": count, "examples": []}
            for theme, count in theme_counter.most_common(8)
        ]
        top_scopes = [
            {"scope_type": scope, "count": count}
            for scope, count in scope_counter.most_common()
        ]
        top_sections = [
            {"section": section, "count": count}
            for section, count in section_counter.most_common(8)
        ]
        knowledge_terms = [
            {"term": term, "count": count}
            for term, count in knowledge_terms_counter.most_common(20)
        ]
        predictions = self.build_predictions(unique_documents)

        return {
            "totals": totals,
            "themes": top_themes,
            "scopes": top_scopes,
            "sections": top_sections,
            "knowledge_terms": knowledge_terms,
            "action_items": actions[:20],
            "recommendations": recommendations[:20],
            "highlights": highlights[:12],
            "problem_solution_examples": problem_solution_examples[:12],
            "predictions": predictions,
        }

    def refresh_application_context(self) -> Dict[str, Any]:
        """Return the aggregated application context from the stored documents."""
        cycle = get_active_cycle("reports")
        cycle_id = cycle.get("id") if cycle else None
        documents = list_documents()
        unique_documents: List[Dict[str, Any]] = []
        seen_hashes: set[str] = set()
        for doc in documents:
            document_hash = str(doc.get("file_hash") or doc.get("last_analyzed_hash") or doc.get("id"))
            if document_hash in seen_hashes:
                continue
            seen_hashes.add(document_hash)
            unique_documents.append(doc)

        context = self.build_application_context(unique_documents)
        context["documents"] = unique_documents
        context["total_documents"] = len(unique_documents)
        context["all_time_documents"] = count_documents()
        context["cycle_documents"] = count_documents(report_cycle_id=cycle_id) if cycle_id is not None else len(unique_documents)
        context["generated_at"] = datetime.utcnow().isoformat()
        context["cycle"] = cycle
        context["cycle_id"] = cycle_id
        return context

    def build_cycle_audit(self) -> Dict[str, Any]:
        """Return a cycle-level audit for PDFs already read versus new or changed files."""
        cycle = get_active_cycle("reports")
        cycle_id = cycle.get("id") if cycle else None
        documents = list_documents()
        new_documents: List[Dict[str, Any]] = []
        changed_documents: List[Dict[str, Any]] = []
        already_read: List[Dict[str, Any]] = []
        legacy_documents: List[Dict[str, Any]] = []
        pending_documents: List[Dict[str, Any]] = []

        for record in documents:
            pdf_path = self._resolve_pdf_path(record)
            exists = Path(pdf_path).exists()
            current_hash = self._file_hash(pdf_path) if exists else None
            stored_hash = record.get("last_analyzed_hash") or record.get("file_hash")
            same_cycle = cycle_id is not None and record.get("report_cycle_id") == cycle_id
            legacy = record.get("report_cycle_id") is None
            has_summary = bool(record.get("summary") or record.get("summary_json"))

            if not exists:
                pending_documents.append({**record, "audit_state": "missing"})
                continue

            if legacy:
                legacy_documents.append({**record, "audit_state": "legacy"})

            if not stored_hash:
                pending_documents.append({**record, "audit_state": "new"})
                new_documents.append({**record, "audit_state": "new"})
                continue

            if current_hash and stored_hash != current_hash:
                changed_documents.append({**record, "audit_state": "changed"})
                continue

            if same_cycle or has_summary:
                already_read.append({**record, "audit_state": "read"})
                continue

            pending_documents.append({**record, "audit_state": "pending"})

        return {
            "cycle": cycle,
            "cycle_id": cycle_id,
            "generated_at": datetime.utcnow().isoformat(),
            "counts": {
                "all": len(documents),
                "already_read": len(already_read),
                "new": len(new_documents),
                "changed": len(changed_documents),
                "legacy": len(legacy_documents),
                "pending": len(pending_documents),
            },
            "already_read": already_read[:20],
            "new_documents": new_documents[:20],
            "changed_documents": changed_documents[:20],
            "legacy_documents": legacy_documents[:20],
            "pending_documents": pending_documents[:20],
        }

    def _extract_themes(self, text: str, top_words: List[tuple[str, int]]) -> List[Dict[str, Any]]:
        lower = text.lower()
        themes: List[Dict[str, Any]] = []
        for label, keywords in self.TOPIC_KEYWORDS.items():
            count = 0
            examples: List[str] = []
            for keyword in keywords:
                hits = lower.count(keyword)
                if hits:
                    count += hits
                    if len(examples) < 3:
                        examples.append(keyword)
            if count:
                themes.append({"theme": label, "count": count, "examples": examples})

        if not themes:
            themes = [
                {"theme": word.title(), "count": count, "examples": []}
                for word, count in top_words[:6]
            ]

        return sorted(themes, key=lambda item: item["count"], reverse=True)

    def _extract_action_items(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        candidates: List[str] = []
        action_markers = (
            "implement", "implementado", "adicionado", "corrigido", "ajustado",
            "refatorado", "necessário", "necessario", "passa a", "deve", "precisa",
            "permitir", "melhorado", "otimizado",
        )
        for sentence in sentences:
            lowered = sentence.lower().strip()
            if len(lowered) < 20:
                continue
            if any(marker in lowered for marker in action_markers):
                cleaned = sentence.strip()
                if cleaned not in candidates:
                    candidates.append(cleaned[:220])
            if len(candidates) >= 8:
                break
        return candidates

    def _build_recommendations(
        self,
        text: str,
        themes: List[Dict[str, Any]],
        ticket_count: int,
        sections: Optional[List[Dict[str, Any]]] = None,
        problem_solution_pairs: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        lower = text.lower()
        recommendations: List[str] = []
        sections = sections or []
        problem_solution_pairs = problem_solution_pairs or []

        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Performance"]):
            recommendations.append("Abrir revisão de performance com prioridade para consultas, cache e carga das telas impactadas.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Fluxo"]):
            recommendations.append("Validar transições de status e regras de fluxo antes de liberar mudanças em produção.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Validação"]):
            recommendations.append("Reforçar validações de entrada e padronização de payload entre frontend e backend.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Documento"]):
            recommendations.append("Manter trilha de anexos e anexar documentos críticos ao registro gerencial.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Auditoria"]):
            recommendations.append("Aprimorar rastreabilidade de eventos, aprovações e leitura de documentos para auditoria interna.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Busca"]):
            recommendations.append("Fortalecer pesquisa textual, filtros e indexação de conteúdo para acelerar a consulta de PDFs.")
        if any(keyword in lower for keyword in self.TOPIC_KEYWORDS["Visual"]):
            recommendations.append("Revisar a camada visual do documento exportado para reforçar legibilidade e hierarquia da informação.")
        if ticket_count > 10:
            recommendations.append("Dividir a análise por release e módulo para evitar sobrecarga na leitura gerencial.")
        if themes and themes[0]["count"] >= 3:
            recommendations.append(f"Concentrar monitoramento no tema '{themes[0]['theme']}' por recorrência no documento.")
        if any(keyword in lower for keyword in self.SECTION_KEYWORDS["checklist"]):
            recommendations.append("Converter trechos de checklist em ações operacionais e critérios de aceite rastreáveis.")
        if any(keyword in lower for keyword in self.SECTION_KEYWORDS["howto"]):
            recommendations.append("Extrair o passo a passo em formato de playbook reutilizável para treinamento de equipes.")
        if any(keyword in lower for keyword in self.SECTION_KEYWORDS["beneficio"]):
            recommendations.append("Conectar benefícios descritos no PDF com indicadores de adoção e redução de retrabalho.")
        if any(keyword in lower for keyword in self.SECTION_KEYWORDS["solucao"]):
            recommendations.append("Organizar as soluções em catálogo de conhecimento para reaproveitamento por módulo e processo.")
        if sections:
            section_labels = ", ".join(section["section"] for section in sections[:3])
            recommendations.append(f"Usar as seções {section_labels} como base para sumarização executiva e treinamento.")
        if problem_solution_pairs:
            recommendations.append("Transformar os pares problema/solução em playbooks curtos para consulta rápida da operação.")
        if not recommendations:
            recommendations.append("Documento analisado sem riscos explícitos, mas recomenda-se validação manual dos principais destaques.")

        return recommendations[:6]

    def _build_summary(
        self,
        scope_type: str,
        scope_label: Optional[str],
        page_count: int,
        ticket_count: int,
        version_count: int,
        themes: List[Dict[str, Any]],
        action_items: List[str],
        sections: List[Dict[str, Any]],
    ) -> str:
        label = scope_label or scope_type
        theme_text = themes[0]["theme"] if themes else "sem tema recorrente identificado"
        action_text = action_items[0] if action_items else "sem ação destacada"
        section_text = sections[0]["section"] if sections else "sem seção explícita"
        return (
            f"PDF '{label}' com {page_count} página(s), {ticket_count} ticket(s) detectado(s) e "
            f"{version_count} versão(ões). Tema dominante: {theme_text}. "
            f"Seção dominante: {section_text}. Primeira ação destacada: {action_text}"
        )

    def build_payload(self, intelligence: PdfIntelligence) -> Dict[str, Any]:
        return {
            "scope_type": intelligence.scope_type,
            "scope_id": intelligence.scope_id,
            "scope_label": intelligence.scope_label,
            "filename": intelligence.filename,
            "pdf_path": intelligence.pdf_path,
            "page_count": intelligence.page_count,
            "word_count": intelligence.word_count,
            "character_count": intelligence.character_count,
            "ticket_count": intelligence.ticket_count,
            "version_count": intelligence.version_count,
            "date_count": intelligence.date_count,
            "themes": intelligence.themes,
            "sections": intelligence.sections,
            "problem_solution_pairs": intelligence.problem_solution_pairs,
            "knowledge_terms": intelligence.knowledge_terms,
            "action_items": intelligence.action_items,
            "recommendations": intelligence.recommendations,
            "summary": intelligence.summary,
            "extracted_text": intelligence.extracted_text,
            "generated_at": intelligence.generated_at,
        }

    def build_html_report(self, intelligence: PdfIntelligence) -> str:
        payload = self.build_payload(intelligence)
        rows = "".join(
            f"<span class='pill'>{theme['theme']} ({theme['count']})</span>"
            for theme in payload["themes"]
        ) or "<span class='muted'>Nenhum tema identificado.</span>"
        actions = "".join(f"<li>{item}</li>" for item in payload["action_items"]) or "<li>Sem ações extraídas.</li>"
        recs = "".join(f"<li>{item}</li>" for item in payload["recommendations"])
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>CS CONTROLE 360 - Inteligência PDF Confidencial - {payload['filename']}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
.hero {{ background: linear-gradient(135deg, #0d3b66, #184e77); color: white; border-radius: 20px; padding: 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 18px; }}
.card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px; }}
.muted {{ color: #6b7280; }}
.pill {{ display: inline-block; background: #dbeafe; color: #1d4ed8; padding: 6px 10px; border-radius: 999px; margin: 0 8px 8px 0; }}
h2 {{ margin-top: 24px; }}
ul {{ line-height: 1.6; }}
.confidential {{ margin-top: 14px; padding: 12px 16px; background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; border-radius: 14px; font-size: 13px; }}
.footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }}
</style>
</head>
<body>
<div class='hero'>
  <h1 style='margin:0;'>Inteligência de PDF</h1>
  <p style='margin:8px 0 0 0;'>{payload['summary']}</p>
</div>
<div class='confidential'>{self.CONFIDENTIAL_TAG} | Documento destinado ao cliente e às áreas autorizadas.</div>
<div class='grid'>
  <div class='card'><div class='muted'>Páginas</div><strong>{payload['page_count']}</strong></div>
  <div class='card'><div class='muted'>Palavras</div><strong>{payload['word_count']}</strong></div>
  <div class='card'><div class='muted'>Tickets</div><strong>{payload['ticket_count']}</strong></div>
  <div class='card'><div class='muted'>Versões</div><strong>{payload['version_count']}</strong></div>
</div>
<h2>Temas e Focos Analíticos</h2>
<div>{rows}</div>
<h2>Ações Extraídas</h2>
<ul>{actions}</ul>
<h2>Recomendações Executivas</h2>
<ul>{recs}</ul>
<h2>Texto Extraído</h2>
<pre style='white-space: pre-wrap; background:#f9fafb; padding:16px; border-radius:16px; border:1px solid #e5e7eb;'>{payload['extracted_text'][:12000]}</pre>
<div class='footer'>Material confidencial e de uso restrito ao cliente. Distribuição somente para perfis autorizados.</div>
</body>
</html>"""

    def render_pdf_with_chrome(self, html: str, output_path: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as html_file:
            html_file.write(html)
            html_path = html_file.name

        try:
            subprocess.run(
                [
                    "google-chrome",
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    f"--print-to-pdf={output_path}",
                    html_path,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            self._render_pdf_fallback(html, output_path)
        finally:
            Path(html_path).unlink(missing_ok=True)

    def _render_pdf_fallback(self, html: str, output_path: str) -> None:
        """Render a readable PDF fallback when headless Chrome fails."""
        def _safe_text(value: str) -> str:
            text = html_lib.unescape(value)
            return text.encode("latin-1", "replace").decode("latin-1")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        effective_width = pdf.w - pdf.l_margin - pdf.r_margin

        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = _safe_text(title_match.group(1).strip()) if title_match else "Relatório"
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.multi_cell(effective_width, 8, title)
        pdf.ln(2)
        pdf.set_font("Helvetica", size=11)

        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = _safe_text(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            if line == title:
                continue
            for chunk in textwrap.wrap(line, width=110, break_long_words=True, break_on_hyphens=False) or [""]:
                pdf.multi_cell(effective_width, 6, chunk)

        pdf.output(output_path)
