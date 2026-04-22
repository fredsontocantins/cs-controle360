import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi, releaseApi, playbooksApi, reportsApi } from '../services/api';
import { Badge, Button, Card, Input, Select, Textarea, PdfUploadCard, CycleTimelineCard } from '../components';
import type { Playbook } from '../types';

type Section = 'manual' | 'erro' | 'release' | 'lista' | 'dashboard' | 'sugestoes' | 'predicoes';

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

export function Playbooks() {
  const queryClient = useQueryClient();
  const focusRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const [section, setSection] = useState<Section>('dashboard');
  const [selectedRelease, setSelectedRelease] = useState<string>('');
  const [selectedCycleId, setSelectedCycleId] = useState<string>('');
  const [closedPeriodLabel, setClosedPeriodLabel] = useState<string>('');
  const [nextPeriodLabel, setNextPeriodLabel] = useState<string>('');
  const [focusedPlaybookId, setFocusedPlaybookId] = useState<number | null>(null);
  const [focusedSuggestion, setFocusedSuggestion] = useState<string | null>(null);
  const [focusedPredictionTitle, setFocusedPredictionTitle] = useState<string | null>(null);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: playbooks = [] } = useQuery({
    queryKey: ['playbooks', selectedCycleId],
    queryFn: () => playbooksApi.list(selectedCycleId ? Number(selectedCycleId) : undefined),
  });

  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['playbooks', 'dashboard', selectedCycleId],
    queryFn: () => playbooksApi.dashboard(selectedCycleId ? Number(selectedCycleId) : undefined),
  });

  const { data: suggestionsData } = useQuery({
    queryKey: ['playbooks', 'suggestions', selectedCycleId],
    queryFn: () => playbooksApi.suggestions(selectedCycleId ? Number(selectedCycleId) : undefined),
  });

  const { data: pdfContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });

  const { data: currentCycle } = useQuery({
    queryKey: ['report-cycle', selectedRelease],
    queryFn: () => reportsApi.cycle(selectedRelease ? Number(selectedRelease) : undefined),
  });
  const cycle = currentCycle?.cycle ?? null;
  const { data: reportCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles'],
    queryFn: () => reportsApi.cycles(),
  });
  const openCycle = reportCycles.find((item) => item.status === 'aberto') ?? cycle;
  const reportCycleId = selectedCycleId ? Number(selectedCycleId) : openCycle?.id;
  const previousClosedCycle = useMemo(() => {
    const closed = reportCycles.filter((item) => item.status === 'prestado');
    if (closed.length === 0) {
      return null;
    }
    return closed[0];
  }, [reportCycles]);
  const selectedCycle = useMemo(
    () => reportCycles.find((item) => String(item.id) === selectedCycleId) ?? null,
    [reportCycles, selectedCycleId],
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
  const focusedPlaybook = useMemo(
    () => playbooks.find((item) => item.id === focusedPlaybookId) ?? null,
    [focusedPlaybookId, playbooks],
  );
  const focusedPrediction = useMemo(
    () => (pdfContext?.predictions ?? []).find((item) => item.title === focusedPredictionTitle) ?? null,
    [focusedPredictionTitle, pdfContext?.predictions],
  );

  const exportPlaybookReportText = async () => {
    await reportsApi.summaryText(undefined, reportCycleId);
  };

  const openPlaybookReportHtml = async () => {
    const result = await reportsApi.htmlReport(undefined, undefined, reportCycleId);
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const downloadPlaybookReportPdf = async () => {
    const blob = await reportsApi.pdfReport(undefined, undefined, reportCycleId);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = reportCycleId ? `playbooks-ciclo-${reportCycleId}.pdf` : 'playbooks-relatorio.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const handleClosedMonthChange = (value: string) => {
    setClosedPeriodLabel(value);
    const suggested = getNextMonthLabel(value);
    if (suggested) {
      setNextPeriodLabel(suggested);
    }
  };

  useEffect(() => {
    if (section === 'lista') {
      listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    focusRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [section, focusedPlaybookId, focusedPredictionTitle, focusedSuggestion]);

  const focusSummary = useMemo(() => {
    switch (section) {
      case 'manual':
        return {
          title: 'Foco manual',
          subtitle: 'Estruture um playbook manual e edite a base de conhecimento antes de salvar.',
          primary: 'Criação orientada',
          secondary: 'HowTo + checklist',
          bullets: ['Defina título, área e objetivo.', 'O sistema monta a estrutura sugerida.', 'Ajuste antes de salvar.'],
        };
      case 'erro':
        return {
          title: 'Foco em erros',
          subtitle: 'Gera guias dos problemas mais relevantes e recorrentes.',
          primary: `${dashboard?.ranking?.length ?? 0} riscos`,
          secondary: `${dashboard?.coverage?.erros ?? 0}% cobertura`,
          bullets: [
            dashboard?.ranking?.[0]?.erro || 'Sem risco principal.',
            dashboard?.ranking?.[0] ? `Score ${dashboard.ranking[0].score}.` : 'Sem score calculado.',
            'Use a geração automática para transformar recorrência em treinamento.',
          ],
        };
      case 'release':
        return {
          title: 'Foco em release',
          subtitle: 'Explora o que mudou em cada release e onde há aprendizado embutido.',
          primary: selectedRelease ? `Versão ${selectedRelease}` : 'Sem recorte',
          secondary: `${playbooks.filter((item) => item.origin === 'release').length} guias`,
          bullets: [
            selectedRelease ? 'Recorte ativo para a versão selecionada.' : 'Selecione uma versão para contextualizar.',
            cycle?.status === 'prestado' ? 'Prestação atual está fechada.' : 'Prestação aberta para novos anexos.',
            'A leitura de PDF alimenta essa geração sem IA externa.',
          ],
        };
      case 'predicoes':
        return {
          title: 'Foco preditivo',
          subtitle: 'Transforma sinais locais da aplicação em recomendações concretas.',
          primary: `${pdfContext?.predictions?.length ?? 0} previsões`,
          secondary: `${dashboard?.totals?.predictions ?? 0} guias preditivos`,
          bullets: [
            focusedPrediction?.title || pdfContext?.predictions?.[0]?.title || 'Sem previsão destacada.',
            focusedPrediction?.action || pdfContext?.predictions?.[0]?.action || 'Sem ação recomendada.',
            'Clique em uma previsão para focá-la e gerar guias automatizados.',
          ],
        };
      case 'lista':
        return {
          title: 'Foco na listagem',
          subtitle: 'A lista mostra origem, score e status com ações de visualização.',
          primary: `${playbooks.length} registros`,
          secondary: `${playbooks.filter((item) => item.status === 'ativo').length} ativos`,
          bullets: [
            focusedPlaybook ? `Playbook focado: ${focusedPlaybook.title}.` : 'Nenhum playbook selecionado.',
            focusedPlaybook ? `Origem: ${originLabel(focusedPlaybook.origin)}.` : 'Selecione um playbook para detalhar.',
            focusedPlaybook ? `Área: ${focusedPlaybook.area || '—'}.` : 'Sem área em foco.',
          ],
        };
      case 'sugestoes':
        return {
          title: 'Foco em sugestões',
          subtitle: 'Mostra pendências e recomendações para cobertura do conhecimento.',
          primary: `${suggestionsData?.suggestions?.length ?? 0} sugestões`,
          secondary: `${dashboard?.coverage?.areas_sem_documentacao?.length ?? 0} pendências`,
          bullets: [
            focusedSuggestion || suggestionsData?.suggestions?.[0] || 'Sem sugestão em foco.',
            dashboard?.coverage?.areas_sem_documentacao?.[0] ? `Área crítica: ${dashboard.coverage.areas_sem_documentacao[0]}.` : 'Sem área crítica listada.',
            'Use essas sugestões para criar ou atualizar playbooks.',
          ],
        };
      case 'dashboard':
      default:
        return {
          title: 'Foco do dashboard',
          subtitle: 'Resumo geral de cobertura, riscos e guias em uso.',
          primary: `${dashboard?.totals?.playbooks ?? playbooks.length} guias`,
          secondary: `${dashboard?.coverage?.processos ?? 0}% cobertura`,
          bullets: [
            selectedCycle ? `Ciclo histórico em foco: ${selectedCycle.period_label || `Prestação ${selectedCycle.cycle_number || selectedCycle.id}`}.` : `Ciclo aberto: ${openCycle?.period_label || 'Sem ciclo operacional aberto'}.`,
            dashboard?.ranking?.[0]?.erro || 'Sem risco prioritário.',
            dashboard?.suggestions?.[0] || suggestionsData?.suggestions?.[0] || 'Sem sugestão prioritária.',
            dashboard?.coverage?.areas_sem_documentacao?.length ? `${dashboard.coverage.areas_sem_documentacao.length} áreas sem documentação.` : 'Cobertura documentada.',
          ],
        };
    }
  }, [
    dashboard?.coverage?.areas_sem_documentacao,
    dashboard?.coverage?.erros,
    dashboard?.coverage?.processos,
    dashboard?.ranking,
    dashboard?.suggestions,
    dashboard?.totals?.playbooks,
    dashboard?.totals?.predictions,
    focusedPlaybook,
    focusedPrediction,
    focusedSuggestion,
    pdfContext?.predictions,
    playbooks,
    section,
    selectedRelease,
    selectedCycle,
    suggestionsData?.suggestions,
    cycle?.status,
    openCycle?.period_label,
  ]);

  const clearFocus = () => {
    setFocusedPlaybookId(null);
    setFocusedPredictionTitle(null);
    setFocusedSuggestion(null);
    setSelectedCycleId('');
  };

  const revealGeneratedPlaybooks = async (generatedPlaybooks: Playbook[], notice: string) => {
    clearFocus();
    setGenerationNotice(notice);
    setSection('lista');
    if (generatedPlaybooks.length > 0) {
      setFocusedPlaybookId(generatedPlaybooks[0].id);
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
      queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['playbooks', 'suggestions'] }),
    ]);
  };

  const createManualMutation = useMutation({
    mutationFn: playbooksApi.createManual,
    onSuccess: async (playbook) => {
      await revealGeneratedPlaybooks([playbook], `Guia manual criado: ${playbook.title}.`);
    },
  });

  const generateErrorMutation = useMutation({
    mutationFn: () => playbooksApi.generateErrors(8),
    onSuccess: async (result) => {
      await revealGeneratedPlaybooks(result.playbooks, `${result.playbooks.length} guia(s) gerado(s) a partir de erros.`);
    },
  });

  const generateReleaseMutation = useMutation({
    mutationFn: (releaseId: number) => playbooksApi.generateRelease(releaseId),
    onSuccess: async (result) => {
      await revealGeneratedPlaybooks(result.playbooks, `${result.playbooks.length} guia(s) gerado(s) a partir da versão selecionada.`);
    },
  });

  const generatePredictionMutation = useMutation({
    mutationFn: () => playbooksApi.generatePredictions(),
    onSuccess: async (result) => {
      await revealGeneratedPlaybooks(result.playbooks, `${result.playbooks.length} guia(s) preditivo(s) gerado(s).`);
    },
  });

  const closeCycleMutation = useMutation({
    mutationFn: (reopenNew: boolean) => reportsApi.closeCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      reopenNew,
      closedPeriodLabel: closedPeriodLabel.trim() || undefined,
      nextPeriodLabel: nextPeriodLabel.trim() || undefined,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['report-cycle', selectedRelease] });
    },
  });

  const openCycleMutation = useMutation({
    mutationFn: () => reportsApi.openCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
      periodLabel: nextPeriodLabel.trim() || undefined,
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['report-cycle', selectedRelease] });
    },
  });

  const releaseOptions = [
    { value: '', label: 'Selecione uma release' },
    ...releases.map((release) => ({ value: String(release.id), label: `${release.release_name || `Versão ${release.id}`} (${release.version})` })),
  ];

  const metrics = dashboard?.totals ?? {
    playbooks: playbooks.length,
    manual: playbooks.filter((item) => item.origin === 'manual').length,
    errors: playbooks.filter((item) => item.origin === 'erro').length,
    releases: playbooks.filter((item) => item.origin === 'release').length,
  };

  const currentStatus = cycle?.status || openCycle?.status || 'fechado';
  const openButtonDisabled = currentStatus === 'aberto';

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-[#0d3b66] via-[#184e77] to-[#1d5c85] p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.35em] text-white/70">Guias</p>
            <h1 className="mt-2 text-3xl font-bold">Motor inteligente de conhecimento operacional</h1>
            <p className="mt-3 text-white/85">
              Gere guias a partir de erros, versões e criação manual. Feche a prestação de contas como prestado e abra um novo ciclo quando necessário.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={currentStatus === 'prestado' ? 'success' : 'warning'}>{currentStatus}</Badge>
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => setSection('manual')}>
              Novo manual
            </Button>
            <Button type="button" variant="secondary" onClick={() => setSection('erro')}>
              Gerar por erros
            </Button>
            <Button type="button" variant="secondary" onClick={() => setSection('release')}>
              Gerar por versão
            </Button>
            <Button type="button" variant="secondary" onClick={() => setSection('predicoes')}>
              Gerar por previsões
            </Button>
          </div>
        </div>
      </div>

      <Card>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="w-full max-w-sm">
            <Select
              label="Recorte"
              options={releaseOptions}
              value={selectedRelease}
              onChange={(e) => setSelectedRelease(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(['dashboard', 'manual', 'erro', 'release', 'predicoes', 'lista', 'sugestoes'] as Section[]).map((item) => (
              <Button
                key={item}
                type="button"
                size="sm"
                variant={section === item ? 'primary' : 'outline'}
                onClick={() => setSection(item)}
              >
                {item === 'dashboard' && 'Painel'}
                {item === 'manual' && 'Manual'}
                {item === 'erro' && 'Erros'}
                {item === 'release' && 'Versão'}
                {item === 'predicoes' && 'Previsões'}
                {item === 'lista' && 'Listagem'}
                {item === 'sugestoes' && 'Sugestões'}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      <CycleTimelineCard
        title="Ciclo de conhecimento"
        description="Os guias seguem o mesmo ritmo operacional da prestação de contas: um mês ativo para evolução e um mês anterior consolidado para comparação."
        currentCycle={openCycle}
        previousCycle={previousClosedCycle}
        cycles={reportCycles}
        selectedCycleId={selectedCycleId}
        onSelectCycle={(cycleId) => {
          setSelectedCycleId(cycleId);
          const cycleItem = reportCycles.find((item) => String(item.id) === cycleId);
          if (cycleItem) {
            setFocusedSuggestion(cycleItem.period_label || `Prestação ${cycleItem.cycle_number || cycleItem.id}`);
            setSection('dashboard');
          }
        }}
        onOpenPrevious={() => {
          if (previousClosedCycle) {
            setSelectedCycleId(String(previousClosedCycle.id));
            setSection('dashboard');
            setFocusedSuggestion(previousClosedCycle.period_label || `Prestação ${previousClosedCycle.cycle_number || previousClosedCycle.id}`);
          }
        }}
        onOpenCurrent={() => {
          setSelectedCycleId('');
          setSection('dashboard');
          setFocusedSuggestion(openCycle?.period_label || `Prestação ${openCycle?.cycle_number || openCycle?.id || ''}`);
        }}
      />

      {generationNotice && (
        <Card className="border-l-4 border-l-emerald-500 bg-emerald-50/40">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-emerald-700">Geração concluída</p>
              <h2 className="mt-1 text-lg font-semibold text-emerald-950">{generationNotice}</h2>
              <p className="text-sm text-emerald-800">
                A lista foi aberta automaticamente para você ver os guias, exportar em PDF ou abrir a inteligência HTML.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="primary" onClick={() => setSection('lista')}>
                Ver lista
              </Button>
              <Button type="button" variant="outline" onClick={() => setGenerationNotice(null)}>
                Fechar aviso
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div ref={focusRef}>
        <Card className="border-l-4 border-l-[#0d3b66]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-[0.35em] text-gray-500">Foco do módulo</p>
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
            <Button type="button" size="sm" variant="outline" onClick={() => void exportPlaybookReportText()}>
              Texto do ciclo
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void openPlaybookReportHtml()}>
              HTML do ciclo
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void downloadPlaybookReportPdf()}>
              PDF do ciclo
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
            <Button type="button" size="sm" variant={section === 'dashboard' ? 'primary' : 'outline'} onClick={() => setSection('dashboard')}>
              Painel
            </Button>
            <Button type="button" size="sm" variant={section === 'manual' ? 'primary' : 'outline'} onClick={() => setSection('manual')}>
              Manual
            </Button>
            <Button type="button" size="sm" variant={section === 'erro' ? 'primary' : 'outline'} onClick={() => setSection('erro')}>
              Erros
            </Button>
            <Button type="button" size="sm" variant={section === 'release' ? 'primary' : 'outline'} onClick={() => setSection('release')}>
              Versão
            </Button>
            <Button type="button" size="sm" variant={section === 'predicoes' ? 'primary' : 'outline'} onClick={() => setSection('predicoes')}>
              Previsões
            </Button>
            <Button type="button" size="sm" variant={section === 'lista' ? 'primary' : 'outline'} onClick={() => setSection('lista')}>
              Lista
            </Button>
            <Button type="button" size="sm" variant={section === 'sugestoes' ? 'primary' : 'outline'} onClick={() => setSection('sugestoes')}>
              Sugestões
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={clearFocus}>
              Limpar foco
            </Button>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat label="Guias" value={metrics.playbooks} />
        <Stat label="Manuais" value={metrics.manual} />
        <Stat label="Por erro" value={metrics.errors} />
        <Stat label="Por release" value={metrics.releases} />
        <Stat label="Preditivos" value={dashboard?.totals?.predictions ?? 0} />
      </div>

      <PdfUploadCard scopeType="global" scopeLabel="Guias" />

      <Card>
        <h2 className="text-xl font-semibold text-gray-900">Prestação de contas</h2>
        <p className="text-sm text-gray-500">
          Prestação atual: #{cycle?.cycle_number || 1} · Status atual: {currentStatus}.
          {cycle?.period_label ? ` Período: ${cycle.period_label}.` : ''} O fechamento precisa informar o mês encerrado e o mês que será aberto.
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
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              if (!window.confirm('Fechar este mês e abrir a nova prestação informada?')) return;
              closeCycleMutation.mutate(true);
            }}
            disabled={closeCycleMutation.isPending}
          >
            Fechar e abrir nova prestação
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (!window.confirm('Abrir nova prestação para o mês informado?')) return;
              openCycleMutation.mutate();
            }}
            disabled={openCycleMutation.isPending || openButtonDisabled}
          >
            Abrir nova prestação
          </Button>
        </div>
      </Card>

      {section === 'dashboard' && (
        <DashboardSection
          loading={dashboardLoading}
          dashboard={dashboard ?? null}
          onOpenSection={(nextSection) => setSection(nextSection)}
          onFocusSuggestion={(suggestion) => {
            setFocusedSuggestion(suggestion);
            setSection('sugestoes');
          }}
        />
      )}

      {section === 'manual' && (
        <ManualPlaybookForm
          isLoading={createManualMutation.isPending}
          onSubmit={(data) => createManualMutation.mutate(data)}
        />
      )}

      {section === 'erro' && (
        <Card>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Gerar por erros do mês</h2>
              <p className="text-sm text-gray-500">Analisa atividades, frequência, impacto e reincidência para gerar guias automáticos.</p>
            </div>
            <Button type="button" onClick={() => generateErrorMutation.mutate()} disabled={generateErrorMutation.isPending}>
              {generateErrorMutation.isPending ? 'Gerando...' : 'Gerar guias críticos'}
            </Button>
          </div>
        </Card>
      )}

      {section === 'release' && (
        <Card>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Gerar por versão (PDF)</h2>
              <p className="text-sm text-gray-500">Usa os PDFs já lidos para extrair funcionalidades, melhorias e correções que exigem aprendizado.</p>
            </div>
            <Button
              type="button"
              onClick={() => selectedRelease && generateReleaseMutation.mutate(Number(selectedRelease))}
              disabled={!selectedRelease || generateReleaseMutation.isPending}
            >
              {generateReleaseMutation.isPending ? 'Gerando...' : 'Gerar para versão'}
            </Button>
          </div>
        </Card>
      )}

      {section === 'predicoes' && (
        <Card>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Gerar por previsões locais</h2>
              <p className="text-sm text-gray-500">
                Usa a inteligência da aplicação para criar guias automáticos a partir dos riscos e oportunidades previstos.
              </p>
            </div>
            <Button
              type="button"
              onClick={() => generatePredictionMutation.mutate()}
              disabled={generatePredictionMutation.isPending}
            >
              {generatePredictionMutation.isPending ? 'Gerando...' : 'Gerar guias preditivos'}
            </Button>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {(pdfContext?.predictions ?? []).slice(0, 4).map((item) => (
              <button
                key={item.title}
                type="button"
                className={`rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ${
                  focusedPredictionTitle === item.title
                    ? 'border-[#0d3b66] bg-white'
                    : 'border-gray-200 bg-gray-50'
                }`}
                onClick={() => {
                  setFocusedPredictionTitle(item.title);
                  setSection('predicoes');
                }}
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
                    setFocusedPredictionTitle(item.title);
                    generatePredictionMutation.mutate();
                  }}
                >
                  Gerar playbook
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={(event) => {
                    event.stopPropagation();
                    setFocusedPredictionTitle(item.title);
                  }}
                >
                  Focar
                </Button>
              </div>
              </button>
            ))}
            {(pdfContext?.predictions ?? []).length === 0 && (
              <p className="text-sm text-gray-500">Sem previsões disponíveis no momento.</p>
            )}
          </div>
        </Card>
      )}

      {section === 'lista' && (
        <div ref={listRef}>
          <PlaybookList
            playbooks={playbooks}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['playbooks'] })}
            focusedPlaybookId={focusedPlaybookId}
            onFocusPlaybook={(id) => {
              setFocusedPlaybookId(id);
              setGenerationNotice(null);
            }}
          />
        </div>
      )}

      {section === 'sugestoes' && (
        <SuggestionsSection suggestions={suggestionsData?.suggestions ?? []} coverage={suggestionsData?.coverage ?? dashboard?.coverage ?? null} />
      )}

    </div>
  );
}

