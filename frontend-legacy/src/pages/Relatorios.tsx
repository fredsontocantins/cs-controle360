import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { pdfIntelligenceApi, reportsApi, releaseApi } from '../services/api';
import { Button, Select, Card, TipoBadge, Badge, PdfProcessingCard, PdfIntelligencePanel, Input, Textarea, CycleTimelineCard } from '../components';


type Section = 'executivo' | 'inteligencia_pdf' | 'playbooks_insights' | 'performance' | 'modulos' | 'releases' | 'temas' | 'tickets' | 'auditoria';

type SectionFocus = {
  title: string;
  subtitle: string;
  badge: string;
  tone: string;
  primaryStatLabel: string;
  primaryStatValue: string;
  secondaryStatLabel?: string;
  secondaryStatValue?: string;
  bullets: string[];
  actionHint: string;
};

const MONTH_LABELS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function buildMonthOptions(yearOffset = 0) {
  const year = new Date().getFullYear() + yearOffset;
  return MONTH_LABELS.map((month) => ({ value: `${month}/${year}`, label: `${month}/${year}` }));
}

function getNextMonthLabel(value: string) {
  const [monthName, yearPart] = value.split('/');
  const monthIndex = MONTH_LABELS.indexOf(monthName);
  const year = Number(yearPart);
  if (monthIndex < 0 || Number.isNaN(year)) return '';
  const nextIndex = (monthIndex + 1) % 12;
  const nextYear = monthIndex === 11 ? year + 1 : year;
  return `${MONTH_LABELS[nextIndex]}/${nextYear}`;
}

function statusLabel(status: string) {
  return { backlog: 'Pendente', em_andamento: 'Em Andamento', em_revisao: 'Em Revisão', concluida: 'Concluída', bloqueada: 'Bloqueada' }[status] || status;
}

function severityVariant(severity: 'info' | 'warning' | 'success' | 'danger') {
  return { info: 'info' as const, warning: 'warning' as const, success: 'success' as const, danger: 'danger' as const }[severity];
}

