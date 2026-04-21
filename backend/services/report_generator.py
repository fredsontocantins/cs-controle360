"""Report Generator Service - Creates executive and analytical reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TIPO_CORRECAO_BUG, TIPO_MELHORIA, TIPO_NOVA_FUNCIONALIDADE, TIPO_OPTIONS
from ..models.atividade import list_atividade
from ..models.modulo import list_modulo
from ..models.release import list_release


@dataclass
class TicketSummary:
    """Summary of a single ticket."""

    ticket: str
    tipo: str
    descricao: str
    resolucao: str
    status: str
    title: str
    module: str
    release: str
    version: str


@dataclass
class InsightCard:
    """Human-readable management insight."""

    title: str
    detail: str
    severity: str = "info"


class ReportGenerator:
    """Generates management reports from activities, releases and modules."""

    TIPO_LABELS = {
        TIPO_NOVA_FUNCIONALIDADE: "Nova Funcionalidade",
        TIPO_CORRECAO_BUG: "Correção de Bug",
        TIPO_MELHORIA: "Melhoria",
    }

    THEME_KEYWORDS: Dict[str, List[str]] = {
        "Performance": ["performance", "lentidão", "lento", "otimiza", "cache", "query", "consulta"],
        "Fluxo": ["fluxo", "transição", "status", "recebimento", "encaminhamento", "finalização"],
        "Cadastro": ["cadastro", "cadastrar", "salvar", "inserção", "duplicidade"],
        "Busca/Filtro": ["busca", "filtro", "autocomplete", "pesquisa", "seleção", "selecionar"],
        "Visual": ["visual", "layout", "estilo", "destaque", "cor", "card", "tela"],
        "Documento/PDF": ["pdf", "documento", "relatório", "relatorio", "anexo", "upload"],
        "Integração": ["integra", "pncp", "api", "notificação", "notificacao", "sincron"],
        "Validação": ["validação", "validacao", "obrigatoriedade", "regra", "impedindo", "bloqueando"],
        "Auditoria": ["auditoria", "histórico", "historico", "rastreabilidade", "usuário", "usuario"],
    }

    def _parse_datetime(self, value: Any) -> datetime:
        if not value:
            return datetime.min

        text = str(value).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ):
            try:
                return datetime.strptime(text[:19] if fmt.endswith("%S") and "T" in text else text, fmt)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return datetime.min

    def _safe_label(self, value: Optional[str], fallback: str) -> str:
        return value.strip() if value and value.strip() else fallback

    def _build_indexes(
        self,
        activities: List[Dict[str, Any]],
    ) -> tuple[list[Dict[str, Any]], dict[int, Dict[str, Any]], dict[int, Dict[str, Any]], dict[str, Dict[str, Any]]]:
        modules = list_modulo()
        releases = list_release()

        module_by_id = {module["id"]: module for module in modules if module.get("id") is not None}
        release_by_id = {release["id"]: release for release in releases if release.get("id") is not None}
        module_by_name = {
            self._safe_label(module.get("name"), f"Módulo {module.get('id', '')}"): module
            for module in modules
        }

        return activities, release_by_id, module_by_id, module_by_name

    def _resolve_module_name(
        self,
        release: Optional[Dict[str, Any]],
        module_by_id: dict[int, Dict[str, Any]],
        module_by_name: dict[str, Dict[str, Any]],
        activity: Optional[Dict[str, Any]] = None,
    ) -> str:
        if release:
            if release.get("module"):
                return str(release["module"])
            module_id = release.get("module_id")
            if module_id and module_id in module_by_id:
                return self._safe_label(module_by_id[module_id].get("name"), "Sem módulo")

        if activity and activity.get("module"):
            return str(activity["module"])

        if activity and activity.get("module_id") and activity["module_id"] in module_by_id:
            return self._safe_label(module_by_id[activity["module_id"]].get("name"), "Sem módulo")

        return "Sem módulo"

    def _resolve_release_name(self, release: Optional[Dict[str, Any]], activity: Optional[Dict[str, Any]] = None) -> str:
        if release:
            name = release.get("release_name")
            version = release.get("version")
            if name and version:
                return f"{name} ({version})"
            if version:
                return f"v{version}"
        if activity and activity.get("release_name"):
            return str(activity["release_name"])
        return "Sem release"

    def _analyze_themes(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        corpus = " ".join(
            " ".join(
                [
                    str(item.get("title", "")),
                    str(item.get("ticket", "")),
                    str(item.get("descricao", "")),
                    str(item.get("resolucao", "")),
                    str(item.get("module", "")),
                    str(item.get("release", "")),
                ]
            )
            for item in tickets
        ).lower()

        themes = []
        for label, keywords in self.THEME_KEYWORDS.items():
            count = 0
            examples: list[str] = []
            for item in tickets:
                text = " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("descricao", "")),
                        str(item.get("resolucao", "")),
                    ]
                ).lower()
                if any(keyword in text for keyword in keywords):
                    count += 1
                    if len(examples) < 3:
                        examples.append(str(item.get("ticket", "")))
            if count:
                themes.append({"theme": label, "count": count, "examples": examples})

        if not themes and corpus.strip():
            # Fallback to the most repeated generic words when the keyword buckets are empty.
            words = [word for word in corpus.split() if len(word) > 3]
            top = Counter(words).most_common(5)
            themes = [
                {"theme": word.title(), "count": count, "examples": []}
                for word, count in top
            ]

        return sorted(themes, key=lambda item: item["count"], reverse=True)

    def _build_management_report(
        self,
        activities: List[Dict[str, Any]],
        release_id: Optional[int] = None,
        release_name: Optional[str] = None,
        pdf_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        activities = activities or []
        all_releases = list_release()
        if release_id is not None:
            all_releases = [release for release in all_releases if release.get("id") == release_id]

        all_modules = list_modulo()
        if release_id is not None:
            scoped_module_ids = {release.get("module_id") for release in all_releases if release.get("module_id")}
            if scoped_module_ids:
                all_modules = [module for module in all_modules if module.get("id") in scoped_module_ids]
            else:
                scoped_module_names = {release.get("module") for release in all_releases if release.get("module")}
                if scoped_module_names:
                    all_modules = [module for module in all_modules if module.get("name") in scoped_module_names]

        activities, release_by_id, module_by_id, module_by_name = self._build_indexes(activities)

        enriched_tickets: List[Dict[str, Any]] = []
        by_type: dict[str, int] = {tipo: 0 for tipo in TIPO_OPTIONS}
        by_status: Counter[str] = Counter()
        by_module: defaultdict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "module": "",
                "releases": 0,
                "corrections": 0,
                "improvements": 0,
                "tickets": 0,
                "latest_version": "—",
                "latest_release": "—",
                "latest_release_date": datetime.min.isoformat(),
            }
        )
        release_rows: defaultdict[int, Dict[str, Any]] = defaultdict(
            lambda: {
                "id": None,
                "module": "Sem módulo",
                "release_name": "Sem release",
                "version": "—",
                "applies_on": None,
                "tickets": 0,
                "corrections": 0,
                "improvements": 0,
                "by_status": Counter(),
                "last_activity_at": None,
            }
        )

        for release in all_releases:
            release_id = release.get("id")
            if release_id is None:
                continue

            module_name = self._resolve_module_name(release, module_by_id, module_by_name)
            release_label = self._resolve_release_name(release)
            release_date = self._parse_datetime(release.get("applies_on") or release.get("created_at"))

            release_entry = release_rows[release_id]
            release_entry.update(
                {
                    "id": release_id,
                    "module": module_name,
                    "release_name": release.get("release_name") or release_label,
                    "version": release.get("version") or "—",
                    "applies_on": release.get("applies_on"),
                }
            )

            module_entry = by_module[module_name]
            module_entry["module"] = module_name
            module_entry["releases"] += 1
            if release_date >= self._parse_datetime(module_entry["latest_release_date"]):
                module_entry["latest_release_date"] = release_date.isoformat()
                module_entry["latest_version"] = release.get("version") or "—"
                module_entry["latest_release"] = release.get("release_name") or f"v{release.get('version') or '—'}"

        for activity in activities:
            release = release_by_id.get(activity.get("release_id"))
            module_name = self._resolve_module_name(release, module_by_id, module_by_name, activity)
            release_label = self._resolve_release_name(release, activity)
            tipo = activity.get("tipo", TIPO_MELHORIA)
            status = activity.get("status", "backlog")
            ticket_number = activity.get("ticket") or "N/A"
            title = activity.get("title") or ticket_number
            descricao = activity.get("descricao_erro") or activity.get("description") or ""
            resolucao = activity.get("resolucao") or ""
            created_at = activity.get("created_at")

            enriched = {
                "ticket": ticket_number,
                "tipo": tipo,
                "tipo_label": self.TIPO_LABELS.get(tipo, tipo),
                "status": status,
                "title": title,
                "descricao": descricao,
                "resolucao": resolucao,
                "module": module_name,
                "release": release_label,
                "version": release.get("version") if release else "—",
                "release_id": activity.get("release_id"),
                "created_at": created_at,
            }
            enriched_tickets.append(enriched)

            if tipo in by_type:
                by_type[tipo] += 1
            by_status[status] += 1

            module_entry = by_module[module_name]
            module_entry["module"] = module_name
            module_entry["tickets"] += 1
            if tipo == TIPO_CORRECAO_BUG:
                module_entry["corrections"] += 1
            elif tipo == TIPO_NOVA_FUNCIONALIDADE:
                module_entry["improvements"] += 1

            if release and release.get("id") in release_rows:
                release_entry = release_rows[release["id"]]
                release_entry["tickets"] += 1
                if tipo == TIPO_CORRECAO_BUG:
                    release_entry["corrections"] += 1
                elif tipo == TIPO_NOVA_FUNCIONALIDADE:
                    release_entry["improvements"] += 1
                release_entry["by_status"][status] += 1
                created_dt = self._parse_datetime(created_at)
                last_activity = self._parse_datetime(release_entry["last_activity_at"])
                if created_dt >= last_activity:
                    release_entry["last_activity_at"] = created_at

        module_rows = []
        for module_name, data in by_module.items():
            total_tickets = data["tickets"] or 0
            release_total = data["releases"] or 0
            share = round((total_tickets / len(activities)) * 100, 1) if activities else 0.0
            module_rows.append(
                {
                    "module": module_name,
                    "releases": release_total,
                    "corrections": data["corrections"],
                    "improvements": data["improvements"],
                    "tickets": total_tickets,
                    "latest_version": data["latest_version"],
                    "latest_release": data["latest_release"],
                    "share": share,
                }
            )

        module_rows.sort(key=lambda item: (item["tickets"], item["releases"], item["module"]), reverse=True)

        release_rows_list = []
        for release in all_releases:
            release_id = release.get("id")
            if release_id is None:
                continue
            row = release_rows[release_id]
            release_rows_list.append(
                {
                    "id": release_id,
                    "module": row["module"],
                    "release_name": row["release_name"],
                    "version": row["version"],
                    "applies_on": row["applies_on"],
                    "tickets": row["tickets"],
                    "corrections": row["corrections"],
                    "improvements": row["improvements"],
                    "by_status": dict(row["by_status"]),
                    "last_activity_at": row["last_activity_at"],
                }
            )

        release_rows_list.sort(
            key=lambda item: (
                self._parse_datetime(item.get("applies_on")) or datetime.min,
                item.get("version") or "",
            ),
            reverse=True,
        )

        total_releases = len(all_releases)
        total_modules = len(all_modules)
        total_tickets = len(activities)
        total_corrections = by_type[TIPO_CORRECAO_BUG]
        total_improvements = by_type[TIPO_MELHORIA]
        total_features = by_type[TIPO_NOVA_FUNCIONALIDADE]

        top_module = module_rows[0] if module_rows else None
        top_release = max(release_rows_list, key=lambda item: item["tickets"], default=None)
        themes = self._analyze_themes(enriched_tickets)
        pdf_context = pdf_context or {}
        pdf_totals = pdf_context.get("totals") or {}
        pdf_themes = pdf_context.get("themes") or []
        pdf_recommendations = pdf_context.get("recommendations") or []
        pdf_actions = pdf_context.get("action_items") or []
        pdf_highlights = pdf_context.get("highlights") or []
        pdf_predictions = pdf_context.get("predictions") or []

        insights: List[InsightCard] = []
        if top_module and top_module["tickets"]:
            insights.append(
                InsightCard(
                    title="Concentração de demanda",
                    detail=f"{top_module['module']} concentra {top_module['tickets']} tickets ({top_module['share']}% do total analisado).",
                    severity="warning",
                )
            )

        if total_corrections > total_improvements:
            insights.append(
                InsightCard(
                    title="Perfil do ciclo",
                    detail="O volume de correções está acima do volume de melhorias, indicando foco em estabilização e refinamento operacional.",
                    severity="info",
                )
            )
        elif total_improvements > total_corrections:
            insights.append(
                InsightCard(
                    title="Perfil do ciclo",
                    detail="As melhorias superam as correções, sugerindo espaço para evolução funcional e ganho de experiência do usuário.",
                    severity="success",
                )
            )

        if by_status.get("backlog", 0):
            insights.append(
                InsightCard(
                    title="Fila operacional",
                    detail=f"Há {by_status['backlog']} atividades em backlog. O relatório deve priorizar triagem e definição de SLA.",
                    severity="warning",
                )
            )

        if top_release and top_release["tickets"]:
            insights.append(
                InsightCard(
                    title="Release mais carregada",
                    detail=f"{top_release['release_name']} reúne {top_release['tickets']} tickets e merece revisão gerencial.",
                    severity="info",
                )
            )

        if themes:
            leading_theme = themes[0]
            insights.append(
                InsightCard(
                    title="Tema recorrente",
                    detail=f"O tema '{leading_theme['theme']}' aparece com maior frequência no relatório.",
                    severity="info",
                )
            )

        if pdf_themes:
            insights.append(
                InsightCard(
                    title="Leitura global de PDFs",
                    detail=f"A aplicação consolidou {pdf_totals.get('documents', 0)} documento(s) e destacou o tema '{pdf_themes[0]['theme']}'.",
                    severity="info",
                )
            )

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "scope": {
                "release_id": release_id,
                "release_name": release_name,
            },
            "totals": {
                "modules": total_modules,
                "releases": total_releases,
                "tickets": total_tickets,
                "corrections": total_corrections,
                "improvements": total_improvements,
                "features": total_features,
            },
            "by_type": {tipo: by_type[tipo] for tipo in TIPO_OPTIONS},
            "by_status": dict(by_status),
            "module_summary": module_rows,
            "release_summary": release_rows_list,
            "tickets": enriched_tickets,
            "themes": themes,
            "insights": [insight.__dict__ for insight in insights],
            "top_module": top_module,
            "top_release": top_release,
            "errors": [item for item in enriched_tickets if item["tipo"] == TIPO_CORRECAO_BUG],
            "features_list": [item for item in enriched_tickets if item["tipo"] == TIPO_NOVA_FUNCIONALIDADE],
            "improvements_list": [item for item in enriched_tickets if item["tipo"] == TIPO_MELHORIA],
            "pdf_context": pdf_context,
            "pdf_totals": pdf_totals,
            "pdf_themes": pdf_themes,
            "pdf_recommendations": pdf_recommendations,
            "pdf_actions": pdf_actions,
            "pdf_highlights": pdf_highlights,
            "pdf_predictions": pdf_predictions,
        }

    def generate_ticket_report(
        self,
        activities: List[Dict[str, Any]],
        release_id: Optional[int] = None,
        release_name: Optional[str] = None,
        pdf_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate the analytical report used by the reports menu."""
        report = self._build_management_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
        )
        report["total"] = report["totals"]["tickets"]
        report["by_type"] = report["by_type"]
        report["errors"] = report["errors"]
        report["features"] = report["features_list"]
        report["improvements"] = report["improvements_list"]
        return report

    def generate_summary_report(
        self,
        activities: List[Dict[str, Any]],
        release_id: Optional[int] = None,
        release_name: Optional[str] = None,
        pdf_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a text summary report in the same structure as the PDF."""
        report = self._build_management_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
        )

        lines = [
            "=" * 72,
            "CS CONTROLE 360 - RELATÓRIO GERENCIAL",
            "=" * 72,
            f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}",
            "",
            "Resumo Executivo",
            "-" * 72,
            f"Total de releases: {report['totals']['releases']}",
            f"Módulos: {report['totals']['modules']}",
            f"Correções: {report['totals']['corrections']}",
            f"Melhorias: {report['totals']['improvements']}",
            f"Tickets: {report['totals']['tickets']}",
            "",
            "Resumo por Módulo",
            "-" * 72,
        ]

        if report["module_summary"]:
            for module in report["module_summary"]:
                lines.append(
                    f"{module['module']} | Releases: {module['releases']} | "
                    f"Correções: {module['corrections']} | Melhorias: {module['improvements']} | "
                    f"Tickets: {module['tickets']} | Última versão: {module['latest_version']}"
                )
        else:
            lines.append("Nenhum módulo encontrado.")

        lines.extend(
            [
                "",
                "Destaques Analíticos",
                "-" * 72,
            ]
        )

        if report["insights"]:
            for insight in report["insights"]:
                lines.append(f"- {insight['title']}: {insight['detail']}")
        else:
            lines.append("Nenhum insight disponível.")

        lines.extend(
            [
                "",
                "Temas Recorrentes",
                "-" * 72,
            ]
        )
        if report["themes"]:
            for theme in report["themes"]:
                examples = f" Exemplos: {', '.join(theme['examples'])}" if theme.get("examples") else ""
                lines.append(f"- {theme['theme']}: {theme['count']} ocorrência(s).{examples}")
        else:
            lines.append("Nenhum tema recorrente identificado.")

        lines.extend(
            [
                "",
                "Tickets",
                "-" * 72,
            ]
        )
        if report["tickets"]:
            for item in report["tickets"]:
                lines.append(
                    f"[{item['ticket']}] ({item['tipo_label']}) [{item['status']}] "
                    f"{item['title']} - {item['descricao'][:80]}"
                )
                if item.get("resolucao"):
                    lines.append(f"  Solução: {item['resolucao'][:120]}")
        else:
            lines.append("Nenhum ticket registrado.")

        lines.extend(
            [
                "",
                "Inteligência de PDFs",
                "-" * 72,
                f"Documentos processados: {report['pdf_totals'].get('documents', 0)}",
                f"Páginas lidas: {report['pdf_totals'].get('pages', 0)}",
                f"Palavras lidas: {report['pdf_totals'].get('words', 0)}",
                f"Tickets detectados nos PDFs: {report['pdf_totals'].get('tickets', 0)}",
            ]
        )
        if report["pdf_themes"]:
            for theme in report["pdf_themes"][:8]:
                lines.append(f"- {theme['theme']}: {theme['count']} ocorrência(s)")
        if report["pdf_actions"]:
            lines.append("")
            lines.append("Ações extraídas dos PDFs")
            for action in report["pdf_actions"][:8]:
                lines.append(f"- {action}")
        if report["pdf_recommendations"]:
            lines.append("")
            lines.append("Recomendações globais dos PDFs")
            for item in report["pdf_recommendations"][:8]:
                lines.append(f"- {item}")
        if report["pdf_predictions"]:
            lines.append("")
            lines.append("Previsões preditivas")
            for item in report["pdf_predictions"][:8]:
                lines.append(f"- {item['title']}: {item['detail']}")

        return "\n".join(lines)

    def generate_html_report(
        self,
        activities: List[Dict[str, Any]],
        release_id: Optional[int] = None,
        release_name: Optional[str] = None,
        pdf_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate an HTML management report."""
        report = self._build_management_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
        )

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            f"<title>Relatório Gerencial{f' - {release_name}' if release_name else ''}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 32px; color: #1f2937; background: #f9fafb; }",
            ".hero { background: linear-gradient(135deg, #0d3b66, #184e77); color: white; padding: 28px; border-radius: 20px; }",
            ".muted { color: #6b7280; }",
            ".grid { display: grid; gap: 16px; }",
            ".grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }",
            ".grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }",
            ".card { background: white; border: 1px solid #e5e7eb; border-radius: 18px; padding: 18px; box-shadow: 0 10px 20px rgba(15,23,42,.05); }",
            ".stat { font-size: 28px; font-weight: 800; color: #0d3b66; }",
            "table { width: 100%; border-collapse: collapse; }",
            "th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }",
            "th { background: #f3f4f6; text-transform: uppercase; letter-spacing: .04em; font-size: 12px; }",
            ".pill { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; margin: 0 6px 6px 0; }",
            ".pill-info { background: #dbeafe; color: #1d4ed8; }",
            ".pill-success { background: #dcfce7; color: #15803d; }",
            ".pill-warning { background: #fef3c7; color: #b45309; }",
            ".pill-danger { background: #fee2e2; color: #b91c1c; }",
            ".ticket { border-left: 4px solid #0d3b66; padding: 14px 16px; margin: 14px 0; background: white; border-radius: 14px; }",
            ".ticket h4 { margin: 0 0 6px 0; }",
            ".section { margin-top: 24px; }",
            ".section h2 { margin-bottom: 12px; color: #0f172a; }",
            ".bar { height: 10px; background: #dbeafe; border-radius: 999px; overflow: hidden; }",
            ".bar > span { display: block; height: 100%; background: #0d3b66; }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='hero'>",
            f"<h1 style='margin:0 0 8px 0;'>CS Controle 360 - Relatório Gerencial</h1>",
            f"<p style='margin:0;'>Gerado em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</p>",
            f"<p style='margin:8px 0 0 0;'>Release selecionada: {release_name or 'Todas'}</p>",
            "</div>",
            "<div class='section grid grid-4' style='margin-top: 20px;'>",
            f"<div class='card'><div class='muted'>Releases</div><div class='stat'>{report['totals']['releases']}</div></div>",
            f"<div class='card'><div class='muted'>Módulos</div><div class='stat'>{report['totals']['modules']}</div></div>",
            f"<div class='card'><div class='muted'>Correções</div><div class='stat'>{report['totals']['corrections']}</div></div>",
            f"<div class='card'><div class='muted'>Melhorias</div><div class='stat'>{report['totals']['improvements']}</div></div>",
            "</div>",
        ]

        if report["insights"]:
            html_parts.extend([
                "<div class='section'>",
                "<h2>Destaques Gerenciais</h2>",
                "<div class='grid grid-2'>",
            ])
            for insight in report["insights"]:
                pill_class = {
                    "success": "pill-success",
                    "warning": "pill-warning",
                    "danger": "pill-danger",
                }.get(insight["severity"], "pill-info")
                html_parts.append(
                    f"<div class='card'><span class='pill {pill_class}'>{insight['title']}</span><p>{insight['detail']}</p></div>"
                )
            html_parts.extend(["</div>", "</div>"])

        html_parts.extend([
            "<div class='section'>",
            "<h2>Resumo Executivo por Módulo</h2>",
            "<div class='card'>",
            "<table>",
            "<thead><tr><th>Módulo</th><th>Releases</th><th>Correções</th><th>Melhorias</th><th>Tickets</th><th>Última versão</th></tr></thead>",
            "<tbody>",
        ])

        if report["module_summary"]:
            for module in report["module_summary"]:
                html_parts.append(
                    "<tr>"
                    f"<td>{module['module']}</td>"
                    f"<td>{module['releases']}</td>"
                    f"<td>{module['corrections']}</td>"
                    f"<td>{module['improvements']}</td>"
                    f"<td>{module['tickets']}</td>"
                    f"<td>{module['latest_version']}</td>"
                    "</tr>"
                )
        else:
            html_parts.append("<tr><td colspan='6'>Nenhum módulo encontrado.</td></tr>")

        html_parts.extend(["</tbody>", "</table>", "</div>", "</div>"])

        html_parts.extend([
            "<div class='section'>",
            "<h2>Temas Recorrentes</h2>",
            "<div>",
        ])
        if report["themes"]:
            for theme in report["themes"]:
                examples = f"Exemplos: {', '.join(theme['examples'])}" if theme.get("examples") else "Sem exemplos"
                html_parts.append(
                    f"<span class='pill pill-info'>{theme['theme']} ({theme['count']})</span><span class='muted'>{examples}</span><br/>"
                )
        else:
            html_parts.append("<p class='muted'>Nenhum tema recorrente identificado.</p>")
        html_parts.extend(["</div>", "</div>"])

        html_parts.extend([
            "<div class='section'>",
            "<h2>Inteligência Global de PDFs</h2>",
            f"<div class='card'><p class='muted'>Documentos processados: {report['pdf_totals'].get('documents', 0)} | Páginas: {report['pdf_totals'].get('pages', 0)} | Tickets detectados: {report['pdf_totals'].get('tickets', 0)}</p></div>",
            "<div class='grid grid-2'>",
        ])
        if report["pdf_highlights"]:
            for doc in report["pdf_highlights"][:6]:
                theme_list = ", ".join(theme.get("theme", "") for theme in doc.get("themes", [])[:3]) or "Sem tema"
                html_parts.append(
                    f"<div class='card'><strong>{doc.get('filename')}</strong><p class='muted'>{doc.get('scope_label') or doc.get('scope_type') or 'PDF'}</p><p>{theme_list}</p><p>{(doc.get('summary') or '')[:220]}</p></div>"
                )
        else:
            html_parts.append("<div class='card'><p class='muted'>Nenhum PDF processado.</p></div>")
        html_parts.extend([
            "</div>",
            "<div class='card' style='margin-top:16px;'>",
            "<h3>Temas globais dos PDFs</h3>",
        ])
        if report["pdf_themes"]:
            for theme in report["pdf_themes"][:8]:
                score = min(100, int((theme["count"] / max(report["pdf_themes"][0]["count"], 1)) * 100))
                html_parts.append(
                    f"<div style='margin:10px 0;'><div class='muted'>{theme['theme']} ({theme['count']})</div><div class='bar'><span style='width:{score}%'></span></div></div>"
                )
        else:
            html_parts.append("<p class='muted'>Nenhum tema global identificado.</p>")
        html_parts.extend(["</div>"])

        html_parts.extend([
            "<div class='card' style='margin-top:16px;'>",
            "<h3>Previsões Preditivas</h3>",
        ])
        if report["pdf_predictions"]:
            for prediction in report["pdf_predictions"][:6]:
                html_parts.append(
                    "<div style='margin: 12px 0; padding: 12px; border-radius: 14px; background: #f8fafc; border: 1px solid #e5e7eb;'>"
                    f"<strong>{prediction['title']}</strong>"
                    f"<p class='muted' style='margin:6px 0 0 0;'>{prediction['detail']}</p>"
                    f"<p style='margin:6px 0 0 0;'><span class='pill pill-info'>Confiança {prediction.get('confidence', 0)}%</span> <span class='muted'>{prediction.get('action', '')}</span></p>"
                    "</div>"
                )
        else:
            html_parts.append("<p class='muted'>Nenhuma previsão disponível.</p>")

        html_parts.extend(["</div>", "</div>"])

        html_parts.extend([
            "<div class='section'>",
            "<h2>Tickets e Soluções</h2>",
        ])
        if report["tickets"]:
            for ticket in report["tickets"]:
                badge_class = {
                    TIPO_CORRECAO_BUG: "pill-danger",
                    TIPO_NOVA_FUNCIONALIDADE: "pill-success",
                    TIPO_MELHORIA: "pill-info",
                }.get(ticket["tipo"], "pill-info")
                html_parts.extend([
                    "<div class='ticket'>",
                    f"<h4>{ticket['ticket']} <span class='pill {badge_class}'>{ticket['tipo_label']}</span> <span class='pill pill-info'>{ticket['status']}</span></h4>",
                    f"<p class='muted'><strong>Título:</strong> {ticket['title']}</p>",
                    f"<p><strong>Descrição:</strong> {ticket['descricao'] or 'N/A'}</p>",
                    f"<p><strong>Solução:</strong> {ticket['resolucao'] or 'N/A'}</p>",
                    f"<p class='muted'><strong>Módulo:</strong> {ticket['module']} | <strong>Release:</strong> {ticket['release']}</p>",
                    "</div>",
                ])
        else:
            html_parts.append("<p class='muted'>Nenhum ticket registrado.</p>")
        html_parts.extend(["</div>", "</body>", "</html>"])

        return "\n".join(html_parts)

    def get_tickets_by_type(self, tipo: str) -> List[Dict[str, Any]]:
        """Get all tickets of a specific type."""
        all_activities = list_atividade()
        return [a for a in all_activities if a.get("tipo") == tipo]

    def get_ticket_by_number(self, ticket: str) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by its number."""
        all_activities = list_atividade()
        for activity in all_activities:
            if activity.get("ticket", "").upper() == ticket.upper():
                return activity
        return None
