import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { atividadeApi, getAuthUser, summaryApi, playbooksApi, pdfIntelligenceApi, reportsApi } from '../services/api';
import { StatCard, PdfUploadCard, Card, Badge, Button, Select, CycleTimelineCard, ExecutiveInsightDrawer } from '../components';
import type { Summary, PlaybookDashboard } from '../types';

export function Dashboard() {
  const queryClient = useQueryClient();
  const user = getAuthUser();
  const dashboardFocusRef = useRef<HTMLDivElement | null>(null);
  const [dashboardFocus, setDashboardFocus] = useState<'operacao' | 'atividades' | 'playbooks' | 'pdfs' | 'alertas'>('operacao');
  const [activityPeriod, setActivityPeriod] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [activityOwnerFilter, setActivityOwnerFilter] = useState<string>('all');
  const [timelineFocusLabel, setTimelineFocusLabel] = useState<string | null>(null);
  const [selectedCycleId, setSelectedCycleId] = useState<string>('');
  const [drawerContent, setDrawerContent] = useState<{
    title: string;
    subtitle?: string;
    badge?: string;
    metrics?: Array<{ label: string; value: string | number }>;
    bullets?: string[];
  } | null>(null);
  const getActivityPerson = (activity: { owner?: string | null; executor?: string | null }) => {
    const raw = (activity.executor || activity.owner || '').trim();
    if (!raw) {
      return 'Sem responsável';
    }
    return raw
      .split(/\s+/)
      .map((part) => (part ? part[0].toUpperCase() + part.slice(1).toLowerCase() : part))
      .join(' ');
  };
  const { data: summary, isLoading } = useQuery<Summary>({
    queryKey: ['summary'],
    queryFn: () => summaryApi.get(),
  });
  const { data: selectedSummary } = useQuery<Summary>({
    queryKey: ['summary', selectedCycleId],
    queryFn: () => summaryApi.get(selectedCycleId ? Number(selectedCycleId) : undefined),
  });

  const { data: activities = [] } = useQuery({
    queryKey: ['atividade'],
    queryFn: () => atividadeApi.list(),
  });

  const { data: playbookDashboard } = useQuery<PlaybookDashboard>({
    queryKey: ['playbooks', 'dashboard', selectedCycleId],
    queryFn: () => playbooksApi.dashboard(selectedCycleId ? Number(selectedCycleId) : undefined),
  });

  const { data: pdfContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });
  const { data: reportCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles'],
    queryFn: () => reportsApi.cycles(),
  });
  const openCycle = reportCycles.find((cycle) => cycle.status === 'aberto') ?? null;
  const previousCycle = useMemo(() => {
    const closed = reportCycles.filter((cycle) => cycle.status === 'prestado');
    return closed[0] ?? null;
  }, [reportCycles]);
  const reportCycleId = selectedCycleId ? Number(selectedCycleId) : openCycle?.id;
  const selectedCycle = useMemo(
    () => reportCycles.find((cycle) => String(cycle.id) === selectedCycleId) ?? null,
    [reportCycles, selectedCycleId]
  );
  const cycleSummary = selectedSummary?.selected_cycle ?? null;
  const alertCards = useMemo(() => (pdfContext?.predictions ?? []).slice(0, 3), [pdfContext?.predictions]);
  const periodOptions = [
    { value: '7d', label: '7 dias' },
    { value: '30d', label: '30 dias' },
    { value: '90d', label: '90 dias' },
    { value: 'all', label: 'Todo período' },
  ];

  const activityOwnerOptions = useMemo(() => {
    const owners = new Set<string>();
    activities.forEach((activity) => {
      if (activity.status === 'concluida') {
        owners.add(getActivityPerson(activity));
      }
    });
    return [{ value: 'all', label: 'Todos os executantes' }, ...Array.from(owners).sort().map((owner) => ({ value: owner, label: owner }))];
  }, [activities]);

  const completedTasks = useMemo(() => {
    const now = Date.now();
    const periodDays = activityPeriod === '7d' ? 7 : activityPeriod === '30d' ? 30 : activityPeriod === '90d' ? 90 : null;
    const lowerBound = periodDays ? now - periodDays * 24 * 60 * 60 * 1000 : null;

    return activities.filter((activity) => {
      if (activity.status !== 'concluida') {
        return false;
      }
      const person = getActivityPerson(activity);
      if (activityOwnerFilter !== 'all' && person !== activityOwnerFilter) {
        return false;
      }
      if (!lowerBound) {
        return true;
      }
      const completionDate = new Date(activity.completed_at || activity.updated_at || activity.created_at || '');
      if (Number.isNaN(completionDate.getTime())) {
        return true;
      }
      return completionDate.getTime() >= lowerBound;
    });
  }, [activities, activityOwnerFilter, activityPeriod]);

  const completedTasksByOwner = useMemo(() => {
    const grouped = new Map<string, number>();
    completedTasks.forEach((activity) => {
      const person = getActivityPerson(activity);
      grouped.set(person, (grouped.get(person) || 0) + 1);
    });
    return Array.from(grouped.entries())
      .map(([owner, count]) => ({ owner, count }))
      .sort((a, b) => b.count - a.count || a.owner.localeCompare(b.owner));
  }, [completedTasks]);

  const selectedCycleTasksByOwner = cycleSummary?.completed_tasks_by_owner ?? null;
  const tasksByOwnerForView = selectedCycleTasksByOwner ?? completedTasksByOwner;
  const selectedCompletedTasksTotal = cycleSummary?.completed_tasks_total ?? completedTasks.length;
  const chartMax = Math.max(...tasksByOwnerForView.map((item) => item.count), 1);

  useEffect(() => {
    dashboardFocusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [dashboardFocus]);

  const focusSummary = useMemo(() => {
    switch (dashboardFocus) {
      case 'atividades':
        return {
          title: 'Foco em atividades',
          subtitle: 'Mostra tarefas concluídas, responsáveis e pressão operacional.',
          primary: `${selectedCompletedTasksTotal} concluídas`,
          secondary: `${tasksByOwnerForView.length} executante(s)`,
          bullets: [
            activityOwnerFilter === 'all' ? 'Nenhum executante filtrado.' : `Filtro ativo: ${activityOwnerFilter}.`,
            activityPeriod === 'all' ? 'Recorte total da operação.' : `Período atual: ${activityPeriod}.`,
            tasksByOwnerForView[0] ? `${tasksByOwnerForView[0].owner} lidera o volume concluído.` : 'Sem tarefas concluídas no recorte.',
          ],
        };
      case 'playbooks':
        return {
          title: 'Foco em guias',
          subtitle: 'Liga a cobertura, riscos e ações preditivas ao aprendizado operacional.',
          primary: `${playbookDashboard?.totals?.playbooks ?? 0} guias`,
          secondary: `${playbookDashboard?.totals?.predictions ?? 0} preditivos`,
          bullets: [
            (playbookDashboard?.ranking ?? []).length > 0 ? `Top risco: ${(playbookDashboard?.ranking ?? [])[0]?.erro || 'N/A'}.` : 'Sem ranking de risco disponível.',
            (playbookDashboard?.coverage?.areas_sem_documentacao ?? []).length > 0 ? `${playbookDashboard?.coverage?.areas_sem_documentacao?.length} área(s) sem documentação.` : 'Cobertura completa no recorte atual.',
            (playbookDashboard?.suggestions ?? []).length > 0 ? `${playbookDashboard?.suggestions?.length} sugestão(ões) automática(s) prontas.` : 'Sem sugestões automáticas no momento.',
          ],
        };
      case 'pdfs':
        return {
          title: 'Foco em PDFs',
          subtitle: 'Mostra o ciclo atual, histórico e o motor de inteligência local.',
          primary: `${pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0} no ciclo`,
          secondary: `${pdfContext?.themes?.length ?? 0} temas`,
          bullets: [
            pdfContext?.cycle?.status === 'prestado' ? 'Ciclo fechado, próximo processamento abre novo ciclo.' : 'Ciclo aberto para novos arquivos.',
            pdfContext?.predictions?.length ? `${pdfContext.predictions.length} previsão(ões) calculadas localmente.` : 'Sem previsões calculadas ainda.',
            pdfContext?.recommendations?.[0] || 'Sem recomendação adicional.',
          ],
        };
      case 'alertas':
        return {
          title: 'Foco em alertas',
          subtitle: 'As previsões viram ação e podem gerar playbooks diretamente.',
          primary: `${pdfContext?.predictions?.length ?? 0} alertas`,
          secondary: `${playbookDashboard?.totals?.predictions ?? 0} guias preditivos`,
          bullets: [
            (pdfContext?.predictions ?? []).slice(0, 1)[0]?.title || 'Sem alerta destacado.',
            (pdfContext?.predictions ?? []).slice(0, 1)[0]?.action || 'Sem ação recomendada.',
            'Use o botão para gerar guias preditivos a partir desta inteligência.',
          ],
        };
      case 'operacao':
      default:
        return {
          title: 'Foco operacional',
          subtitle: 'Visão geral do sistema com atalhos inteligentes.',
          primary: `${cycleSummary?.releases ?? summary?.releases ?? 0} releases`,
          secondary: `${cycleSummary?.label ? 'Ciclo em foco' : `${summary?.clientes ?? 0} clientes`}`,
          bullets: [
            cycleSummary
              ? `Ciclo em foco: ${cycleSummary.label} · Homologações ${cycleSummary.homologacoes} · Customizações ${cycleSummary.customizacoes}.`
              : `Homologações: ${summary?.homologacoes ?? 0} | Customizações: ${summary?.customizacoes ?? 0}.`,
            cycleSummary
              ? `Atividades do ciclo em foco: ${cycleSummary.atividades} · Concluídas: ${cycleSummary.completed_tasks_total ?? 0}.`
              : `Atividades concluídas no recorte: ${completedTasks.length}.`,
            selectedCycle ? `Ciclo histórico em foco: ${selectedCycle.period_label || `Prestação ${selectedCycle.cycle_number || selectedCycle.id}`}.` : `Ciclo aberto: ${openCycle?.period_label || 'Sem ciclo operacional aberto'}.`,
            `PDFs do ciclo: ${pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0}.`,
          ],
        };
    }
  }, [
    activityOwnerFilter,
    activityPeriod,
    completedTasks.length,
    completedTasksByOwner,
    dashboardFocus,
    pdfContext?.cycle?.status,
    pdfContext?.cycle_documents,
    pdfContext?.predictions,
    pdfContext?.recommendations,
    pdfContext?.themes?.length,
    pdfContext?.total_documents,
    playbookDashboard?.coverage?.areas_sem_documentacao,
    playbookDashboard?.ranking,
    playbookDashboard?.suggestions,
    playbookDashboard?.totals?.playbooks,
    playbookDashboard?.totals?.predictions,
    openCycle?.period_label,
    selectedCycle?.cycle_number,
    selectedCycle?.id,
    selectedCycle?.period_label,
    cycleSummary,
    selectedCompletedTasksTotal,
    tasksByOwnerForView,
    summary?.clientes,
    summary?.customizacoes,
    summary?.homologacoes,
    summary?.releases,
  ]);

  const generatePredictionsMutation = useMutation({
    mutationFn: playbooksApi.generatePredictions,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
      ]);
    },
  });

  const exportDashboardReportText = async () => {
    await reportsApi.summaryText(undefined, reportCycleId);
  };

  const openDashboardReportHtml = async () => {
    const result = await reportsApi.htmlReport(undefined, undefined, reportCycleId);
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const downloadDashboardReportPdf = async () => {
    const blob = await reportsApi.pdfReport(undefined, undefined, reportCycleId);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = reportCycleId ? `relatorio-ciclo-${reportCycleId}.pdf` : 'relatorio-gerencial.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d3b66]"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Painel</h1>
          <p className="mt-1 text-gray-500">Visão geral do sistema CS CONTROLE 360</p>
        </div>
      </div>

      <Card className="border-l-4 border-l-[#0d3b66]">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Ciclo operacional</p>
            <h2 className="mt-1 text-lg font-semibold text-gray-900">
              {openCycle ? `Mês em trabalho: ${openCycle.period_label || `Prestação ${openCycle.cycle_number || openCycle.id}`}` : 'Sem mês operacional aberto'}
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              {summary?.previous_cycle?.label
                ? `Mês anterior consolidado: ${summary.previous_cycle.label}.`
                : 'Nenhum mês anterior consolidado disponível.'}
            </p>
            {selectedCycle && (
              <p className="mt-1 text-xs font-semibold text-[#0d3b66]">
                Ciclo histórico em foco: {selectedCycle.period_label || `Prestação ${selectedCycle.cycle_number || selectedCycle.id}`}
              </p>
            )}
            {timelineFocusLabel && (
              <p className="mt-1 text-xs font-semibold text-[#0d3b66]">
                Linha do tempo em foco: {timelineFocusLabel}
              </p>
            )}
          </div>
          <Badge variant={openCycle ? 'success' : 'warning'}>
            {openCycle ? 'Mês ativo' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>

      <CycleTimelineCard
        title="Governança de ciclo"
          description="O painel segue a mesma leitura de prestação: mês atual em operação, mês anterior consolidado e histórico visível para comparação."
        currentCycle={openCycle}
        previousCycle={previousCycle}
        cycles={reportCycles}
        selectedCycleId={selectedCycleId}
        onSelectCycle={(cycleId) => {
          setSelectedCycleId(cycleId);
          const cycle = reportCycles.find((item) => String(item.id) === cycleId);
          if (cycle) {
            setTimelineFocusLabel(cycle.period_label || `Prestação ${cycle.cycle_number || cycle.id}`);
          }
          setDashboardFocus('operacao');
        }}
        onOpenPrevious={() => {
          if (previousCycle) {
            setSelectedCycleId(String(previousCycle.id));
            setTimelineFocusLabel(previousCycle.period_label || `Prestação ${previousCycle.cycle_number || previousCycle.id}`);
            setDashboardFocus('operacao');
          }
        }}
        onOpenCurrent={() => {
          if (openCycle) {
            setSelectedCycleId('');
            setTimelineFocusLabel(openCycle.period_label || `Prestação ${openCycle.cycle_number || openCycle.id}`);
            setDashboardFocus('operacao');
          }
        }}
      />

      <Card title="Comparativo de ciclos">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-[#0d3b66]/15 bg-[#f8fbff] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês atual</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">
                  {summary?.current_cycle?.label || openCycle?.period_label || 'Sem referência'}
                </h3>
              </div>
              <Badge variant="success">Aberto</Badge>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniMetric label="Homologações" value={summary?.current_cycle?.homologacoes ?? 0} />
              <MiniMetric label="Customizações" value={summary?.current_cycle?.customizacoes ?? 0} />
              <MiniMetric label="Atividades" value={summary?.current_cycle?.atividades ?? 0} />
              <MiniMetric label="Versões" value={summary?.current_cycle?.releases ?? 0} />
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês anterior</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">
                  {summary?.previous_cycle?.label || 'Sem referência'}
                </h3>
              </div>
              <Badge variant="warning">Fechado</Badge>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniMetric label="Homologações" value={summary?.previous_cycle?.homologacoes ?? 0} />
              <MiniMetric label="Customizações" value={summary?.previous_cycle?.customizacoes ?? 0} />
              <MiniMetric label="Atividades" value={summary?.previous_cycle?.atividades ?? 0} />
              <MiniMetric label="Versões" value={summary?.previous_cycle?.releases ?? 0} />
            </div>
          </div>
        </div>
      </Card>

      {cycleSummary && (
        <Card title="Ciclo histórico em foco">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <MiniMetric label="Homologações" value={cycleSummary.homologacoes} />
            <MiniMetric label="Customizações" value={cycleSummary.customizacoes} />
            <MiniMetric label="Atividades" value={cycleSummary.atividades} />
            <MiniMetric label="Versões" value={cycleSummary.releases} />
          </div>
          <div className="mt-4">
            <p className="text-sm font-semibold text-gray-900">Tarefas concluídas por executante no ciclo em foco</p>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {(cycleSummary.completed_tasks_by_owner ?? []).slice(0, 6).map((item) => (
                <div key={`${item.owner}-${item.count}`} className="rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-gray-900">{item.owner}</span>
                    <Badge variant="info">{item.count}</Badge>
                  </div>
                </div>
              ))}
              {(cycleSummary.completed_tasks_by_owner ?? []).length === 0 && (
                <p className="text-sm text-gray-500">Nenhuma tarefa concluída encontrada nesse ciclo.</p>
              )}
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-4">
        <Link to="/homologacao">
          <StatCard title="Homologações" value={summary?.homologacoes ?? 0} />
        </Link>
        <Link to="/customizacao">
          <StatCard title="Customizações" value={summary?.customizacoes ?? 0} />
        </Link>
        <Link to="/atividade">
          <StatCard title="Atividades" value={summary?.atividades ?? 0} />
        </Link>
        <Link to="/release">
          <StatCard title="Versões" value={summary?.releases ?? 0} />
        </Link>
        {user?.role === 'admin' ? (
          <Link to="/admin">
            <StatCard title="Clientes" value={summary?.clientes ?? 0} />
          </Link>
        ) : (
          <StatCard title="Clientes" value={summary?.clientes ?? 0} />
        )}
        {user?.role === 'admin' ? (
          <Link to="/admin">
            <StatCard title="Módulos" value={summary?.modulos ?? 0} />
          </Link>
        ) : (
          <StatCard title="Módulos" value={summary?.modulos ?? 0} />
        )}
        <Link to="/playbooks">
          <StatCard title="Guias" value={playbookDashboard?.totals?.playbooks ?? 0} />
        </Link>
        <Link to="/relatorios">
          <StatCard title="PDFs do ciclo" value={pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0} />
        </Link>
      </div>

      <div ref={dashboardFocusRef}>
        <Card className="border-l-4 border-l-[#0d3b66]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-[0.35em] text-gray-500">Foco do painel</p>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900">{focusSummary.title}</h2>
              <p className="mt-2 text-sm text-gray-600">{focusSummary.subtitle}</p>
            </div>
            <div className="grid w-full gap-3 sm:grid-cols-2 lg:max-w-xl">
              <div className="rounded-2xl bg-gray-50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Principal</p>
                <p className="mt-1 text-base font-semibold text-gray-900">{focusSummary.primary}</p>
              </div>
              <div className="rounded-2xl bg-gray-50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Secundário</p>
                <p className="mt-1 text-base font-semibold text-gray-900">{focusSummary.secondary}</p>
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => void exportDashboardReportText()}>
              Texto do ciclo
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void openDashboardReportHtml()}>
              HTML do ciclo
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void downloadDashboardReportPdf()}>
              PDF do ciclo
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() =>
                setDrawerContent({
                  title: focusSummary.title,
                  subtitle: focusSummary.subtitle,
                  badge: 'Foco executivo',
                  metrics: [
                    { label: 'Principal', value: focusSummary.primary },
                    { label: 'Secundário', value: focusSummary.secondary },
                  ],
                  bullets: focusSummary.bullets,
                })
              }
            >
              Abrir drawer executivo
            </Button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {focusSummary.bullets.map((bullet, index) => (
              <div key={`${focusSummary.title}-${index}`} className="rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Inteligência {index + 1}</p>
                <p className="mt-1 text-sm text-gray-700">{bullet}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" size="sm" variant={dashboardFocus === 'operacao' ? 'primary' : 'outline'} onClick={() => setDashboardFocus('operacao')}>
              Operação
            </Button>
            <Button type="button" size="sm" variant={dashboardFocus === 'atividades' ? 'primary' : 'outline'} onClick={() => setDashboardFocus('atividades')}>
              Atividades
            </Button>
            <Button type="button" size="sm" variant={dashboardFocus === 'playbooks' ? 'primary' : 'outline'} onClick={() => setDashboardFocus('playbooks')}>
              Guias
            </Button>
            <Button type="button" size="sm" variant={dashboardFocus === 'pdfs' ? 'primary' : 'outline'} onClick={() => setDashboardFocus('pdfs')}>
              PDFs
            </Button>
            <Button type="button" size="sm" variant={dashboardFocus === 'alertas' ? 'primary' : 'outline'} onClick={() => setDashboardFocus('alertas')}>
              Alertas
            </Button>
          </div>
        </Card>
      </div>

      <PdfUploadCard scopeType="global" scopeLabel="Painel" />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Links Rápidos</h2>
          <div className="space-y-3">
            <Link to="/homologacao" className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="p-2 bg-blue-100 rounded-lg mr-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Homologações</p>
                <p className="text-sm text-gray-500">Gerenciar controle de versão</p>
              </div>
            </Link>
            <Link to="/release" className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="p-2 bg-green-100 rounded-lg mr-3">
                <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Versões</p>
                <p className="text-sm text-gray-500">Gerenciar versões e notas</p>
              </div>
            </Link>
            <Link to="/relatorios" className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="p-2 bg-purple-100 rounded-lg mr-3">
                <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Relatórios</p>
                <p className="text-sm text-gray-500">Gerar relatórios gerenciais</p>
              </div>
            </Link>
            <Link to="/playbooks" className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="p-2 bg-amber-100 rounded-lg mr-3">
                <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 20h9" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Guias</p>
                <p className="text-sm text-gray-500">Criar conhecimento operacional</p>
              </div>
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Sistema</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-gray-600">Versão</span>
              <span className="font-medium text-gray-900">2.0.0</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-gray-600">Status</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Operacional
              </span>
            </div>
          </div>
        </div>

        <Card title="Guias Inteligentes" className="xl:col-span-1">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">Motor de conhecimento</p>
                <p className="text-xs text-gray-500">Clique para focar guias, riscos e previsões.</p>
              </div>
              <Button type="button" size="sm" variant="outline" onClick={() => setDashboardFocus('playbooks')}>
                Focar
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <MiniStat label="Cobertura de processos" value={`${playbookDashboard?.coverage?.processos ?? 0}%`} />
              <MiniStat label="Cobertura de erros" value={`${playbookDashboard?.coverage?.erros ?? 0}%`} />
              <MiniStat label="Pendências" value={playbookDashboard?.coverage?.areas_sem_documentacao?.length ?? 0} />
              <MiniStat label="Guias ativos" value={playbookDashboard?.totals?.playbooks ?? 0} />
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Riscos críticos</p>
              <div className="mt-3 space-y-2">
                {(playbookDashboard?.ranking ?? []).slice(0, 4).map((item) => (
                  <button
                    key={item.erro}
                    type="button"
                    className="w-full rounded-lg border border-gray-200 bg-gray-50 p-3 text-left transition hover:border-[#0d3b66]/30 hover:bg-[#f7fbff]"
                    onClick={() => setDashboardFocus('playbooks')}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.erro}</p>
                        <p className="text-xs text-gray-500">
                          Score {item.score} | Impacto {item.impacto} | Freq. {item.frequencia}
                        </p>
                      </div>
                      <Badge variant={item.playbook_criado === 'Sim' ? 'success' : 'warning'}>
                        {item.playbook_criado === 'Sim' ? 'Coberto' : 'Pendente'}
                      </Badge>
                    </div>
                  </button>
                ))}
                {(playbookDashboard?.ranking ?? []).length === 0 && (
                  <p className="text-sm text-gray-500">Sem riscos avaliados ainda.</p>
                )}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Pendências sem playbook</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(playbookDashboard?.coverage?.areas_sem_documentacao ?? []).length > 0 ? (
                  playbookDashboard?.coverage?.areas_sem_documentacao?.map((area) => (
                    <Badge key={area} variant="warning">{area}</Badge>
                  ))
                ) : (
                  <span className="text-sm text-gray-500">Nenhuma pendência crítica.</span>
                )}
              </div>
            </div>

            <div>
              <Link to="/playbooks" className="inline-flex items-center text-sm font-medium text-[#0d3b66] hover:underline">
                Abrir painel de Guias
              </Link>
            </div>
          </div>
        </Card>

        <Card title="Inteligência de PDFs" className="xl:col-span-1">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" variant="outline" onClick={() => void exportDashboardReportText()}>
                Texto do ciclo
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => void openDashboardReportHtml()}>
                HTML do ciclo
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => void downloadDashboardReportPdf()}>
                PDF do ciclo
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <MiniStat label="Documentos do ciclo" value={pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0} />
              <MiniStat label="Histórico" value={pdfContext?.all_time_documents ?? pdfContext?.total_documents ?? 0} />
              <MiniStat label="Páginas" value={pdfContext?.totals?.pages ?? 0} />
              <MiniStat label="Tickets" value={pdfContext?.totals?.tickets ?? 0} />
              <MiniStat label="Temas" value={pdfContext?.themes?.length ?? 0} />
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-gray-900">Ciclo atual</p>
                <Badge variant={pdfContext?.cycle?.status === 'prestado' ? 'warning' : 'success'}>
                  {pdfContext?.cycle?.status || 'aberto'}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                {pdfContext?.cycle?.period_label || 'Leitura contínua com cache por hash'}
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Temas globais</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(pdfContext?.themes ?? []).slice(0, 6).map((theme) => (
                  <Badge key={theme.theme} variant="info">
                    {theme.theme} ({theme.count})
                  </Badge>
                ))}
                {(pdfContext?.themes ?? []).length === 0 && (
                  <span className="text-sm text-gray-500">Nenhum PDF processado ainda.</span>
                )}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Recomendações da base</p>
              <ul className="mt-3 space-y-2 text-sm text-gray-700">
                {(pdfContext?.recommendations ?? []).slice(0, 4).map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Previsões preditivas</p>
              <div className="mt-3 space-y-2">
                {(pdfContext?.predictions ?? []).slice(0, 4).map((item) => (
                  <div key={item.title} className="rounded-lg border border-gray-200 bg-white p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.title}</p>
                        <p className="text-xs text-gray-500 mt-1">{item.detail}</p>
                      </div>
                      <Badge variant={item.confidence >= 80 ? 'danger' : item.confidence >= 60 ? 'warning' : 'info'}>
                        {item.confidence}%
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-gray-600">{item.action}</p>
                  </div>
                ))}
                {(pdfContext?.predictions ?? []).length === 0 && (
                  <p className="text-sm text-gray-500">Sem previsões calculadas ainda.</p>
                )}
              </div>
            </div>
          </div>
        </Card>

      <Card title="Tarefas concluídas" className="xl:col-span-1">
          <div className="space-y-3">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-gray-900">Tarefas feitas</p>
                <Badge variant="success">{selectedCompletedTasksTotal}</Badge>
              </div>
              <p className="mt-1 text-xs text-gray-500">Filtradas por período e responsável.</p>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Select
                label="Período"
                value={activityPeriod}
                onChange={(e) => setActivityPeriod(e.target.value as '7d' | '30d' | '90d' | 'all')}
                options={periodOptions}
              />
              <Select
                label="Executante"
                value={activityOwnerFilter}
                onChange={(e) => setActivityOwnerFilter(e.target.value)}
                options={activityOwnerOptions}
              />
            </div>

            <div className="space-y-3 pt-2">
              {tasksByOwnerForView.length > 0 ? (
                tasksByOwnerForView.slice(0, 8).map((item) => (
                  <button
                    key={item.owner}
                    type="button"
                    className="w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-left transition hover:border-[#0d3b66]/30 hover:bg-[#f7fbff]"
                    onClick={() => {
                      setActivityOwnerFilter(item.owner);
                      setDashboardFocus('atividades');
                    }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.owner}</p>
                        <p className="text-xs text-gray-500">Tarefas feitas</p>
                      </div>
                      <Badge variant={item.count >= 10 ? 'success' : item.count >= 5 ? 'warning' : 'info'}>
                        {item.count}
                      </Badge>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-[#0d3b66]"
                        style={{ width: `${(item.count / chartMax) * 100}%` }}
                      />
                    </div>
                  </button>
                ))
              ) : (
                <p className="text-sm text-gray-500">Nenhuma tarefa concluída no recorte selecionado.</p>
              )}
            </div>
          </div>
        </Card>
      </div>

      <Card title="Alertas Inteligentes">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-gray-500">Previsões locais transformadas em alertas e playbooks.</p>
          </div>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => setDashboardFocus('alertas')}>
              Focar alertas
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => generatePredictionsMutation.mutate()}
              disabled={generatePredictionsMutation.isPending}
            >
              {generatePredictionsMutation.isPending ? 'Gerando...' : 'Gerar guias preditivos'}
            </Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {alertCards.map((item) => (
            <button
              key={item.title}
              type="button"
              className={`rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ${
                item.confidence >= 80
                  ? 'border-red-200 bg-red-50'
                  : item.confidence >= 60
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-sky-200 bg-sky-50'
              }`}
              onClick={() => setDashboardFocus('alertas')}
              >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{item.title}</p>
                  <p className="mt-1 text-xs text-gray-500">{item.detail}</p>
                </div>
                <Badge variant={item.confidence >= 80 ? 'danger' : item.confidence >= 60 ? 'warning' : 'info'}>
                  {item.confidence}%
                </Badge>
              </div>
              <p className="mt-3 text-xs text-gray-600">{item.action}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={(event) => {
                    event.stopPropagation();
                    setDrawerContent({
                      title: item.title,
                      subtitle: item.detail,
                      badge: 'Alerta inteligente',
                      metrics: [
                        { label: 'Confiança', value: `${item.confidence}%` },
                        { label: 'Ação', value: item.action },
                      ],
                      bullets: [
                        item.detail,
                        item.action,
                        'Exportação direta do ciclo disponível no bloco superior.',
                      ],
                    });
                  }}
                >
                  Detalhar
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={(event) => {
                    event.stopPropagation();
                    void exportDashboardReportText();
                  }}
                >
                  Texto
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={(event) => {
                    event.stopPropagation();
                    void openDashboardReportHtml();
                  }}
                >
                  HTML
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={(event) => {
                    event.stopPropagation();
                    void downloadDashboardReportPdf();
                  }}
                >
                  PDF
                </Button>
              </div>
            </button>
          ))}
          {(pdfContext?.predictions ?? []).length === 0 && (
            <p className="text-sm text-gray-500">Nenhum alerta disponível no momento.</p>
          )}
        </div>
      </Card>

      <ExecutiveInsightDrawer
        open={Boolean(drawerContent)}
        title={drawerContent?.title || ''}
        subtitle={drawerContent?.subtitle}
        badge={drawerContent?.badge}
        metrics={drawerContent?.metrics}
        bullets={drawerContent?.bullets}
        onClose={() => setDrawerContent(null)}
      />

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

function MiniMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2 shadow-sm">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}