function ManualPlaybookForm({
  onSubmit,
  isLoading,
}: {
  onSubmit: (data: { title: string; area: string; objective?: string; audience?: string; notes?: string }) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    title: '',
    area: 'Operacional',
    objective: '',
    audience: '',
    notes: '',
  });

  return (
    <Card>
      <h2 className="text-xl font-semibold text-gray-900">Playbook manual</h2>
      <p className="text-sm text-gray-500">Defina um tema e o sistema monta a estrutura HowTo, métricas, exemplos, boas práticas e checklist.</p>
      <form
        className="mt-5 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(formData);
        }}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Input label="Título" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} required />
          <Input label="Área" value={formData.area} onChange={(e) => setFormData({ ...formData, area: e.target.value })} />
        </div>
        <Input label="Objetivo" value={formData.objective} onChange={(e) => setFormData({ ...formData, objective: e.target.value })} />
        <Input label="Público-alvo" value={formData.audience} onChange={(e) => setFormData({ ...formData, audience: e.target.value })} />
        <Textarea label="Notas" value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} />
        <div className="flex justify-end">
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Salvando...' : 'Criar playbook'}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function PlaybookList({
  playbooks,
  onRefresh,
  focusedPlaybookId,
  onFocusPlaybook,
}: {
  playbooks: Playbook[];
  onRefresh: () => void;
  focusedPlaybookId: number | null;
  onFocusPlaybook: (id: number) => void;
}) {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: playbooksApi.delete,
    onSuccess: async () => {
      onRefresh();
      await queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] });
    },
  });
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Playbook['status'] }) => playbooksApi.updateStatus(id, status),
    onSuccess: async () => {
      onRefresh();
      await queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] });
    },
  });

  const openHtml = async (playbook: Playbook) => {
    const response = await playbooksApi.html(playbook.id);
    const popup = window.open('', '_blank', 'noopener,noreferrer');
    if (!popup) {
      return;
    }
    popup.document.open();
    popup.document.write(response.html);
    popup.document.close();
    onFocusPlaybook(playbook.id);
  };

  const downloadPdf = async (playbook: Playbook) => {
    const blob = await playbooksApi.pdf(playbook.id);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${playbook.title}.pdf`;
    anchor.click();
    window.URL.revokeObjectURL(url);
    onFocusPlaybook(playbook.id);
  };

  return (
    <Card>
      <h2 className="text-xl font-semibold text-gray-900">Listagem de guias</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Título</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Origem</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Área</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Score</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Data</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {playbooks.map((playbook) => (
              <tr key={playbook.id} className={focusedPlaybookId === playbook.id ? 'bg-amber-50/60' : ''}>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{playbook.title}</div>
                  <div className="text-xs text-gray-500">{playbook.summary}</div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{originLabel(playbook.origin)}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{playbook.area || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{playbook.priority_score ?? 0} ({playbook.priority_level})</td>
                <td className="px-4 py-3">
                  <Badge variant={playbook.status === 'prestado' ? 'success' : 'info'}>{playbook.status}</Badge>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{playbook.created_at.slice(0, 10)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => {
                      void openHtml(playbook);
                    }}>
                      Ver
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={() => {
                      void downloadPdf(playbook);
                    }}>
                      PDF
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => {
                      onFocusPlaybook(playbook.id);
                      onRefresh();
                    }}>
                      Focar
                    </Button>
                    <Button type="button" size="sm" variant="warning" onClick={() => statusMutation.mutate({ id: playbook.id, status: playbook.status === 'prestado' ? 'ativo' : 'prestado' })}>
                      {playbook.status === 'prestado' ? 'Reabrir' : 'Fechar'}
                    </Button>
                    <Button type="button" size="sm" variant="danger" onClick={() => deleteMutation.mutate(playbook.id)}>
                      Excluir
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {playbooks.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">Nenhum guia criado ainda.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function DashboardSection({
  loading,
  dashboard,
  onFocusSuggestion,
  onOpenSection,
}: {
  loading: boolean;
  dashboard: any | null;
  onFocusSuggestion: (suggestion: string) => void;
  onOpenSection: (section: Section) => void;
}) {
  if (loading) {
    return (
      <Card>
        <p className="text-sm text-gray-500">Carregando dashboard...</p>
      </Card>
    );
  }

  if (!dashboard) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        <InfoCard label="Cobertura de processos" value={`${dashboard.coverage?.processos ?? 0}%`} />
        <InfoCard label="Cobertura de erros" value={`${dashboard.coverage?.erros ?? 0}%`} />
        <InfoCard label="Adoção" value={dashboard.effectiveness?.adoption_rate ?? '0%'} />
        <InfoCard label="Avaliação" value={dashboard.effectiveness?.user_rating ?? '0/5'} />
      </div>

      <Card>
        <h2 className="text-xl font-semibold text-gray-900">Erros vs Guias</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Erro</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Frequência</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Impacto</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Playbook</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Redução</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
            {(dashboard.errors_vs_playbooks || []).map((row: any) => (
              <tr key={row.erro}>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{row.erro}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{row.frequencia}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{row.impacto}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{row.playbook_criado}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{row.status}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{row.reducao_percent}%</td>
              </tr>
            ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="text-xl font-semibold text-gray-900">Ranking de problemas</h2>
          <div className="mt-4 space-y-3">
            {(dashboard.ranking || []).slice(0, 5).map((row: any) => (
              <div key={row.erro} className="rounded-2xl bg-gray-50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-medium text-gray-900">{row.erro}</div>
                    <div className="text-xs text-gray-500">Score {row.score} • {row.priority_level}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={row.playbook_criado === 'Sim' ? 'success' : 'warning'}>{row.playbook_criado}</Badge>
                    <Button type="button" size="sm" variant="outline" onClick={() => onOpenSection('erro')}>
                      Abrir
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-gray-900">Sugestões automáticas</h2>
          <ul className="mt-4 space-y-2 text-sm text-gray-700">
            {(dashboard.suggestions || []).map((item: string) => (
              <li key={item} className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-3 py-2">
                <span className="flex-1">• {item}</span>
                <Button type="button" size="sm" variant="outline" onClick={() => onFocusSuggestion(item)}>
                  Focar
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function SuggestionsSection({
  suggestions,
  coverage,
}: {
  suggestions: string[];
  coverage: any | null;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card>
        <h2 className="text-xl font-semibold text-gray-900">Sugestões inteligentes</h2>
        <ul className="mt-4 space-y-2 text-sm text-gray-700">
          {suggestions.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      </Card>
      <Card>
        <h2 className="text-xl font-semibold text-gray-900">Cobertura</h2>
        <div className="mt-4 space-y-2 text-sm text-gray-700">
          <p>Processos cobertos: {coverage?.processos ?? 0}%</p>
          <p>Erros cobertos: {coverage?.erros ?? 0}%</p>
          <p>Áreas sem documentação: {(coverage?.areas_sem_documentacao ?? []).join(', ') || 'Nenhuma'}</p>
        </div>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    </Card>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
    </Card>
  );
}

function originLabel(origin: string) {
  return {
    manual: 'Manual',
    erro: 'Erro',
    release: 'Versão',
    predicao: 'Preditivo',
  }[origin] || origin;
}
