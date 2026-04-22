import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { pdfIntelligenceApi, reportsApi, releaseApi } from '../services/api';
import { Button, Select, Card, TipoBadge, Badge, PdfProcessingCard, PdfIntelligencePanel, Input, Textarea, CycleTimelineCard } from '../components';

type Section = 'executivo' | 'performance' | 'modulos' | 'releases' | 'temas' | 'tickets' | 'auditoria';

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
  if (monthIndex < 0 || Number.isNaN(year)) {
    return '';
  }
  const nextIndex = (monthIndex + 1) % 12;
  const nextYear = monthIndex === 11 ? year + 1 : year;
  return `${MONTH_LABELS[nextIndex]}/${nextYear}`;
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
    if (selectedRelease) {
      next.set('release', selectedRelease);
    } else {
      next.delete('release');
    }
    if (selectedCycleId) {
      next.set('cycle', selectedCycleId);
    } else {
      next.delete('cycle');
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, selectedCycleId, selectedRelease, setSearchParams]);

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: report, isLoading } = useQuery({
    queryKey: ['reports', 'ticket-summary', selectedRelease, selectedCycleId],
    queryFn: () => reportsApi.ticketSummary(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedCycleId ? Number(selectedCycleId) : undefined,
    ),
    enabled: true,
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
    const closedCycles = availableCycles.filter((cycle) => cycle.status === 'prestado');
    if (closedCycles.length === 0) {
      return '';
    }
    return String(closedCycles[0].id);
  }, [availableCycles]);
  const currentOpenCycleId = useMemo(() => {
    const openCycle = availableCycles.find((cycle) => cycle.status === 'aberto') || (reportCycle?.cycle?.status === 'aberto' ? reportCycle.cycle : null);
    return openCycle?.id ? String(openCycle.id) : '';
  }, [availableCycles, reportCycle?.cycle]);
  const releaseRecordOptions = useMemo(
    () => releases.map((r) => ({ id: r.id, label: `${r.release_name || `Versão ${r.id}`} (${r.version})` })),
    [releases]
  );
  const monthOptions = useMemo(() => {
    const currentYear = buildMonthOptions(0);
    const nextYear = buildMonthOptions(1);
    return [
      { value: '', label: 'Selecione um mês' },
      ...currentYear,
      ...nextYear,
    ];
  }, []);

  const auditItems = useMemo(() => {
    const normalize = (items: Array<{ filename?: string; scope_label?: string | null; audit_state?: string }>) => {
      return items.filter((item) => {
        const stateMatch = auditState === 'todos' || (item.audit_state || 'pending') === auditState;
        const search = auditSearch.trim().toLowerCase();
        const haystack = `${item.filename || ''} ${item.scope_label || ''} ${item.audit_state || ''}`.toLowerCase();
        const searchMatch = !search || haystack.includes(search);
        return stateMatch && searchMatch;
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
    } finally {
      setIsTextLoading(false);
    }
  };

  const handleOpenHtml = async (focus = reportFocus) => {
    const result = await reportsApi.htmlReport(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
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
        selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
        selectedCycleId ? Number(selectedCycleId) : undefined,
        focus ?? undefined,
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = selectedRelease
        ? `relatorio-gerencial-${selectedRelease}.pdf`
        : 'relatorio-gerencial.pdf';
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    } finally {
      setIsPdfLoading(false);
    }
  };

  const clearReportScreen = () => {
    setSelectedRelease('');
    setSelectedCycleId('');
    setActiveSection('executivo');
    setFocusedModuleName(null);
    setFocusedReleaseId(null);
    setFocusedThemeName(null);
    setFocusedTicketNumber(null);
    setTextPreview('');
    setClosedPeriodLabel('');
    setNextPeriodLabel('');
    setAuditState('todos');
    setAuditSearch('');
  };

  const handleClosedMonthChange = (value: string) => {
    setClosedPeriodLabel(value);
    const suggested = getNextMonthLabel(value);
    if (suggested) {
      setNextPeriodLabel(suggested);
    }
  };

  const closeCycleMutation = useMutation({
    mutationFn: (payload: { reopenNew: boolean; notes?: string }) => reportsApi.closeCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      reopenNew: payload.reopenNew,
      notes: payload.notes,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
      closedPeriodLabel: closedPeriodLabel.trim() || undefined,
      nextPeriodLabel: nextPeriodLabel.trim() || undefined,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['report-cycle'] }),
        queryClient.invalidateQueries({ queryKey: ['reports'] }),
        queryClient.invalidateQueries({ queryKey: ['pdf-intelligence'] }),
      ]);
      clearReportScreen();
      setCloseCycleNotes('');
    },
  });

  const openCycleMutation = useMutation({
    mutationFn: () => reportsApi.openCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
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
  const focusedModule = useMemo(
    () => focusModules.find((module) => module.module === focusedModuleName) ?? null,
    [focusModules, focusedModuleName],
  );
  const focusedRelease = useMemo(
    () => focusReleases.find((release) => release.id === focusedReleaseId) ?? null,
    [focusReleases, focusedReleaseId],
  );
  const focusedTheme = useMemo(
    () => focusThemes.find((theme) => theme.theme === focusedThemeName) ?? null,
    [focusThemes, focusedThemeName],
  );
  const focusedTicket = useMemo(
    () => focusTickets.find((ticket) => ticket.ticket === focusedTicketNumber) ?? null,
    [focusTickets, focusedTicketNumber],
  );
  const reportFocus = useMemo(() => {
    if (focusedModuleName) {
      return { type: 'module', value: focusedModuleName, label: `Módulo: ${focusedModuleName}` };
    }
    if (focusedRelease) {
      return {
        type: 'release',
        value: String(focusedRelease.id),
        label: `Versão: ${focusedRelease.release_name} (${focusedRelease.version})`,
      };
    }
    if (focusedThemeName) {
      return { type: 'theme', value: focusedThemeName, label: `Tema: ${focusedThemeName}` };
    }
    if (focusedTicketNumber) {
      return { type: 'ticket', value: focusedTicketNumber, label: `Ticket: ${focusedTicketNumber}` };
    }
    return null;
  }, [focusedModuleName, focusedRelease, focusedThemeName, focusedTicketNumber]);
  const insights = report?.insights ?? [];
  const pdfThemes = report?.pdf_themes ?? [];
  const pdfSections = report?.pdf_context?.sections ?? [];
  const pdfKnowledgeTerms = report?.pdf_context?.knowledge_terms ?? [];
  const pdfProblemSolutions = report?.pdf_context?.problem_solution_examples ?? [];
  const modulesWithoutPdf = useMemo(
    () => focusModules.filter((module) => (module.pdf_documents ?? 0) === 0),
    [focusModules],
  );
  const topVolumeModules = useMemo(
    () => [...focusModules].sort((a, b) => b.tickets - a.tickets || b.releases - a.releases).slice(0, 3),
    [focusModules],
  );
  const topRiskModules = useMemo(
    () =>
      [...focusModules]
        .sort((a, b) => {
          const aTheme = a.themes?.[0]?.count ?? 0;
          const bTheme = b.themes?.[0]?.count ?? 0;
          const aScore = (a.corrections * 3) + aTheme + ((a.pdf_documents ?? 0) === 0 ? 2 : 0);
          const bScore = (b.corrections * 3) + bTheme + ((b.pdf_documents ?? 0) === 0 ? 2 : 0);
          return bScore - aScore || b.tickets - a.tickets;
        })
        .slice(0, 3),
    [focusModules],
  );
  const statusDistribution = useMemo(() => {
    const entries = Object.entries(report?.by_status ?? {}).map(([status, value]) => ({
      label: statusLabel(status),
      value,
      status,
    }));
    return entries.sort((a, b) => b.value - a.value);
  }, [report?.by_status]);
  const modulePerformance = useMemo(() => {
    return [...focusModules].slice(0, 6);
  }, [focusModules]);
  const releasePerformance = useMemo(() => {
    return [...focusReleases]
      .sort((a, b) => {
        const left = a.applies_on ? new Date(a.applies_on).getTime() : 0;
        const right = b.applies_on ? new Date(b.applies_on).getTime() : 0;
        return left - right;
      })
      .slice(-8);
  }, [focusReleases]);

  useEffect(() => {
    sectionFocusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [activeSection]);

  useEffect(() => {
    if (focusedModuleName && !focusedModule) {
      setFocusedModuleName(null);
    }
  }, [focusedModule, focusedModuleName]);

  useEffect(() => {
    if (focusedReleaseId && !focusedRelease) {
      setFocusedReleaseId(null);
    }
  }, [focusedRelease, focusedReleaseId]);

  useEffect(() => {
    if (focusedThemeName && !focusedTheme) {
      setFocusedThemeName(null);
    }
  }, [focusedTheme, focusedThemeName]);

  useEffect(() => {
    if (focusedTicketNumber && !focusedTicket) {
      setFocusedTicketNumber(null);
    }
  }, [focusedTicket, focusedTicketNumber]);

  const sectionFocus = useMemo<SectionFocus>(() => {
    const topTheme = focusThemes[0];
    const topRelease = report?.top_release;
    const topModule = report?.top_module;
    const topTicket = focusTickets[0];
    const pendingAudit = cycleAudit?.counts.pending ?? 0;
    const changedAudit = cycleAudit?.counts.changed ?? 0;
    const alreadyAudit = cycleAudit?.counts.already_read ?? 0;

    switch (activeSection) {
      case 'performance':
        if (focusedRelease) {
          return {
            title: `Foco de performance - ${focusedRelease.release_name}`,
            subtitle: 'A release selecionada muda a leitura da tendência e dos volumes consolidados.',
            badge: 'Versão em foco',
            tone: 'border-[#184e77] bg-[#f3f8fc]',
            primaryStatLabel: 'Tickets da release',
            primaryStatValue: `${focusedRelease.tickets}`,
            secondaryStatLabel: 'Status',
            secondaryStatValue: Object.entries(focusedRelease.by_status).map(([status, count]) => `${statusLabel(status)}: ${count}`).join(' | ') || 'Sem tickets',
            bullets: [
              `${focusedRelease.release_name} (${focusedRelease.version}) está em foco.`,
              focusedRelease.applies_on ? `Aplicada em ${focusedRelease.applies_on.slice(0, 10)}.` : 'Sem data de aplicação informada.',
              `Correções: ${focusedRelease.corrections} | Melhorias: ${focusedRelease.improvements}.`,
            ],
            actionHint: 'Essa release agora governa a leitura visual da seção de performance.',
          };
        }
        return {
          title: 'Foco de performance',
          subtitle: 'A leitura destaca pressão operacional, status e tendência de entregas.',
          badge: 'Medição operacional',
          tone: 'border-[#184e77] bg-[#f3f8fc]',
          primaryStatLabel: 'Status dominante',
          primaryStatValue: statusDistribution[0] ? `${statusDistribution[0].label} (${statusDistribution[0].value})` : 'Sem dados',
          secondaryStatLabel: 'Módulo mais pressionado',
          secondaryStatValue: topModule ? `${topModule.module} (${topModule.tickets})` : 'Sem dados',
          bullets: [
            topModule ? `${topModule.module} concentra ${topModule.share}% do total.` : 'Nenhum módulo concentrado para o recorte atual.',
            releasePerformance.length > 0 ? `Última janela analisada: ${releasePerformance[releasePerformance.length - 1]?.release_name || 'sem referência'}.` : 'Sem tendência por release para exibir.',
            statusDistribution.length > 0 ? `${statusDistribution[0].label} lidera a fila com foco imediato.` : 'Sem distribuição de status disponível.',
          ],
          actionHint: 'Use esta aba para medir gargalos e priorizar a correção da fila.',
        };
      case 'modulos':
        if (focusedModule) {
          return {
            title: `Foco em módulo - ${focusedModule.module}`,
            subtitle: 'A seção de módulos foi recortada para o módulo selecionado.',
            badge: 'Módulo em foco',
            tone: 'border-amber-300 bg-amber-50',
            primaryStatLabel: 'Tickets',
            primaryStatValue: `${focusedModule.tickets}`,
            secondaryStatLabel: 'PDFs relacionados',
            secondaryStatValue: `${focusedModule.pdf_documents ?? 0}`,
            bullets: [
              focusedModule.description || 'Sem descrição cadastrada.',
              focusedModule.explanation || 'Sem explicação gerada.',
              (focusedModule.pdf_topics ?? []).length > 0 ? `Temas: ${(focusedModule.pdf_topics ?? []).slice(0, 3).join(', ')}.` : 'Sem temas de PDF relacionados.',
            ],
            actionHint: 'Você pode usar este foco para revisar tickets-chave e documentação do módulo.',
          };
        }
        return {
          title: 'Foco em módulos',
          subtitle: 'Consolida módulos sem PDF, módulos com maior volume e risco operacional.',
          badge: 'Resumo por módulo',
          tone: 'border-amber-300 bg-amber-50',
          primaryStatLabel: 'Sem PDF',
          primaryStatValue: `${modulesWithoutPdf.length}`,
          secondaryStatLabel: 'Maior volume',
          secondaryStatValue: topVolumeModules[0] ? topVolumeModules[0].module : 'Sem dados',
          bullets: [
            modulesWithoutPdf.length > 0 ? `${modulesWithoutPdf[0].module} ainda não possui PDF relacionado.` : 'Todos os módulos já possuem ao menos um PDF.',
            topRiskModules[0] ? `${topRiskModules[0].module} é o módulo com maior recorrência de risco.` : 'Sem ranking de risco disponível.',
            topModule ? `Módulo principal do recorte: ${topModule.module}.` : 'Sem módulo principal definido.',
          ],
          actionHint: 'Clique aqui para revisar documentação, explicação e tickets-chave de cada módulo.',
        };
      case 'releases':
        if (focusedRelease) {
          return {
            title: `Foco em versão - ${focusedRelease.release_name}`,
            subtitle: 'A release selecionada agora orienta a inteligência dessa seção.',
            badge: 'Versão detalhada',
            tone: 'border-sky-300 bg-sky-50',
            primaryStatLabel: 'Versão',
            primaryStatValue: focusedRelease.version,
            secondaryStatLabel: 'Tickets',
            secondaryStatValue: `${focusedRelease.tickets}`,
            bullets: [
              `${focusedRelease.module || 'Sem módulo'} | ${focusedRelease.release_name}`,
              focusedRelease.applies_on ? `Aplicada em ${focusedRelease.applies_on.slice(0, 10)}.` : 'Sem data de aplicação informada.',
              `Status: ${Object.entries(focusedRelease.by_status).map(([status, count]) => `${statusLabel(status)} ${count}`).join(' | ') || 'Sem tickets'}`,
            ],
            actionHint: 'Use os botões de release para alternar o foco e comparar entregas.',
          };
        }
        return {
          title: 'Foco em releases',
          subtitle: 'Mostra o volume e a distribuição dos tickets por entrega publicada.',
          badge: 'Entrega e impacto',
          tone: 'border-sky-300 bg-sky-50',
          primaryStatLabel: 'Última release',
          primaryStatValue: topRelease ? `${topRelease.release_name}` : 'Sem dados',
          secondaryStatLabel: 'Tickets na última',
          secondaryStatValue: topRelease ? `${topRelease.tickets}` : '0',
          bullets: [
            topRelease ? `${topRelease.release_name} foi a entrega mais relevante do recorte.` : 'Nenhuma versão encontrada no recorte.',
            focusReleases.length > 0 ? `${focusReleases.length} versão(ões) foram consolidadas no período.` : 'Sem versões consolidadas.',
            selectedRelease ? 'O filtro de versão está ativo e restringe o relatório atual.' : 'Nenhum filtro de versão aplicado.',
          ],
          actionHint: 'Use esta aba para abrir a inteligência de uma release específica e validar o que foi entregue.',
        };
      case 'temas':
        if (focusedTheme) {
          return {
            title: `Foco em tema - ${focusedTheme.theme}`,
            subtitle: 'A inteligência temática foi recortada para este tema recorrente.',
            badge: 'Tema em foco',
            tone: 'border-violet-300 bg-violet-50',
            primaryStatLabel: 'Ocorrências',
            primaryStatValue: `${focusedTheme.count}`,
            secondaryStatLabel: 'Exemplos',
            secondaryStatValue: `${focusedTheme.examples.length}`,
            bullets: [
              focusedTheme.theme,
              focusedTheme.examples.length > 0 ? `Exemplos: ${focusedTheme.examples.slice(0, 3).join(', ')}.` : 'Sem exemplos associados.',
              pdfThemes.length > 0 ? `${pdfThemes.length} tema(s) de PDF complementares disponíveis.` : 'Sem temas complementares da base PDF.',
            ],
            actionHint: 'Esse foco ajuda a transformar recorrência em playbooks e ações de treinamento.',
          };
        }
        return {
          title: 'Foco em temas recorrentes',
          subtitle: 'Extrai padrões, repetição e sinais de melhoria contínua dos tickets.',
          badge: 'Inteligência temática',
          tone: 'border-violet-300 bg-violet-50',
          primaryStatLabel: 'Tema líder',
          primaryStatValue: topTheme ? topTheme.theme : 'Sem dados',
          secondaryStatLabel: 'Ocorrências',
          secondaryStatValue: topTheme ? `${topTheme.count}` : '0',
          bullets: [
            topTheme ? `${topTheme.theme} aparece com maior recorrência.` : 'Sem tema recorrente identificado.',
            topTheme?.examples?.length ? `Exemplos: ${topTheme.examples.slice(0, 3).join(', ')}.` : 'Sem exemplos associados.',
            pdfThemes.length > 0 ? `A inteligência local retornou ${pdfThemes.length} tema(s) complementares.` : 'Sem temas adicionais da base PDF.',
          ],
          actionHint: 'Clique aqui para transformar repetição em playbooks ou ações de treinamento.',
        };
      case 'tickets':
        if (focusedTicket) {
          return {
            title: `Foco em ticket - ${focusedTicket.ticket}`,
            subtitle: 'A visualização agora destaca o ticket escolhido e sua resolução.',
            badge: 'Ticket em foco',
            tone: 'border-emerald-300 bg-emerald-50',
            primaryStatLabel: 'Tipo',
            primaryStatValue: focusedTicket.tipo,
            secondaryStatLabel: 'Status',
            secondaryStatValue: focusedTicket.status,
            bullets: [
              focusedTicket.title || focusedTicket.descricao || 'Sem título',
              focusedTicket.descricao || 'Sem descrição do problema.',
              focusedTicket.resolucao || 'Sem solução informada.',
            ],
            actionHint: 'O foco por ticket facilita revisão de causa, solução e impacto.',
          };
        }
        return {
          title: 'Foco em tickets',
          subtitle: 'Lista problema, solução e tipo de cada ticket consolidado no período.',
          badge: 'Base de evidências',
          tone: 'border-emerald-300 bg-emerald-50',
          primaryStatLabel: 'Ticket líder',
          primaryStatValue: topTicket ? topTicket.ticket : 'Sem dados',
          secondaryStatLabel: 'Total visível',
          secondaryStatValue: `${focusTickets.length}`,
          bullets: [
            topTicket ? `${topTicket.ticket} é o ticket de entrada mais recente no foco atual.` : 'Nenhum ticket disponível para o recorte.',
            focusTickets.some((ticket) => ticket.status === 'bloqueada') ? 'Há tickets bloqueados que exigem ação.' : 'Não há bloqueios visíveis no recorte atual.',
            focusTickets.some((ticket) => ticket.tipo === 'correcao_bug') ? 'Há correções registradas para auditoria de causa e efeito.' : 'Sem correções destacadas no momento.',
          ],
          actionHint: 'Use esta seção para revisar evidências, problemas e soluções aplicadas.',
        };
      case 'auditoria':
        return {
          title: 'Foco em auditoria',
          subtitle: 'Audita o ciclo de leitura dos PDFs e separa o que é novo, alterado, legado ou pendente.',
          badge: 'Ciclo de leitura',
          tone: 'border-slate-300 bg-slate-50',
          primaryStatLabel: 'Já lidos',
          primaryStatValue: `${alreadyAudit}`,
          secondaryStatLabel: 'Pendentes',
          secondaryStatValue: `${pendingAudit}`,
          bullets: [
            changedAudit > 0 ? `${changedAudit} documento(s) mudaram e precisam de reprocessamento.` : 'Nenhum documento alterado no ciclo atual.',
            pendingAudit > 0 ? `${pendingAudit} documento(s) aguardam processamento.` : 'Nenhum documento pendente no momento.',
            cycleAudit?.counts.new ? `${cycleAudit.counts.new} arquivo(s) novos foram detectados.` : 'Nenhum arquivo novo neste ciclo.',
          ],
          actionHint: 'Clique nesta aba para validar o que já foi lido e o que ainda precisa de processamento.',
        };
      case 'executivo':
      default:
        return {
          title: 'Foco executivo',
          subtitle: 'Síntese da prestação de contas com os indicadores que mais importam agora.',
          badge: 'Resumo geral',
          tone: 'border-[#0d3b66] bg-[#eef6ff]',
          primaryStatLabel: 'Tickets totais',
          primaryStatValue: `${totals.tickets}`,
          secondaryStatLabel: 'Módulos com maior impacto',
          secondaryStatValue: topModule ? topModule.module : 'Sem dados',
          bullets: [
            topModule ? `${topModule.module} é o módulo dominante do recorte.` : 'Sem módulo dominante no período.',
            insights[0] ? `${insights[0].title}: ${insights[0].detail}` : 'Sem insight adicional disponível.',
            pdfSections.length > 0 ? `A inteligência de PDF trouxe ${pdfSections.length} seção(ões) semântica(s).` : 'Nenhuma seção de PDF foi consolidada.',
          ],
          actionHint: 'Clique nas demais abas para abrir a inteligência operacional por dimensão.',
        };
    }
  }, [
    activeSection,
    cycleAudit?.counts.already_read,
    cycleAudit?.counts.changed,
    cycleAudit?.counts.new,
    cycleAudit?.counts.pending,
    focusTickets,
    focusThemes,
    focusModules,
    focusReleases,
    insights,
    modulesWithoutPdf.length,
    pdfSections.length,
    pdfThemes.length,
    releasePerformance,
    report?.top_module,
    report?.top_release,
    selectedRelease,
    statusDistribution,
    focusedModule,
    focusedRelease,
    focusedTheme,
    focusedTicket,
    topRiskModules,
    topVolumeModules,
    totals.tickets,
  ]);

  const clearFocusedContext = () => {
    setFocusedModuleName(null);
    setFocusedReleaseId(null);
    setFocusedThemeName(null);
    setFocusedTicketNumber(null);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-[#0d3b66] via-[#184e77] to-[#1d5c85] p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.35em] text-white/70">Prestação de Contas Gerencial</p>
            <h1 className="mt-2 text-3xl font-bold">Relatórios com inteligência executiva</h1>
            <p className="mt-3 text-white/85">
              O menu agora sintetiza releases, módulos, tickets, status e temas recorrentes para análise da gerência.
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              className="border-white text-white hover:bg-white hover:text-[#0d3b66]"
              onClick={() => {
                if (currentOpenCycleId) {
                  setSelectedCycleId(currentOpenCycleId);
                  setSelectedRelease('');
                }
              }}
              disabled={!currentOpenCycleId}
            >
              Mês vigente
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-white text-white hover:bg-white hover:text-[#0d3b66]"
              onClick={() => {
                setSelectedCycleId('');
                setSelectedRelease('');
              }}
            >
              Histórico completo
            </Button>
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => handleGenerateText()} disabled={isTextLoading}>
              {isTextLoading ? 'Gerando texto...' : 'Gerar texto'}
            </Button>
            <Button type="button" variant="secondary" onClick={() => handleOpenHtml()}>
              Abrir HTML
            </Button>
            <Button type="button" variant="secondary" onClick={() => handleExportPdf()} disabled={isPdfLoading}>
              {isPdfLoading ? 'Exportando PDF...' : 'Exportar PDF'}
            </Button>
          </div>
        </div>
        {reportFocus && (
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
            <Badge variant="info">{reportFocus.label}</Badge>
            <span className="text-sm text-white/80">O relatório pode ser exportado com este recorte em foco.</span>
            <Button type="button" size="sm" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => handleGenerateText(reportFocus)}>
              Texto do foco
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => handleOpenHtml(reportFocus)}>
              HTML do foco
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => handleExportPdf(reportFocus)} disabled={isPdfLoading}>
              PDF do foco
            </Button>
            <Button type="button" size="sm" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={clearFocusedContext}>
              Limpar foco
            </Button>
          </div>
        )}
      </div>

      <Card>
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="w-full max-w-sm">
            <Select
              label="Versão"
              options={releaseOptions}
              value={selectedRelease}
              onChange={(e) => {
                setSelectedRelease(e.target.value);
                setSelectedCycleId('');
              }}
            />
          </div>
          <div className="w-full max-w-sm">
            <Select
              label="Ciclo fechado"
              options={cycleOptions}
              value={selectedCycleId}
              onChange={(e) => setSelectedCycleId(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!previousClosedCycleId}
              onClick={() => setSelectedCycleId(previousClosedCycleId)}
            >
              Abrir ciclo anterior
            </Button>
            {(['executivo', 'performance', 'modulos', 'releases', 'temas', 'tickets', 'auditoria'] as Section[]).map((section) => (
              <Button
                key={section}
                type="button"
                size="sm"
                variant={activeSection === section ? 'primary' : 'outline'}
                className={activeSection === section ? 'shadow-lg shadow-[#0d3b66]/20' : 'hover:-translate-y-0.5'}
                onClick={() => setActiveSection(section)}
                aria-pressed={activeSection === section}
              >
                {section === 'executivo' && 'Executivo'}
                {section === 'performance' && 'Performance'}
                {section === 'modulos' && 'Módulos'}
                {section === 'releases' && 'Versões'}
                {section === 'temas' && 'Temas'}
                {section === 'tickets' && 'Tickets'}
                {section === 'auditoria' && 'Auditoria'}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      <CycleTimelineCard
        title="Linha do tempo da prestação"
        description="A prestação aberta concentra os dados do mês em trabalho. Os meses fechados aparecem como histórico consolidado e podem ser selecionados para análise gerencial."
        currentCycle={reportCycle?.cycle ?? availableCycles.find((cycle) => cycle.status === 'aberto') ?? null}
        previousCycle={availableCycles.find((cycle) => cycle.status === 'prestado') ?? null}
        cycles={availableCycles}
        selectedCycleId={selectedCycleId}
        onSelectCycle={(cycleId) => {
          setSelectedCycleId(cycleId);
          setActiveSection('executivo');
        }}
        onOpenPrevious={() => {
          if (previousClosedCycleId) {
            setSelectedCycleId(previousClosedCycleId);
            setActiveSection('executivo');
          }
        }}
        onOpenCurrent={() => {
          setSelectedCycleId('');
          setActiveSection('executivo');
        }}
      />

      <PdfProcessingCard
        scopeType="release"
        scopeLabel="Relatórios"
        scopeId={selectedRelease ? Number(selectedRelease) : null}
        recordOptions={releaseRecordOptions}
      />

      <Card>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Prestação de contas</h2>
            <p className="text-sm text-gray-500">
              Prestação atual: <span className="font-semibold text-gray-900">#{reportCycle?.cycle?.cycle_number || 1}</span> · Status atual: <span className="font-semibold text-gray-900">{reportCycle?.cycle?.status || 'aberto'}</span>.
              {reportCycle?.cycle?.closed_at ? ` Fechado em ${reportCycle.cycle.closed_at.slice(0, 19).replace('T', ' ')}` : ' Ainda aberto para revisão.'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {reportCycle?.cycle?.period_label || 'Prestação atual'}{reportCycle?.cycle?.notes ? ` | Último fechamento: ${reportCycle.cycle.notes}` : ''}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Mês em trabalho: <span className="font-semibold text-gray-900">{report?.current_cycle?.label || reportCycle?.cycle?.period_label || 'Sem referência'}</span>
              {report?.previous_cycle?.label ? (
                <> · Mês anterior consolidado: <span className="font-semibold text-gray-900">{report.previous_cycle.label}</span></>
              ) : null}
            </p>
            <p className="mt-1 text-xs font-semibold text-[#0d3b66]">
              {selectedCycleId
                ? `Ciclo histórico selecionado: ${cycleOptions.find((option) => option.value === selectedCycleId)?.label || selectedCycleId}`
                : 'Visão atual: histórico completo consolidado.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={closeCycleMutation.isPending}
              onClick={() => {
                if (!window.confirm('Fechar este mês e iniciar a nova prestação informada?')) return;
                closeCycleMutation.mutate({ reopenNew: true, notes: closeCycleNotes.trim() || undefined });
              }}
            >
              Fechar e abrir nova prestação
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={openCycleMutation.isPending}
              onClick={() => openCycleMutation.mutate()}
            >
              Nova prestação
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-xl font-semibold text-gray-900">Resumo do fechamento</h2>
        <p className="text-sm text-gray-500">
          Informe qual mês está sendo fechado e qual mês será aberto. O resumo ficará salvo no ciclo fechado e a nova prestação nascerá numerada e limpa.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <Select
            label="Qual mês está sendo fechado?"
            options={monthOptions}
            value={closedPeriodLabel}
            onChange={(e) => handleClosedMonthChange(e.target.value)}
          />
          <Select
            label="Qual mês será aberto?"
            options={monthOptions}
            value={nextPeriodLabel}
            onChange={(e) => setNextPeriodLabel(e.target.value)}
          />
        </div>
        <div className="mt-4">
          <Textarea
            label="Informações da prestação"
            value={closeCycleNotes}
            onChange={(e) => setCloseCycleNotes(e.target.value)}
            placeholder="Ex.: entregas concluídas, pendências, riscos, decisões da gerência e observações do período."
          />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={closeCycleMutation.isPending}
            onClick={() => {
              if (!window.confirm('Fechar esta prestação com os meses informados?')) return;
              closeCycleMutation.mutate({ reopenNew: false, notes: closeCycleNotes.trim() || undefined });
            }}
          >
            Fechar somente o período
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={openCycleMutation.isPending}
            onClick={() => {
              if (!window.confirm('Abrir nova prestação para o mês informado?')) return;
              openCycleMutation.mutate();
            }}
          >
            Abrir nova prestação
          </Button>
        </div>
      </Card>

      <Card title="Corte operacional">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-[#0d3b66]/15 bg-[#f8fbff] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês em trabalho</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">
                  {report?.current_cycle?.label || reportCycle?.cycle?.period_label || 'Sem referência'}
                </h3>
              </div>
              <Badge variant="success">Operacional</Badge>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              Este é o mês aberto. O sistema grava os novos dados aqui e não mistura com ciclos já fechados.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniCycleMetric label="Homologações" value={report?.current_cycle?.homologacoes ?? 0} />
              <MiniCycleMetric label="Customizações" value={report?.current_cycle?.customizacoes ?? 0} />
              <MiniCycleMetric label="Atividades" value={report?.current_cycle?.atividades ?? 0} />
              <MiniCycleMetric label="Versões" value={report?.current_cycle?.releases ?? 0} />
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês anterior</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">
                  {report?.previous_cycle?.label || 'Sem referência'}
                </h3>
              </div>
              <Badge variant="warning">Fechado</Badge>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              Este ciclo já foi consolidado e só aparece nos relatórios executivos.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniCycleMetric label="Homologações" value={report?.previous_cycle?.homologacoes ?? 0} />
              <MiniCycleMetric label="Customizações" value={report?.previous_cycle?.customizacoes ?? 0} />
              <MiniCycleMetric label="Atividades" value={report?.previous_cycle?.atividades ?? 0} />
              <MiniCycleMetric label="Versões" value={report?.previous_cycle?.releases ?? 0} />
            </div>
          </div>
        </div>
      </Card>

      <PdfIntelligencePanel
        scopeType="release"
        scopeLabel="Relatórios Gerenciais"
        scopeId={selectedRelease ? Number(selectedRelease) : null}
        recordOptions={releaseRecordOptions}
      />

      <div ref={sectionFocusRef}>
        <Card className={`border-l-4 ${sectionFocus.tone}`}>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="info">{sectionFocus.badge}</Badge>
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Seção ativa</span>
              </div>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900">{sectionFocus.title}</h2>
              <p className="mt-2 text-sm text-gray-600">{sectionFocus.subtitle}</p>
              <p className="mt-3 text-sm font-medium text-[#0d3b66]">{sectionFocus.actionHint}</p>
            </div>
            <div className="grid w-full gap-3 sm:grid-cols-2 lg:max-w-xl">
              <div className="rounded-2xl bg-white px-4 py-3 shadow-sm">
                <p className="text-[11px] uppercase tracking-wider text-gray-500">{sectionFocus.primaryStatLabel}</p>
                <p className="mt-1 text-base font-semibold text-gray-900">{sectionFocus.primaryStatValue}</p>
              </div>
              {sectionFocus.secondaryStatLabel && (
                <div className="rounded-2xl bg-white px-4 py-3 shadow-sm">
                  <p className="text-[11px] uppercase tracking-wider text-gray-500">{sectionFocus.secondaryStatLabel}</p>
                  <p className="mt-1 text-base font-semibold text-gray-900">{sectionFocus.secondaryStatValue}</p>
                </div>
              )}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {sectionFocus.bullets.map((bullet, index) => (
              <div key={`${sectionFocus.title}-${index}`} className="rounded-2xl border border-white/80 bg-white/90 px-4 py-3 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Inteligência {index + 1}</p>
                <p className="mt-1 text-sm text-gray-700">{bullet}</p>
              </div>
            ))}
          </div>
          {(focusedModuleName || focusedReleaseId || focusedThemeName || focusedTicketNumber) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {focusedModuleName && <Badge variant="warning">Módulo: {focusedModuleName}</Badge>}
              {focusedReleaseId && <Badge variant="warning">Versão: {focusedReleaseId}</Badge>}
              {focusedThemeName && <Badge variant="warning">Tema: {focusedThemeName}</Badge>}
              {focusedTicketNumber && <Badge variant="warning">Ticket: {focusedTicketNumber}</Badge>}
              <Button type="button" variant="outline" size="sm" onClick={clearFocusedContext}>
                Limpar foco
              </Button>
            </div>
          )}
        </Card>
      </div>

      {activeSection === 'auditoria' && (
        <Card>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Auditoria de leitura de PDFs</h2>
                <p className="text-sm text-gray-500">
                  Controle de documentos já lidos, novos arquivos, mudanças detectadas e itens legados do ciclo atual.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <MiniAudit label="Já lidos" value={cycleAudit?.counts.already_read ?? 0} />
                <MiniAudit label="Novos" value={cycleAudit?.counts.new ?? 0} />
                <MiniAudit label="Alterados" value={cycleAudit?.counts.changed ?? 0} />
                <MiniAudit label="Pendentes" value={cycleAudit?.counts.pending ?? 0} />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" variant={auditState === 'todos' ? 'primary' : 'outline'} onClick={() => setAuditState('todos')}>
                Todos
              </Button>
              <Button type="button" size="sm" variant={auditState === 'read' ? 'primary' : 'outline'} onClick={() => setAuditState('read')}>
                Já lidos
              </Button>
              <Button type="button" size="sm" variant={auditState === 'new' ? 'primary' : 'outline'} onClick={() => setAuditState('new')}>
                Novos
              </Button>
              <Button type="button" size="sm" variant={auditState === 'changed' ? 'primary' : 'outline'} onClick={() => setAuditState('changed')}>
                Alterados
              </Button>
              <Button type="button" size="sm" variant={auditState === 'pending' ? 'primary' : 'outline'} onClick={() => setAuditState('pending')}>
                Pendentes
              </Button>
              <Button type="button" size="sm" variant={auditState === 'legacy' ? 'primary' : 'outline'} onClick={() => setAuditState('legacy')}>
                Legados
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Input
                label="Buscar documento"
                value={auditSearch}
                onChange={(e) => setAuditSearch(e.target.value)}
                placeholder="Digite nome, recorte ou estado"
              />
              <Select
                label="Filtrar por estado"
                value={auditState}
                onChange={(e) => setAuditState(e.target.value)}
                options={[
                  { value: 'todos', label: 'Todos' },
                  { value: 'read', label: 'Já lidos' },
                  { value: 'new', label: 'Novos' },
                  { value: 'changed', label: 'Alterados' },
                  { value: 'legacy', label: 'Legados' },
                  { value: 'pending', label: 'Pendentes' },
                  { value: 'missing', label: 'Ausentes' },
                ]}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <AuditList title="Novos no ciclo" items={auditItems.new_documents} />
              <AuditList title="Alterados" items={auditItems.changed_documents} />
              <AuditList title="Legados" items={auditItems.legacy_documents} />
              <AuditList title="Pendentes" items={auditItems.pending_documents} />
            </div>
          </div>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-[#0d3b66]" />
        </div>
      ) : report ? (
        <div className="space-y-6">
          {activeSection === 'executivo' && (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
                <MetricCard title="Versões" value={totals.releases} tone="bg-[#0d3b66]" />
                <MetricCard title="Módulos" value={totals.modules} tone="bg-slate-800" />
                <MetricCard title="Tickets" value={totals.tickets} tone="bg-emerald-600" />
                <MetricCard title="Correções" value={totals.corrections} tone="bg-red-600" />
                <MetricCard title="Melhorias" value={totals.improvements} tone="bg-blue-600" />
                <MetricCard title="Funcionalidades" value={totals.features} tone="bg-violet-600" />
              </div>

              {report.top_module && (
                <Card>
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-wider text-gray-500">Concentração de demanda</p>
                      <h2 className="text-xl font-semibold text-gray-900">{report.top_module.module}</h2>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="warning">{report.top_module.share}% do total</Badge>
                      <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(report.top_module?.module || null); setActiveSection('modulos'); }}>
                        Focar módulo
                      </Button>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <MiniStat label="Tickets" value={report.top_module.tickets} />
                    <MiniStat label="Versões" value={report.top_module.releases} />
                    <MiniStat label="Última versão" value={report.top_module.latest_version} />
                    <MiniStat label="Última versão" value={report.top_module.latest_release} />
                  </div>
                </Card>
              )}

              {insights.length > 0 && (
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  {insights.map((insight) => (
                    <Card key={insight.title} className="h-full">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-lg font-semibold text-gray-900">{insight.title}</h3>
                        <Badge variant={severityVariant(insight.severity)}>{insight.severity}</Badge>
                      </div>
                      <p className="mt-3 text-sm text-gray-600">{insight.detail}</p>
                    </Card>
                  ))}
                </div>
              )}

              {(pdfSections.length > 0 || pdfKnowledgeTerms.length > 0 || pdfProblemSolutions.length > 0) && (
                <Card>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">Conhecimento extraído dos PDFs</h2>
                      <p className="text-sm text-gray-500">Seções, termos recorrentes e pares problema/solução identificados localmente.</p>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Seções</h3>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {pdfSections.length > 0 ? (
                          pdfSections.slice(0, 8).map((section) => (
                            <Badge key={section.section} variant="info">
                              {section.section} ({section.count})
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-gray-500">Sem seções extraídas.</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Termos de conhecimento</h3>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {pdfKnowledgeTerms.length > 0 ? (
                          pdfKnowledgeTerms.slice(0, 10).map((term) => (
                            <Badge key={term.term} variant="warning">
                              {term.term} ({term.count})
                            </Badge>
                          ))
                        ) : (
                          <span className="text-sm text-gray-500">Sem termos destacados.</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Problema / Solução</h3>
                      <div className="mt-3 space-y-2">
                        {pdfProblemSolutions.length > 0 ? (
                          pdfProblemSolutions.slice(0, 3).map((item, index) => (
                            <div key={`${item.filename || 'doc'}-${index}`} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                              <p className="text-sm font-medium text-gray-900">{item.filename || 'PDF'}</p>
                              <p className="mt-1 text-xs text-gray-500">{item.problem || 'Problema não identificado'}</p>
                              <p className="mt-1 text-xs text-gray-700">{item.solution || 'Solução não identificada'}</p>
                            </div>
                          ))
                        ) : (
                          <span className="text-sm text-gray-500">Sem pares problema/solução.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              )}
            </>
          )}

          {activeSection === 'performance' && (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <Card className="xl:col-span-1">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Distribuição por status</h2>
                    <p className="text-sm text-gray-500">Leitura de fila e maturidade operacional.</p>
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => setActiveSection('tickets')}>
                    Ver tickets
                  </Button>
                </div>
                <div className="mt-4 space-y-3">
                  {statusDistribution.length > 0 ? (
                    statusDistribution.map((item) => (
                      <BarRow key={item.status} label={item.label} value={item.value} total={totals.tickets || 1} />
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados para o recorte atual.</p>
                  )}
                </div>
              </Card>

              <Card className="xl:col-span-1">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Concentração por módulo</h2>
                    <p className="text-sm text-gray-500">Onde a operação está mais pressionada.</p>
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => setActiveSection('modulos')}>
                    Ver módulos
                  </Button>
                </div>
                <div className="mt-4 space-y-3">
                  {modulePerformance.length > 0 ? (
                    modulePerformance.map((module) => (
                      <button
                        key={module.module}
                        type="button"
                        className="block w-full rounded-2xl border border-transparent text-left transition hover:border-[#0d3b66]/20 hover:bg-[#f7fbff]"
                        onClick={() => {
                          setFocusedModuleName(module.module);
                          setActiveSection('modulos');
                        }}
                      >
                        <BarRow key={module.module} label={module.module} value={module.tickets} total={totals.tickets || 1} suffix={`${module.share}%`} />
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados para o recorte atual.</p>
                  )}
                </div>
              </Card>

              <Card className="xl:col-span-1">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Tendência por release</h2>
                    <p className="text-sm text-gray-500">Volume entregue por período de aplicação.</p>
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => setActiveSection('releases')}>
                    Ver releases
                  </Button>
                </div>
                <div className="mt-4 space-y-3">
                  {releasePerformance.length > 0 ? (
                    releasePerformance.map((release) => (
                      <button
                        key={release.id}
                        type="button"
                        className="block w-full rounded-2xl border border-transparent text-left transition hover:border-[#0d3b66]/20 hover:bg-[#f7fbff]"
                        onClick={() => {
                          setFocusedReleaseId(release.id);
                          setSelectedRelease(String(release.id));
                          setActiveSection('releases');
                        }}
                      >
                        <BarRow
                          label={release.release_name}
                          value={release.tickets}
                          total={Math.max(...releasePerformance.map((item) => item.tickets), 1)}
                          suffix={release.applies_on ? release.applies_on.slice(0, 10) : '---'}
                        />
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados para o recorte atual.</p>
                  )}
                </div>
              </Card>
            </div>
          )}

          {activeSection === 'modulos' && (
            <div className="space-y-4">
              <Card>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Resumo Executivo por Módulo</h2>
                    <p className="text-sm text-gray-500">Estrutura inspirada na prestação de contas do PDF.</p>
                  </div>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Módulo</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Versões</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Correções</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Melhorias</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Tickets</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Última versão</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">PDFs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {focusModules.map((module) => (
                        <tr key={module.module} className={report.top_module?.module === module.module ? 'bg-amber-50/60' : ''}>
                          <td className="px-4 py-3 font-medium text-gray-900">{module.module}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.releases}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.corrections}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.improvements}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.tickets}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.latest_version}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{module.pdf_documents ?? 0}</td>
                        </tr>
                      ))}
                      {focusModules.length === 0 && (
                        <tr>
                          <td className="px-4 py-8 text-center text-sm text-gray-500" colSpan={7}>
                            Nenhum módulo encontrado para o recorte selecionado.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {focusModules.map((module) => (
                  <Card
                    key={`${module.module}-detail`}
                    className={[
                      report.top_module?.module === module.module ? 'border-l-4 border-l-[#0d3b66]' : '',
                      focusedModuleName === module.module ? 'ring-2 ring-amber-300' : '',
                    ].join(' ')}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-wider text-gray-500">{module.owner || 'Sem responsável'}</p>
                        <h3 className="text-lg font-semibold text-gray-900">{module.module}</h3>
                        <p className="mt-2 text-sm text-gray-600">{module.description || 'Sem descrição cadastrada.'}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant={module.tickets > 0 ? 'warning' : 'default'}>{module.tickets} tickets</Badge>
                        <p className="mt-2 text-xs text-gray-500">{module.pdf_documents ?? 0} PDFs relacionados</p>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(module.module); setActiveSection('modulos'); }}>
                        Focar módulo
                      </Button>
                      <Button type="button" size="sm" variant="secondary" onClick={() => { setFocusedModuleName(module.module); setActiveSection('executivo'); }}>
                        Ver no executivo
                      </Button>
                    </div>
                    <p className="mt-4 text-sm text-gray-700">{module.explanation || 'Sem explicação gerada.'}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {(module.pdf_topics ?? []).map((topic) => (
                        <Badge key={topic} variant="info">
                          {topic}
                        </Badge>
                      ))}
                      {(module.pdf_topics ?? []).length === 0 && (
                        <span className="text-sm text-gray-500">Sem temas de PDF relacionados.</span>
                      )}
                    </div>
                    <div className="mt-4">
                      <p className="text-sm font-semibold text-gray-700">Tickets-chave</p>
                      <div className="mt-2 space-y-2">
                        {(module.top_tickets ?? []).slice(0, 3).map((ticket) => (
                          <div key={ticket.ticket} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                            <p className="text-sm font-medium text-gray-900">{ticket.ticket}</p>
                            <p className="text-xs text-gray-500">{ticket.tipo_label} | {ticket.status}</p>
                            <p className="mt-1 text-sm text-gray-700">{ticket.title}</p>
                            <p className="mt-1 text-xs text-gray-500">{ticket.descricao || 'Sem descrição.'}</p>
                          </div>
                        ))}
                        {(module.top_tickets ?? []).length === 0 && (
                          <p className="text-sm text-gray-500">Nenhum ticket cadastrado para este módulo.</p>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                <Card title="Módulos sem PDF">
                  {modulesWithoutPdf.length > 0 ? (
                    <ul className="space-y-2 text-sm text-gray-700">
                      {modulesWithoutPdf.map((module) => (
                        <li key={module.module} className="flex items-center justify-between gap-3">
                          <strong>{module.module}</strong> - {module.tickets} ticket(s)
                          <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(module.module); setActiveSection('modulos'); }}>
                            Focar
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">Todos os módulos possuem ao menos um PDF relacionado.</p>
                  )}
                </Card>

                <Card title="Maior volume">
                  {topVolumeModules.length > 0 ? (
                    <ul className="space-y-2 text-sm text-gray-700">
                      {topVolumeModules.map((module) => (
                        <li key={module.module} className="flex items-center justify-between gap-3">
                          <strong>{module.module}</strong> - {module.tickets} ticket(s), {module.releases} release(s)
                          <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(module.module); setActiveSection('modulos'); }}>
                            Focar
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados de volume para o recorte atual.</p>
                  )}
                </Card>

                <Card title="Maior risco / recorrência">
                  {topRiskModules.length > 0 ? (
                    <ul className="space-y-2 text-sm text-gray-700">
                      {topRiskModules.map((module) => (
                        <li key={module.module} className="flex items-center justify-between gap-3">
                          <strong>{module.module}</strong> - {module.corrections} correção(ões), tema {module.themes?.[0]?.theme || 'sem tema'}
                          <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedModuleName(module.module); setActiveSection('modulos'); }}>
                            Focar
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados de risco para o recorte atual.</p>
                  )}
                </Card>
              </div>
            </div>
          )}

          {activeSection === 'releases' && (
            <div className="space-y-4">
              <Card>
                <h2 className="text-xl font-semibold text-gray-900">Visão por Versão</h2>
                <p className="text-sm text-gray-500">Versão, status e volume de tickets por entrega.</p>
              </Card>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {focusReleases.map((release) => (
                  <Card
                    key={release.id}
                    className={[
                      release.tickets > 0 ? 'border-l-4 border-l-[#0d3b66]' : '',
                      focusedReleaseId === release.id ? 'ring-2 ring-sky-300' : '',
                    ].join(' ')}
                  >
                    <div className="flex flex-col gap-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-wider text-gray-500">{release.module}</p>
                          <h3 className="text-lg font-semibold text-gray-900">{release.release_name}</h3>
                          <p className="text-sm text-gray-500">Versão {release.version}</p>
                        </div>
                        <Badge variant={release.tickets > 0 ? 'warning' : 'default'}>{release.tickets} tickets</Badge>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedReleaseId(release.id); setActiveSection('releases'); }}>
                          Ver inteligência
                        </Button>
                        <Button type="button" size="sm" variant="secondary" onClick={() => { setSelectedRelease(String(release.id)); setFocusedReleaseId(release.id); setActiveSection('releases'); }}>
                          Filtrar release
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                        <MiniStat label="Correções" value={release.corrections} />
                        <MiniStat label="Melhorias" value={release.improvements} />
                        <MiniStat label="Última atividade" value={release.last_activity_at ? release.last_activity_at.slice(0, 10) : '---'} />
                        <MiniStat label="Status" value={Object.entries(release.by_status).map(([status, count]) => `${status}: ${count}`).join(' | ') || 'Sem tickets'} />
                      </div>
                    </div>
                  </Card>
                ))}
                {focusReleases.length === 0 && (
                  <Card>
                    <p className="text-sm text-gray-500">Nenhum release encontrado para o recorte selecionado.</p>
                  </Card>
                )}
              </div>
            </div>
          )}

          {activeSection === 'temas' && (
            <Card>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Temas Recorrentes</h2>
                  <p className="text-sm text-gray-500">Classificação automática a partir das descrições e soluções.</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                {focusThemes.map((theme) => (
                  <div
                    key={theme.theme}
                    className={[
                      'rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3',
                      focusedThemeName === theme.theme ? 'ring-2 ring-violet-300' : '',
                    ].join(' ')}
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{theme.count}</Badge>
                      <span className="font-medium text-gray-900">{theme.theme}</span>
                    </div>
                    {theme.examples.length > 0 && (
                      <p className="mt-2 text-xs text-gray-500">Exemplos: {theme.examples.join(', ')}</p>
                    )}
                    <div className="mt-3">
                      <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedThemeName(theme.theme); setActiveSection('temas'); }}>
                        Focar tema
                      </Button>
                    </div>
                  </div>
                ))}
                {focusThemes.length === 0 && <p className="text-sm text-gray-500">Nenhum tema recorrente identificado.</p>}
              </div>
            </Card>
          )}

          {activeSection === 'tickets' && (
            <div className="space-y-4">
              <Card>
                <h2 className="text-xl font-semibold text-gray-900">Tickets e Soluções</h2>
                <p className="text-sm text-gray-500">Base para a leitura executiva, auditoria e histórico de entregas.</p>
              </Card>
              <div className="space-y-4">
                {focusTickets.map((ticket) => (
                  <Card
                    key={`${ticket.ticket}-${ticket.release_id ?? 'na'}`}
                    className={focusedTicketNumber === ticket.ticket ? 'ring-2 ring-emerald-300' : ''}
                  >
                    <div className="flex flex-col gap-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-wider text-gray-500">{ticket.module || 'Sem módulo'}</p>
                          <h3 className="text-lg font-semibold text-gray-900">{ticket.ticket}</h3>
                          <p className="text-sm text-gray-500">{ticket.title || ticket.descricao || 'Sem título'}</p>
                        </div>
                        <div className="flex flex-wrap justify-end gap-2">
                          {ticket.status && <Badge variant="info">{ticket.status}</Badge>}
                          <TipoBadge tipo={ticket.tipo} />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => { setFocusedTicketNumber(ticket.ticket); setActiveSection('tickets'); }}>
                          Focar ticket
                        </Button>
                        <Button type="button" size="sm" variant="secondary" onClick={() => { setFocusedTicketNumber(ticket.ticket); setActiveSection('executivo'); }}>
                          Resumir no executivo
                        </Button>
                      </div>
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div>
                          <p className="text-sm font-semibold text-gray-500">Descrição / Problema</p>
                          <p className="mt-1 text-sm text-gray-900">{ticket.descricao || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-500">Solução Aplicada</p>
                          <p className="mt-1 text-sm text-gray-900">{ticket.resolucao || 'N/A'}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                        {ticket.release && <span>Versão: {ticket.release}</span>}
                        {ticket.version && <span>Versão: {ticket.version}</span>}
                      </div>
                    </div>
                  </Card>
                ))}
                {focusTickets.length === 0 && <p className="text-center text-sm text-gray-500">Nenhum ticket encontrado</p>}
              </div>
            </div>
          )}
        </div>
      ) : null}

      {textPreview && (
        <Card>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Saída textual gerada</h2>
              <p className="text-sm text-gray-500">Versão legível do relatório para cópia rápida e auditoria.</p>
            </div>
            <Button type="button" variant="outline" onClick={() => setTextPreview('')}>
              Fechar
            </Button>
          </div>
          <pre className="mt-4 max-h-[480px] overflow-auto whitespace-pre-wrap rounded-2xl bg-gray-950 p-4 text-sm text-gray-100">
            {textPreview}
          </pre>
        </Card>
      )}
    </div>
  );
}

function MetricCard({ title, value, tone }: { title: string; value: number; tone: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white p-4 shadow-sm">
      <div className={`h-1 w-12 rounded-full ${tone}`} />
      <p className="mt-4 text-sm font-medium text-gray-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-gray-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function MiniAudit({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-base font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function MiniCycleMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2 shadow-sm">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function AuditList({ title, items }: { title: string; items: Array<{ filename?: string; scope_label?: string | null; audit_state?: string }> }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.slice(0, 5).map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-xl bg-white px-3 py-2 shadow-sm">
            <p className="text-sm font-medium text-gray-900">{item.filename || 'Documento'}</p>
            <p className="text-xs text-gray-500">{item.scope_label || 'Sem recorte'} • {item.audit_state || '—'}</p>
          </div>
        )) : (
          <p className="text-sm text-gray-500">Nenhum item neste grupo.</p>
        )}
      </div>
    </div>
  );
}

function BarRow({ label, value, total, suffix }: { label: string; value: number; total: number; suffix?: string }) {
  const pct = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-gray-900">{label}</span>
        <span className="text-gray-500">
          {value}
          {suffix ? ` • ${suffix}` : ''}
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-[#0d3b66]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function severityVariant(severity: 'info' | 'warning' | 'success' | 'danger') {
  const variants: Record<'info' | 'warning' | 'success' | 'danger', 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    info: 'info',
    warning: 'warning',
    success: 'success',
    danger: 'danger',
  };

  return variants[severity];
}

function statusLabel(status: string) {
  return {
    backlog: 'Pendente',
    em_andamento: 'Em Andamento',
    em_revisao: 'Em Revisão',
    concluida: 'Concluída',
    bloqueada: 'Bloqueada',
  }[status] || status;
}