export function Relatorios() {
  const queryClient = useQueryClient();
  const sectionFocusRef = useRef<HTMLDivElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedRelease, setSelectedRelease] = useState<string>(searchParams.get('release') ?? '');
  const [selectedCycleId, setSelectedCycleId] = useState<string>(searchParams.get('cycle') ?? '');
  const [activeSection, setActiveSection] = useState<Section>('executivo');
  const [focusedModuleName, setFocusedModuleName] = useState<string | null>(null);
  const [focusedReleaseId, setFocusedReleaseId] = useState<number | null>(null);
  const [focusedThemeName, setFocusedThemeName] = useState<string | null>(null);
  const [focusedTicketNumber, setFocusedTicketNumber] = useState<string | null>(null);
  const [textPreview, setTextPreview] = useState<string>('');
  const [isTextLoading, setIsTextLoading] = useState(false);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [closeCycleNotes, setCloseCycleNotes] = useState<string>('');
  const [closedPeriodLabel, setClosedPeriodLabel] = useState<string>('');
  const [nextPeriodLabel, setNextPeriodLabel] = useState<string>('');
  const [auditState, setAuditState] = useState<string>('todos');
  const [auditSearch, setAuditSearch] = useState<string>('');

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (selectedRelease) next.set('release', selectedRelease); else next.delete('release');
    if (selectedCycleId) next.set('cycle', selectedCycleId); else next.delete('cycle');
    if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true });
  }, [searchParams, selectedCycleId, selectedRelease, setSearchParams]);

  const { data: releases = [] } = useQuery({ queryKey: ['release'], queryFn: releaseApi.list });

  const { data: report, isLoading } = useQuery({
    queryKey: ['reports', 'ticket-summary', selectedRelease, selectedCycleId],
    queryFn: () => reportsApi.ticketSummary(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedCycleId ? Number(selectedCycleId) : undefined,
    ),
  });

  // ── NEW: Consolidated Intelligence query ──
  const { data: intelligence } = useQuery({
    queryKey: ['reports', 'intelligence', selectedRelease, selectedCycleId],
    queryFn: () => reportsApi.intelligence(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedCycleId ? Number(selectedCycleId) : undefined,
    ),
  });

  const { data: reportCycle } = useQuery({
    queryKey: ['report-cycle', selectedRelease],
    queryFn: () => reportsApi.cycle(selectedRelease ? Number(selectedRelease) : undefined),
  });

  const { data: availableCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles', selectedRelease],
    queryFn: () => reportsApi.cycles(selectedRelease ? Number(selectedRelease) : undefined),
  });

  const { data: cycleAudit } = useQuery({
    queryKey: ['pdf-intelligence', 'cycle-audit'],
    queryFn: pdfIntelligenceApi.cycleAudit,
  });

  const releaseOptions = [
    { value: '', label: 'Todos os releases' },
    ...releases.map((r) => ({ value: String(r.id), label: `${r.release_name || `Versão ${r.id}`} (${r.version})` })),
  ];
  const cycleOptions = useMemo(() => [
    { value: '', label: 'Histórico completo' },
    ...availableCycles.filter((cycle) => cycle.status === 'prestado').map((cycle) => ({
      value: String(cycle.id),
      label: `${cycle.period_label || `Prestação ${cycle.cycle_number || cycle.id}`} · ${cycle.status === 'prestado' ? 'fechado' : 'aberto'}`,
    })),
  ], [availableCycles]);
  const previousClosedCycleId = useMemo(() => {
    const closed = availableCycles.filter((c) => c.status === 'prestado');
    return closed.length ? String(closed[0].id) : '';
  }, [availableCycles]);
  const currentOpenCycleId = useMemo(() => {
    const open = availableCycles.find((c) => c.status === 'aberto') || (reportCycle?.cycle?.status === 'aberto' ? reportCycle.cycle : null);
    return open?.id ? String(open.id) : '';
  }, [availableCycles, reportCycle?.cycle]);
  const releaseRecordOptions = useMemo(
    () => releases.map((r) => ({ id: r.id, label: `${r.release_name || `Versão ${r.id}`} (${r.version})` })),
    [releases]
  );
  const monthOptions = useMemo(() => {
    return [{ value: '', label: 'Selecione um mês' }, ...buildMonthOptions(0), ...buildMonthOptions(1)];
  }, []);

  const auditItems = useMemo(() => {
    const normalize = (items: Array<{ filename?: string; scope_label?: string | null; audit_state?: string }>) => {
      return items.filter((item) => {
        const stateMatch = auditState === 'todos' || (item.audit_state || 'pending') === auditState;
        const search = auditSearch.trim().toLowerCase();
        const haystack = `${item.filename || ''} ${item.scope_label || ''} ${item.audit_state || ''}`.toLowerCase();
        return stateMatch && (!search || haystack.includes(search));
      });
    };
    return {
      already_read: normalize(cycleAudit?.already_read ?? []),
      new_documents: normalize(cycleAudit?.new_documents ?? []),
      changed_documents: normalize(cycleAudit?.changed_documents ?? []),
      legacy_documents: normalize(cycleAudit?.legacy_documents ?? []),
      pending_documents: normalize(cycleAudit?.pending_documents ?? []),
    };
  }, [auditSearch, auditState, cycleAudit]);

  const totals = report?.totals ?? {
    modules: report?.module_summary?.length ?? 0,
    releases: report?.release_summary?.length ?? 0,
    tickets: report?.total ?? 0,
    corrections: report?.by_type?.correcao_bug ?? 0,
    improvements: report?.by_type?.melhoria ?? 0,
    features: report?.by_type?.nova_funcionalidade ?? 0,
  };

  // Intelligence shortcuts
  const pdfIntel = intelligence?.pdf_intelligence;
  const playbookIntel = intelligence?.playbooks;
  const crossModule = intelligence?.cross_module;

  const handleGenerateText = async (focus = reportFocus) => {
    setIsTextLoading(true);
    try {
      const result = await reportsApi.summaryText(
        selectedRelease ? Number(selectedRelease) : undefined,
        selectedCycleId ? Number(selectedCycleId) : undefined,
        focus ?? undefined,
      );
      setTextPreview(result.report);
      setActiveSection('executivo');
    } finally { setIsTextLoading(false); }
  };

  const handleOpenHtml = async (focus = reportFocus) => {
    const result = await reportsApi.htmlReport(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedRelease ? releases.find((r) => r.id === Number(selectedRelease))?.release_name : undefined,
      selectedCycleId ? Number(selectedCycleId) : undefined,
      focus ?? undefined,
    );
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const handleExportPdf = async (focus = reportFocus) => {
    setIsPdfLoading(true);
    try {
      const blob = await reportsApi.pdfReport(
        selectedRelease ? Number(selectedRelease) : undefined,
        selectedRelease ? releases.find((r) => r.id === Number(selectedRelease))?.release_name : undefined,
        selectedCycleId ? Number(selectedCycleId) : undefined,
        focus ?? undefined,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = selectedRelease ? `relatorio-gerencial-${selectedRelease}.pdf` : 'relatorio-gerencial.pdf';
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    } finally { setIsPdfLoading(false); }
  };

  const clearReportScreen = () => {
    setSelectedRelease(''); setSelectedCycleId(''); setActiveSection('executivo');
    setFocusedModuleName(null); setFocusedReleaseId(null); setFocusedThemeName(null); setFocusedTicketNumber(null);
    setTextPreview(''); setClosedPeriodLabel(''); setNextPeriodLabel(''); setAuditState('todos'); setAuditSearch('');
  };

  const handleClosedMonthChange = (value: string) => {
    setClosedPeriodLabel(value);
    const suggested = getNextMonthLabel(value);
    if (suggested) setNextPeriodLabel(suggested);
  };

  const closeCycleMutation = useMutation({
    mutationFn: (payload: { reopenNew: boolean; notes?: string }) => reportsApi.closeCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      reopenNew: payload.reopenNew, notes: payload.notes,
      scopeLabel: selectedRelease ? releases.find((r) => r.id === Number(selectedRelease))?.release_name : undefined,
      closedPeriodLabel: closedPeriodLabel.trim() || undefined, nextPeriodLabel: nextPeriodLabel.trim() || undefined,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['report-cycle'] }),
        queryClient.invalidateQueries({ queryKey: ['reports'] }),
        queryClient.invalidateQueries({ queryKey: ['pdf-intelligence'] }),
      ]);
      clearReportScreen(); setCloseCycleNotes('');
    },
  });

  const openCycleMutation = useMutation({
    mutationFn: () => reportsApi.openCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      scopeLabel: selectedRelease ? releases.find((r) => r.id === Number(selectedRelease))?.release_name : undefined,
      periodLabel: nextPeriodLabel.trim() || undefined,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['report-cycle'] }),
        queryClient.invalidateQueries({ queryKey: ['reports'] }),
        queryClient.invalidateQueries({ queryKey: ['pdf-intelligence'] }),
      ]);
      clearReportScreen();
    },
  });

  const focusModules = report?.module_summary ?? [];
  const focusReleases = report?.release_summary ?? [];
  const focusThemes = report?.themes ?? [];
  const focusTickets = report?.tickets ?? [];
  const insights = report?.insights ?? [];
  const pdfSections = report?.pdf_context?.sections ?? [];
  const pdfKnowledgeTerms = report?.pdf_context?.knowledge_terms ?? [];
  const pdfProblemSolutions = report?.pdf_context?.problem_solution_examples ?? [];

  const focusedModule = useMemo(() => focusModules.find((m) => m.module === focusedModuleName) ?? null, [focusModules, focusedModuleName]);
  const focusedRelease = useMemo(() => focusReleases.find((r) => r.id === focusedReleaseId) ?? null, [focusReleases, focusedReleaseId]);
  const focusedTheme = useMemo(() => focusThemes.find((t) => t.theme === focusedThemeName) ?? null, [focusThemes, focusedThemeName]);
  const focusedTicket = useMemo(() => focusTickets.find((t) => t.ticket === focusedTicketNumber) ?? null, [focusTickets, focusedTicketNumber]);

  const reportFocus = useMemo(() => {
    if (focusedModuleName) return { type: 'module', value: focusedModuleName, label: `Módulo: ${focusedModuleName}` };
    if (focusedRelease) return { type: 'release', value: String(focusedRelease.id), label: `Versão: ${focusedRelease.release_name} (${focusedRelease.version})` };
    if (focusedThemeName) return { type: 'theme', value: focusedThemeName, label: `Tema: ${focusedThemeName}` };
    if (focusedTicketNumber) return { type: 'ticket', value: focusedTicketNumber, label: `Ticket: ${focusedTicketNumber}` };
    return null;
  }, [focusedModuleName, focusedRelease, focusedThemeName, focusedTicketNumber]);

  const modulesWithoutPdf = useMemo(() => focusModules.filter((m) => (m.pdf_documents ?? 0) === 0), [focusModules]);
  const topVolumeModules = useMemo(() => [...focusModules].sort((a, b) => b.tickets - a.tickets).slice(0, 3), [focusModules]);
  const statusDistribution = useMemo(() => {
    return Object.entries(report?.by_status ?? {}).map(([s, v]) => ({ label: statusLabel(s), value: v, status: s })).sort((a, b) => b.value - a.value);
  }, [report?.by_status]);

  useEffect(() => { sectionFocusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, [activeSection]);
  useEffect(() => { if (focusedModuleName && !focusedModule) setFocusedModuleName(null); }, [focusedModule, focusedModuleName]);
  useEffect(() => { if (focusedReleaseId && !focusedRelease) setFocusedReleaseId(null); }, [focusedRelease, focusedReleaseId]);
  useEffect(() => { if (focusedThemeName && !focusedTheme) setFocusedThemeName(null); }, [focusedTheme, focusedThemeName]);
  useEffect(() => { if (focusedTicketNumber && !focusedTicket) setFocusedTicketNumber(null); }, [focusedTicket, focusedTicketNumber]);

  const sectionFocus = useMemo<SectionFocus>(() => {
    switch (activeSection) {
      case 'inteligencia_pdf':
        return {
          title: 'Inteligência de PDFs', subtitle: 'Temas, seções, termos e previsões extraídos localmente da base documental.',
          badge: 'PDF Intelligence', tone: 'border-indigo-400 bg-indigo-50',
          primaryStatLabel: 'Documentos do ciclo', primaryStatValue: `${pdfIntel?.cycle_documents ?? 0}`,
          secondaryStatLabel: 'Temas detectados', secondaryStatValue: `${(pdfIntel?.themes ?? []).length}`,
          bullets: [
            (pdfIntel?.predictions ?? []).length > 0 ? `${pdfIntel!.predictions.length} previsão(ões) preditiva(s) calculadas.` : 'Sem previsões calculadas.',
            (pdfIntel?.recommendations ?? []).length > 0 ? pdfIntel!.recommendations[0] : 'Sem recomendações.',
            (pdfIntel?.action_items ?? []).length > 0 ? pdfIntel!.action_items[0] : 'Sem itens de ação.',
          ],
          actionHint: 'Tudo calculado localmente sem chamadas externas de IA.',
        };
      case 'playbooks_insights':
        return {
          title: 'Guias e Recomendações', subtitle: 'Cobertura de processos, erros e ações preditivas consolidadas dos playbooks.',
          badge: 'Playbook Intelligence', tone: 'border-amber-400 bg-amber-50',
          primaryStatLabel: 'Guias ativos', primaryStatValue: `${playbookIntel?.totals?.playbooks ?? 0}`,
          secondaryStatLabel: 'Guias preditivos', secondaryStatValue: `${playbookIntel?.totals?.predictions ?? 0}`,
          bullets: [
            (playbookIntel?.ranking ?? []).length > 0 ? `Top risco: ${playbookIntel!.ranking[0]?.erro || 'N/A'}.` : 'Sem ranking de risco.',
            (playbookIntel?.coverage?.areas_sem_documentacao ?? []).length > 0 ? `${playbookIntel!.coverage.areas_sem_documentacao.length} área(s) sem documentação.` : 'Cobertura completa.',
            (playbookIntel?.suggestions ?? []).length > 0 ? playbookIntel!.suggestions[0] : 'Sem sugestões automáticas.',
          ],
          actionHint: 'Use as sugestões para criar novos guias e fechar lacunas de conhecimento.',
        };
      case 'performance':
        return {
          title: 'Performance operacional', subtitle: 'Distribuição por status, módulo e tendência por release.',
          badge: 'Medição operacional', tone: 'border-[#184e77] bg-[#f3f8fc]',
          primaryStatLabel: 'Status dominante', primaryStatValue: statusDistribution[0] ? `${statusDistribution[0].label} (${statusDistribution[0].value})` : 'Sem dados',
          secondaryStatLabel: 'Módulo mais pressionado', secondaryStatValue: report?.top_module ? `${report.top_module.module} (${report.top_module.tickets})` : 'Sem dados',
          bullets: [
            report?.top_module ? `${report.top_module.module} concentra ${report.top_module.share}% do total.` : 'Sem módulo concentrado.',
            statusDistribution.length > 0 ? `${statusDistribution[0].label} lidera a fila.` : 'Sem distribuição de status.',
            `${totals.tickets} tickets no recorte atual.`,
          ],
          actionHint: 'Use esta aba para medir gargalos e priorizar correções.',
        };
      case 'executivo':
      default:
        return {
          title: 'Foco executivo', subtitle: 'Síntese da prestação de contas com os indicadores que mais importam.',
          badge: 'Resumo geral', tone: 'border-[#0d3b66] bg-[#eef6ff]',
          primaryStatLabel: 'Tickets totais', primaryStatValue: `${totals.tickets}`,
          secondaryStatLabel: 'Módulos', secondaryStatValue: `${crossModule?.totals?.modulos ?? totals.modules}`,
          bullets: [
            report?.top_module ? `${report.top_module.module} é o módulo dominante.` : 'Sem módulo dominante.',
            insights[0] ? `${insights[0].title}: ${insights[0].detail}` : 'Sem insight adicional.',
            pdfSections.length > 0 ? `A inteligência de PDF trouxe ${pdfSections.length} seção(ões) semântica(s).` : 'Nenhuma seção de PDF consolidada.',
          ],
          actionHint: 'Navegue pelas abas para explorar cada dimensão da inteligência.',
        };
    }
  }, [activeSection, pdfIntel, playbookIntel, crossModule, statusDistribution, report, totals, insights, pdfSections.length]);

  const clearFocusedContext = () => { setFocusedModuleName(null); setFocusedReleaseId(null); setFocusedThemeName(null); setFocusedTicketNumber(null); };

  const SECTIONS: { key: Section; label: string }[] = [
    { key: 'executivo', label: 'Executivo' },
    { key: 'inteligencia_pdf', label: '📄 PDF Intelligence' },
    { key: 'playbooks_insights', label: '📘 Guias' },
    { key: 'performance', label: 'Performance' },
    { key: 'modulos', label: 'Módulos' },
    { key: 'releases', label: 'Versões' },
    { key: 'temas', label: 'Temas' },
    { key: 'tickets', label: 'Tickets' },
    { key: 'auditoria', label: 'Auditoria' },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Hero */}
      <div className="rounded-3xl bg-gradient-to-br from-[#0d3b66] via-[#184e77] to-[#1d5c85] p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.35em] text-white/70">Centro de Inteligência</p>
            <h1 className="mt-2 text-3xl font-bold">Relatórios com inteligência consolidada</h1>
            <p className="mt-3 text-white/85">Hub de inteligência local: PDF, playbooks e métricas de todos os módulos em um único lugar.</p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => { if (currentOpenCycleId) { setSelectedCycleId(currentOpenCycleId); setSelectedRelease(''); } }} disabled={!currentOpenCycleId}>Mês vigente</Button>
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => { setSelectedCycleId(''); setSelectedRelease(''); }}>Histórico completo</Button>
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => handleGenerateText()} disabled={isTextLoading}>{isTextLoading ? 'Gerando...' : 'Gerar texto'}</Button>
            <Button type="button" variant="secondary" onClick={() => handleOpenHtml()}>HTML</Button>
            <Button type="button" variant="secondary" onClick={() => handleExportPdf()} disabled={isPdfLoading}>{isPdfLoading ? 'Exportando...' : 'PDF'}</Button>
          </div>
        </div>
        {reportFocus && (
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
            <Badge variant="info">{reportFocus.label}</Badge>
            <span className="text-sm text-white/80">Relatório pode ser exportado com este foco.</span>
            <Button type="button" size="sm" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => handleGenerateText(reportFocus)}>Texto</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => handleOpenHtml(reportFocus)}>HTML</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => handleExportPdf(reportFocus)} disabled={isPdfLoading}>PDF</Button>
            <Button type="button" size="sm" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={clearFocusedContext}>Limpar foco</Button>
          </div>
        )}
      </div>

      {/* Filters + section tabs */}
      <Card>
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex gap-4">
            <div className="w-full max-w-xs"><Select label="Versão" options={releaseOptions} value={selectedRelease} onChange={(e) => { setSelectedRelease(e.target.value); setSelectedCycleId(''); }} /></div>
            <div className="w-full max-w-xs"><Select label="Ciclo fechado" options={cycleOptions} value={selectedCycleId} onChange={(e) => setSelectedCycleId(e.target.value)} /></div>
          </div>
          <div className="flex flex-wrap gap-2">
            {SECTIONS.map((s) => (
              <Button key={s.key} type="button" size="sm" variant={activeSection === s.key ? 'primary' : 'outline'} className={activeSection === s.key ? 'shadow-lg shadow-[#0d3b66]/20' : ''} onClick={() => setActiveSection(s.key)} aria-pressed={activeSection === s.key}>{s.label}</Button>
            ))}
          </div>
        </div>
      </Card>

      {/* Timeline */}
      <CycleTimelineCard title="Linha do tempo da prestação" description="A prestação aberta concentra os dados do mês em trabalho." currentCycle={reportCycle?.cycle ?? availableCycles.find((c) => c.status === 'aberto') ?? null} previousCycle={availableCycles.find((c) => c.status === 'prestado') ?? null} cycles={availableCycles} selectedCycleId={selectedCycleId} onSelectCycle={(id) => { setSelectedCycleId(id); setActiveSection('executivo'); }} onOpenPrevious={() => { if (previousClosedCycleId) { setSelectedCycleId(previousClosedCycleId); setActiveSection('executivo'); } }} onOpenCurrent={() => { setSelectedCycleId(''); setActiveSection('executivo'); }} />

      <PdfProcessingCard scopeType="release" scopeLabel="Relatórios" scopeId={selectedRelease ? Number(selectedRelease) : null} recordOptions={releaseRecordOptions} />

      {/* Section focus card */}
      <div ref={sectionFocusRef}>
        <Card className={`border-l-4 ${sectionFocus.tone}`}>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2"><Badge variant="info">{sectionFocus.badge}</Badge><span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Seção ativa</span></div>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900">{sectionFocus.title}</h2>
              <p className="mt-2 text-sm text-gray-600">{sectionFocus.subtitle}</p>
              <p className="mt-3 text-sm font-medium text-[#0d3b66]">{sectionFocus.actionHint}</p>
            </div>
            <div className="grid w-full gap-3 sm:grid-cols-2 lg:max-w-xl">
              <div className="rounded-2xl bg-white px-4 py-3 shadow-sm"><p className="text-[11px] uppercase tracking-wider text-gray-500">{sectionFocus.primaryStatLabel}</p><p className="mt-1 text-base font-semibold text-gray-900">{sectionFocus.primaryStatValue}</p></div>
              {sectionFocus.secondaryStatLabel && (<div className="rounded-2xl bg-white px-4 py-3 shadow-sm"><p className="text-[11px] uppercase tracking-wider text-gray-500">{sectionFocus.secondaryStatLabel}</p><p className="mt-1 text-base font-semibold text-gray-900">{sectionFocus.secondaryStatValue}</p></div>)}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {sectionFocus.bullets.map((b, i) => (<div key={`${sectionFocus.title}-${i}`} className="rounded-2xl border border-white/80 bg-white/90 px-4 py-3 shadow-sm"><p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Inteligência {i + 1}</p><p className="mt-1 text-sm text-gray-700">{b}</p></div>))}
          </div>
        </Card>
      </div>

      {/* ── SECTION: PDF Intelligence (NEW) ── */}
      {activeSection === 'inteligencia_pdf' && (
        <div className="space-y-6">
          {/* Predictions */}
          {(pdfIntel?.predictions ?? []).length > 0 && (
            <Card title="Previsões Preditivas Locais">
              <p className="text-sm text-gray-500 mb-4">Previsões calculadas a partir dos PDFs sem chamadas externas.</p>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {pdfIntel!.predictions.map((p) => (
                  <div key={p.title} className={`rounded-2xl border p-4 ${p.confidence >= 80 ? 'border-red-200 bg-red-50' : p.confidence >= 60 ? 'border-amber-200 bg-amber-50' : 'border-sky-200 bg-sky-50'}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div><p className="text-sm font-medium text-gray-900">{p.title}</p><p className="mt-1 text-xs text-gray-500">{p.detail}</p></div>
                      <Badge variant={p.confidence >= 80 ? 'danger' : p.confidence >= 60 ? 'warning' : 'info'}>{p.confidence}%</Badge>
                    </div>
                    <p className="mt-3 text-xs text-gray-600">{p.action}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Themes, Sections, Terms */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Temas dos PDFs">
              <div className="flex flex-wrap gap-2">
                {(pdfIntel?.themes ?? []).length > 0 ? pdfIntel!.themes.slice(0, 12).map((t) => (<Badge key={t.theme} variant="info">{t.theme} ({t.count})</Badge>)) : <span className="text-sm text-gray-500">Sem temas.</span>}
              </div>
            </Card>
            <Card title="Seções Semânticas">
              <div className="flex flex-wrap gap-2">
                {(pdfIntel?.sections ?? []).length > 0 ? pdfIntel!.sections!.slice(0, 10).map((s) => (<Badge key={s.section} variant="warning">{s.section} ({s.count})</Badge>)) : <span className="text-sm text-gray-500">Sem seções.</span>}
              </div>
            </Card>
            <Card title="Termos de Conhecimento">
              <div className="flex flex-wrap gap-2">
                {(pdfIntel?.knowledge_terms ?? []).length > 0 ? pdfIntel!.knowledge_terms!.slice(0, 12).map((t) => (<Badge key={t.term} variant="default">{t.term} ({t.count})</Badge>)) : <span className="text-sm text-gray-500">Sem termos.</span>}
              </div>
            </Card>
          </div>

          {/* Problem-solution pairs */}
          {(pdfIntel?.problem_solution_examples ?? []).length > 0 && (
            <Card title="Pares Problema / Solução">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {pdfIntel!.problem_solution_examples!.slice(0, 6).map((ps, i) => (
                  <div key={`ps-${i}`} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                    <p className="text-sm font-medium text-gray-900">{ps.filename || 'PDF'}</p>
                    <p className="mt-1 text-xs text-gray-500">Problema: {ps.problem || 'N/A'}</p>
                    <p className="mt-1 text-xs text-gray-700">Solução: {ps.solution || 'N/A'}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Recommendations + Action items */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Recomendações"><ul className="space-y-2 text-sm text-gray-700">{(pdfIntel?.recommendations ?? []).map((r) => (<li key={r}>• {r}</li>))}</ul>{(pdfIntel?.recommendations ?? []).length === 0 && <p className="text-sm text-gray-500">Sem recomendações.</p>}</Card>
            <Card title="Itens de Ação"><ul className="space-y-2 text-sm text-gray-700">{(pdfIntel?.action_items ?? []).map((a) => (<li key={a}>• {a}</li>))}</ul>{(pdfIntel?.action_items ?? []).length === 0 && <p className="text-sm text-gray-500">Sem itens de ação.</p>}</Card>
          </div>

          <PdfIntelligencePanel scopeType="release" scopeLabel="Relatórios Gerenciais" scopeId={selectedRelease ? Number(selectedRelease) : null} recordOptions={releaseRecordOptions} />
        </div>
      )}

      {/* ── SECTION: Playbook Insights (NEW) ── */}
      {activeSection === 'playbooks_insights' && (
        <div className="space-y-6">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-6">
            <MetricCard title="Guias totais" value={playbookIntel?.totals?.playbooks ?? 0} tone="bg-[#0d3b66]" />
            <MetricCard title="Manuais" value={playbookIntel?.totals?.manual ?? 0} tone="bg-emerald-600" />
            <MetricCard title="Por erros" value={playbookIntel?.totals?.errors ?? 0} tone="bg-red-600" />
            <MetricCard title="Por release" value={playbookIntel?.totals?.releases ?? 0} tone="bg-blue-600" />
            <MetricCard title="Preditivos" value={playbookIntel?.totals?.predictions ?? 0} tone="bg-violet-600" />
            <MetricCard title="Cobertura" value={`${playbookIntel?.coverage?.processos ?? 0}%`} tone="bg-amber-600" />
          </div>

          {/* Risk ranking */}
          {(playbookIntel?.ranking ?? []).length > 0 && (
            <Card title="Ranking de Risco">
              <div className="space-y-3">
                {playbookIntel!.ranking.slice(0, 8).map((item) => (
                  <div key={item.erro} className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 bg-gray-50 p-3">
                    <div><p className="text-sm font-medium text-gray-900">{item.erro}</p><p className="text-xs text-gray-500">Score {item.score} | Impacto {item.impacto} | Freq. {item.frequencia}</p></div>
                    <Badge variant={item.playbook_criado === 'Sim' ? 'success' : 'warning'}>{item.playbook_criado === 'Sim' ? 'Coberto' : 'Pendente'}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Coverage gaps + Suggestions */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Áreas sem documentação">
              <div className="flex flex-wrap gap-2">
                {(playbookIntel?.coverage?.areas_sem_documentacao ?? []).length > 0 ? playbookIntel!.coverage.areas_sem_documentacao.map((a) => (<Badge key={a} variant="warning">{a}</Badge>)) : <span className="text-sm text-gray-500">Cobertura completa.</span>}
              </div>
            </Card>
            <Card title="Sugestões automáticas">
              <ul className="space-y-2 text-sm text-gray-700">{(playbookIntel?.suggestions ?? []).map((s) => (<li key={s}>• {s}</li>))}</ul>
              {(playbookIntel?.suggestions ?? []).length === 0 && <p className="text-sm text-gray-500">Sem sugestões.</p>}
            </Card>
          </div>

          {/* Effectiveness */}
          {playbookIntel?.effectiveness && (
            <Card title="Eficácia dos Guias">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MiniStat label="Taxa de redução" value={`${playbookIntel.effectiveness.reduction_rate}%`} />
                <MiniStat label="Tempo médio" value={playbookIntel.effectiveness.avg_execution_time} />
                <MiniStat label="Taxa de adoção" value={playbookIntel.effectiveness.adoption_rate} />
                <MiniStat label="Cobertura processos" value={`${playbookIntel.effectiveness.coverage_processos}%`} />
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── SECTION: Executivo ── */}
      {!isLoading && report && activeSection === 'executivo' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
            <MetricCard title="Versões" value={totals.releases} tone="bg-[#0d3b66]" />
            <MetricCard title="Módulos" value={totals.modules} tone="bg-slate-800" />
            <MetricCard title="Tickets" value={totals.tickets} tone="bg-emerald-600" />
            <MetricCard title="Correções" value={totals.corrections} tone="bg-red-600" />
            <MetricCard title="Melhorias" value={totals.improvements} tone="bg-blue-600" />
            <MetricCard title="Funcionalidades" value={totals.features} tone="bg-violet-600" />
          </div>

          {/* Cross-module totals from intelligence */}
          {crossModule && (
            <Card title="Visão consolidada de todos os módulos">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <MiniStat label="Homologações" value={crossModule.totals.homologacoes} />
                <MiniStat label="Customizações" value={crossModule.totals.customizacoes} />
                <MiniStat label="Atividades" value={crossModule.totals.atividades} />
                <MiniStat label="Releases" value={crossModule.totals.releases} />
                <MiniStat label="Módulos" value={crossModule.totals.modulos} />
                <MiniStat label="Clientes" value={crossModule.totals.clientes} />
              </div>
              {crossModule.module_metrics.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full"><thead><tr className="border-b border-gray-200">
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Módulo</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Homol.</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Custom.</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Ativid.</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Releases</th>
                  </tr></thead><tbody className="divide-y divide-gray-100">
                    {crossModule.module_metrics.slice(0, 10).map((m) => (
                      <tr key={m.name}><td className="px-3 py-2 text-sm font-medium text-gray-900">{m.name}</td><td className="px-3 py-2 text-sm text-gray-700">{m.homologacoes}</td><td className="px-3 py-2 text-sm text-gray-700">{m.customizacoes}</td><td className="px-3 py-2 text-sm text-gray-700">{m.atividades}</td><td className="px-3 py-2 text-sm text-gray-700">{m.releases}</td></tr>
                    ))}
                  </tbody></table>
                </div>
              )}
            </Card>
          )}

          {report.top_module && (
            <Card>
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div><p className="text-sm uppercase tracking-wider text-gray-500">Concentração de demanda</p><h2 className="text-xl font-semibold text-gray-900">{report.top_module.module}</h2></div>
                <div className="flex flex-wrap items-center gap-2"><Badge variant="warning">{report.top_module.share}% do total</Badge><Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(report.top_module?.module || null); setActiveSection('modulos'); }}>Focar módulo</Button></div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4"><MiniStat label="Tickets" value={report.top_module.tickets} /><MiniStat label="Versões" value={report.top_module.releases} /><MiniStat label="Última versão" value={report.top_module.latest_version} /><MiniStat label="Última release" value={report.top_module.latest_release} /></div>
            </Card>
          )}

          {insights.length > 0 && (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {insights.map((ins) => (<Card key={ins.title} className="h-full"><div className="flex items-center justify-between gap-3"><h3 className="text-lg font-semibold text-gray-900">{ins.title}</h3><Badge variant={severityVariant(ins.severity)}>{ins.severity}</Badge></div><p className="mt-3 text-sm text-gray-600">{ins.detail}</p></Card>))}
            </div>
          )}

          {(pdfSections.length > 0 || pdfKnowledgeTerms.length > 0 || pdfProblemSolutions.length > 0) && (
            <Card>
              <h2 className="text-xl font-semibold text-gray-900">Conhecimento extraído dos PDFs</h2>
              <p className="text-sm text-gray-500">Seções, termos e pares problema/solução.</p>
              <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
                <div><h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Seções</h3><div className="mt-3 flex flex-wrap gap-2">{pdfSections.length > 0 ? pdfSections.slice(0, 8).map((s) => (<Badge key={s.section} variant="info">{s.section} ({s.count})</Badge>)) : <span className="text-sm text-gray-500">Sem seções.</span>}</div></div>
                <div><h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Termos</h3><div className="mt-3 flex flex-wrap gap-2">{pdfKnowledgeTerms.length > 0 ? pdfKnowledgeTerms.slice(0, 10).map((t) => (<Badge key={t.term} variant="warning">{t.term} ({t.count})</Badge>)) : <span className="text-sm text-gray-500">Sem termos.</span>}</div></div>
                <div><h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Problema / Solução</h3><div className="mt-3 space-y-2">{pdfProblemSolutions.length > 0 ? pdfProblemSolutions.slice(0, 3).map((ps, i) => (<div key={`exec-ps-${i}`} className="rounded-xl border border-gray-200 bg-gray-50 p-3"><p className="text-sm font-medium text-gray-900">{ps.filename || 'PDF'}</p><p className="mt-1 text-xs text-gray-500">{ps.problem || 'N/A'}</p><p className="mt-1 text-xs text-gray-700">{ps.solution || 'N/A'}</p></div>)) : <span className="text-sm text-gray-500">Sem pares.</span>}</div></div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── SECTION: Performance ── */}
      {!isLoading && report && activeSection === 'performance' && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-1"><h2 className="text-xl font-semibold text-gray-900">Distribuição por status</h2><div className="mt-4 space-y-3">{statusDistribution.length > 0 ? statusDistribution.map((item) => (<BarRow key={item.status} label={item.label} value={item.value} total={totals.tickets || 1} />)) : <p className="text-sm text-gray-500">Sem dados.</p>}</div></Card>
          <Card className="xl:col-span-1"><h2 className="text-xl font-semibold text-gray-900">Concentração por módulo</h2><div className="mt-4 space-y-3">{focusModules.slice(0, 6).map((m) => (<button key={m.module} type="button" className="block w-full rounded-2xl border border-transparent text-left transition hover:border-[#0d3b66]/20 hover:bg-[#f7fbff]" onClick={() => { setFocusedModuleName(m.module); setActiveSection('modulos'); }}><BarRow label={m.module} value={m.tickets} total={totals.tickets || 1} suffix={`${m.share}%`} /></button>))}</div></Card>
          <Card className="xl:col-span-1"><h2 className="text-xl font-semibold text-gray-900">Tendência por release</h2><div className="mt-4 space-y-3">{focusReleases.slice(-8).map((r) => (<button key={r.id} type="button" className="block w-full rounded-2xl border border-transparent text-left transition hover:border-[#0d3b66]/20 hover:bg-[#f7fbff]" onClick={() => { setFocusedReleaseId(r.id); setActiveSection('releases'); }}><BarRow label={r.release_name} value={r.tickets} total={Math.max(...focusReleases.map((x) => x.tickets), 1)} suffix={r.applies_on ? r.applies_on.slice(0, 10) : '---'} /></button>))}</div></Card>
        </div>
      )}

      {/* ── SECTION: Módulos ── */}
      {!isLoading && report && activeSection === 'modulos' && (
        <div className="space-y-4">
          <Card><h2 className="text-xl font-semibold text-gray-900">Resumo por Módulo</h2>
            <div className="mt-4 overflow-x-auto"><table className="w-full"><thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Módulo</th><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Versões</th><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Correções</th><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Melhorias</th><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Tickets</th><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">PDFs</th></tr></thead><tbody className="divide-y divide-gray-100">
              {focusModules.map((m) => (<tr key={m.module} className={report.top_module?.module === m.module ? 'bg-amber-50/60' : ''}><td className="px-4 py-3 font-medium text-gray-900">{m.module}</td><td className="px-4 py-3 text-sm text-gray-700">{m.releases}</td><td className="px-4 py-3 text-sm text-gray-700">{m.corrections}</td><td className="px-4 py-3 text-sm text-gray-700">{m.improvements}</td><td className="px-4 py-3 text-sm text-gray-700">{m.tickets}</td><td className="px-4 py-3 text-sm text-gray-700">{m.pdf_documents ?? 0}</td></tr>))}
              {focusModules.length === 0 && (<tr><td className="px-4 py-8 text-center text-sm text-gray-500" colSpan={6}>Nenhum módulo encontrado.</td></tr>)}
            </tbody></table></div>
          </Card>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Módulos sem PDF">{modulesWithoutPdf.length > 0 ? <ul className="space-y-2 text-sm text-gray-700">{modulesWithoutPdf.map((m) => (<li key={m.module} className="flex items-center justify-between gap-3"><strong>{m.module}</strong> - {m.tickets} ticket(s)<Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(m.module); }}>Focar</Button></li>))}</ul> : <p className="text-sm text-gray-500">Todos com PDF.</p>}</Card>
            <Card title="Maior volume">{topVolumeModules.length > 0 ? <ul className="space-y-2 text-sm text-gray-700">{topVolumeModules.map((m) => (<li key={m.module}><strong>{m.module}</strong> - {m.tickets} ticket(s)</li>))}</ul> : <p className="text-sm text-gray-500">Sem dados.</p>}</Card>
            <Card title="Temas recorrentes por módulo">{focusModules.filter((m) => (m.themes ?? []).length > 0).slice(0, 3).map((m) => (<div key={m.module} className="mb-2"><p className="text-sm font-semibold text-gray-900">{m.module}</p><div className="flex flex-wrap gap-1 mt-1">{(m.themes ?? []).slice(0, 3).map((t) => (<Badge key={t.theme} variant="info">{t.theme} ({t.count})</Badge>))}</div></div>))}{focusModules.filter((m) => (m.themes ?? []).length > 0).length === 0 && <p className="text-sm text-gray-500">Sem temas.</p>}</Card>
          </div>
        </div>
      )}

      {/* ── SECTION: Versões ── */}
      {!isLoading && report && activeSection === 'releases' && (
        <div className="space-y-4"><Card><h2 className="text-xl font-semibold text-gray-900">Visão por Versão</h2></Card>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {focusReleases.map((r) => (<Card key={r.id} className={r.tickets > 0 ? 'border-l-4 border-l-[#0d3b66]' : ''}>
              <div className="flex items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-gray-500">{r.module}</p><h3 className="text-lg font-semibold text-gray-900">{r.release_name}</h3><p className="text-sm text-gray-500">Versão {r.version}</p></div><Badge variant={r.tickets > 0 ? 'warning' : 'default'}>{r.tickets} tickets</Badge></div>
              <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4"><MiniStat label="Correções" value={r.corrections} /><MiniStat label="Melhorias" value={r.improvements} /><MiniStat label="Última atividade" value={r.last_activity_at ? r.last_activity_at.slice(0, 10) : '---'} /><MiniStat label="Aplicada em" value={r.applies_on ? r.applies_on.slice(0, 10) : '---'} /></div>
            </Card>))}
            {focusReleases.length === 0 && <Card><p className="text-sm text-gray-500">Nenhum release encontrado.</p></Card>}
          </div>
        </div>
      )}

      {/* ── SECTION: Temas ── */}
      {!isLoading && report && activeSection === 'temas' && (
        <Card><h2 className="text-xl font-semibold text-gray-900">Temas Recorrentes</h2><div className="mt-4 flex flex-wrap gap-3">
          {focusThemes.map((t) => (<div key={t.theme} className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3"><div className="flex items-center gap-2"><Badge variant="info">{t.count}</Badge><span className="font-medium text-gray-900">{t.theme}</span></div>{t.examples.length > 0 && <p className="mt-2 text-xs text-gray-500">Exemplos: {t.examples.join(', ')}</p>}</div>))}
          {focusThemes.length === 0 && <p className="text-sm text-gray-500">Nenhum tema recorrente.</p>}
        </div></Card>
      )}

      {/* ── SECTION: Tickets ── */}
      {!isLoading && report && activeSection === 'tickets' && (
        <div className="space-y-4"><Card><h2 className="text-xl font-semibold text-gray-900">Tickets e Soluções</h2></Card>
          {focusTickets.map((t) => (<Card key={`${t.ticket}-${t.release_id ?? 'na'}`}>
            <div className="flex items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-gray-500">{t.module || 'Sem módulo'}</p><h3 className="text-lg font-semibold text-gray-900">{t.ticket}</h3></div><div className="flex flex-wrap gap-2">{t.status && <Badge variant="info">{t.status}</Badge>}<TipoBadge tipo={t.tipo} /></div></div>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2"><div><p className="text-sm font-semibold text-gray-500">Problema</p><p className="mt-1 text-sm text-gray-900">{t.descricao || 'N/A'}</p></div><div><p className="text-sm font-semibold text-gray-500">Solução</p><p className="mt-1 text-sm text-gray-900">{t.resolucao || 'N/A'}</p></div></div>
          </Card>))}
          {focusTickets.length === 0 && <p className="text-center text-sm text-gray-500">Nenhum ticket encontrado.</p>}
        </div>
      )}

      {/* ── SECTION: Auditoria ── */}
      {activeSection === 'auditoria' && (
        <Card><h2 className="text-xl font-semibold text-gray-900">Auditoria de leitura de PDFs</h2>
          <div className="mt-4 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
            <MiniAudit label="Já lidos" value={cycleAudit?.counts.already_read ?? 0} /><MiniAudit label="Novos" value={cycleAudit?.counts.new ?? 0} /><MiniAudit label="Alterados" value={cycleAudit?.counts.changed ?? 0} /><MiniAudit label="Pendentes" value={cycleAudit?.counts.pending ?? 0} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {['todos', 'read', 'new', 'changed', 'pending', 'legacy'].map((s) => (<Button key={s} type="button" size="sm" variant={auditState === s ? 'primary' : 'outline'} onClick={() => setAuditState(s)}>{s === 'todos' ? 'Todos' : s === 'read' ? 'Já lidos' : s === 'new' ? 'Novos' : s === 'changed' ? 'Alterados' : s === 'pending' ? 'Pendentes' : 'Legados'}</Button>))}
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input label="Buscar documento" value={auditSearch} onChange={(e) => setAuditSearch(e.target.value)} placeholder="Nome, recorte ou estado" />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"><AuditList title="Novos no ciclo" items={auditItems.new_documents} /><AuditList title="Alterados" items={auditItems.changed_documents} /><AuditList title="Legados" items={auditItems.legacy_documents} /><AuditList title="Pendentes" items={auditItems.pending_documents} /></div>
        </Card>
      )}

      {/* Cycle management */}
      <Card><h2 className="text-xl font-semibold text-gray-900">Prestação de contas</h2>
        <p className="text-sm text-gray-500">Prestação atual: <span className="font-semibold text-gray-900">#{reportCycle?.cycle?.cycle_number || 1}</span> · Status: <span className="font-semibold text-gray-900">{reportCycle?.cycle?.status || 'aberto'}</span></p>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2"><Select label="Mês sendo fechado" options={monthOptions} value={closedPeriodLabel} onChange={(e) => handleClosedMonthChange(e.target.value)} /><Select label="Mês a abrir" options={monthOptions} value={nextPeriodLabel} onChange={(e) => setNextPeriodLabel(e.target.value)} /></div>
        <div className="mt-4"><Textarea label="Informações" value={closeCycleNotes} onChange={(e) => setCloseCycleNotes(e.target.value)} placeholder="Entregas, pendências, riscos..." /></div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={closeCycleMutation.isPending} onClick={() => { if (!window.confirm('Fechar e abrir nova prestação?')) return; closeCycleMutation.mutate({ reopenNew: true, notes: closeCycleNotes.trim() || undefined }); }}>Fechar e abrir nova</Button>
          <Button type="button" variant="outline" disabled={openCycleMutation.isPending} onClick={() => openCycleMutation.mutate()}>Nova prestação</Button>
        </div>
      </Card>

      {/* Text preview */}
      {textPreview && (
        <Card><div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold text-gray-900">Saída textual</h2><Button type="button" variant="outline" onClick={() => setTextPreview('')}>Fechar</Button></div>
          <pre className="mt-4 max-h-[480px] overflow-auto whitespace-pre-wrap rounded-2xl bg-gray-950 p-4 text-sm text-gray-100">{textPreview}</pre>
        </Card>
      )}

      {isLoading && (<div className="flex justify-center py-10"><div className="h-10 w-10 animate-spin rounded-full border-b-2 border-[#0d3b66]" /></div>)}
    </div>
  );
}

function MetricCard({ title, value, tone }: { title: string; value: number | string; tone: string }) {
  return (<div className="rounded-2xl border border-white/10 bg-white p-4 shadow-sm"><div className={`h-1 w-12 rounded-full ${tone}`} /><p className="mt-4 text-sm font-medium text-gray-500">{title}</p><p className="mt-2 text-3xl font-bold text-gray-900">{value}</p></div>);
}

function MiniStat({ label, value }: { label: string; value: number | string }) {
  return (<div className="rounded-xl bg-gray-50 px-3 py-2"><p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p><p className="mt-1 text-sm font-semibold text-gray-900">{value}</p></div>);
}

function MiniAudit({ label, value }: { label: string; value: number }) {
  return (<div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2"><p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p><p className="mt-1 text-base font-semibold text-gray-900">{value}</p></div>);
}

function AuditList({ title, items }: { title: string; items: Array<{ filename?: string; scope_label?: string | null; audit_state?: string }> }) {
  return (<div className="rounded-2xl border border-gray-200 bg-gray-50 p-4"><h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">{title}</h3><div className="mt-3 space-y-2">{items.length > 0 ? items.slice(0, 5).map((item, i) => (<div key={`${title}-${i}`} className="rounded-xl bg-white px-3 py-2 shadow-sm"><p className="text-sm font-medium text-gray-900">{item.filename || 'Documento'}</p><p className="text-xs text-gray-500">{item.scope_label || 'Sem recorte'} • {item.audit_state || '—'}</p></div>)) : <p className="text-sm text-gray-500">Nenhum item.</p>}</div></div>);
}

function BarRow({ label, value, total, suffix }: { label: string; value: number; total: number; suffix?: string }) {
  const pct = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (<div><div className="flex items-center justify-between gap-3 text-sm"><span className="font-medium text-gray-900">{label}</span><span className="text-gray-500">{value}{suffix ? ` • ${suffix}` : ''}</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-100"><div className="h-full rounded-full bg-[#0d3b66]" style={{ width: `${pct}%` }} /></div></div>);
}
