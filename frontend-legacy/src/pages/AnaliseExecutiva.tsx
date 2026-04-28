import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { pdfIntelligenceApi, playbooksApi, reportsApi, summaryApi } from '../services/api';
import { Badge, Button, Card, CycleTimelineCard, StatCard } from '../components';

export function AnaliseExecutiva() {
  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn: () => summaryApi.get(),
  });

  const { data: reportCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles'],
    queryFn: () => reportsApi.cycles(),
  });

  const { data: playbookDashboard } = useQuery({
    queryKey: ['playbooks', 'dashboard'],
    queryFn: () => playbooksApi.dashboard(),
  });

  const { data: pdfContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });

  const openCycle = reportCycles.find((cycle) => cycle.status === 'aberto') ?? null;
  const previousCycle = useMemo(() => {
    const closed = reportCycles.filter((cycle) => cycle.status === 'prestado');
    return closed[0] ?? null;
  }, [reportCycles]);

  const exportCycleText = async () => {
    await reportsApi.summaryText();
  };

  const openCycleHtml = async () => {
    const result = await reportsApi.htmlReport();
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const exportCyclePdf = async () => {
    const blob = await reportsApi.pdfReport();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'analise-executiva.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const currentStats = [
    { title: 'Homologações', value: summary?.homologacoes ?? 0 },
    { title: 'Customizações', value: summary?.customizacoes ?? 0 },
    { title: 'Atividades', value: summary?.atividades ?? 0 },
    { title: 'Versões', value: summary?.releases ?? 0 },
    { title: 'Guias', value: playbookDashboard?.totals?.playbooks ?? 0 },
    { title: 'PDFs', value: pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0 },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-[#0d3b66] via-[#184e77] to-[#1d5c85] p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.35em] text-white/70">Análise Executiva</p>
            <h1 className="mt-2 text-3xl font-bold">Centro operacional e gerencial</h1>
            <p className="mt-3 text-white/85">
              Consolida o ciclo vigente, os ciclos fechados, os guias e a inteligência de PDF em um único ponto de decisão.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={() => void exportCycleText()}>
              Texto
            </Button>
            <Button type="button" variant="secondary" onClick={() => void openCycleHtml()}>
              HTML
            </Button>
            <Button type="button" variant="secondary" onClick={() => void exportCyclePdf()}>
              PDF
            </Button>
          </div>
        </div>
      </div>

      <CycleTimelineCard
        title="Linha do tempo executiva"
        description="Um único painel para abrir o mês vigente, revisar o mês anterior e navegar pelos ciclos fechados com leitura corporativa."
        currentCycle={openCycle}
        previousCycle={previousCycle}
        cycles={reportCycles}
        selectedCycleId={openCycle ? String(openCycle.id) : ''}
        onSelectCycle={() => void 0}
        onOpenPrevious={() => void 0}
        onOpenCurrent={() => void 0}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {currentStats.map((stat) => (
          <StatCard key={stat.title} title={stat.title} value={stat.value} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Ações executivas">
          <div className="space-y-3">
            <Link to="/relatorios" className="block">
              <Button type="button" className="w-full">Abrir Relatórios</Button>
            </Link>
            <Link to="/playbooks" className="block">
              <Button type="button" className="w-full" variant="secondary">Abrir Guias</Button>
            </Link>
            <Link to="/" className="block">
              <Button type="button" className="w-full" variant="outline">Abrir Painel</Button>
            </Link>
          </div>
        </Card>

        <Card title="Ciclo vigente">
          <div className="space-y-3">
            <Badge variant={openCycle ? 'success' : 'warning'}>{openCycle ? 'Aberto' : 'Sem ciclo aberto'}</Badge>
            <p className="text-sm text-gray-600">
              {openCycle?.period_label || 'Sem mês operacional aberto.'}
            </p>
            <p className="text-sm text-gray-600">
              {summary?.current_cycle?.label
                ? `Mês em trabalho: ${summary.current_cycle.label}`
                : 'Os dados atuais continuam sendo consolidados ao abrir o ciclo.'}
            </p>
          </div>
        </Card>

        <Card title="Foco executivo">
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Use esta área para validar rapidamente o que está aberto, o que foi fechado e o que precisa de ação imediata.
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="info">Gerencial</Badge>
              <Badge variant="warning">Confidencial</Badge>
              <Badge variant="success">Ciclo ativo</Badge>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
