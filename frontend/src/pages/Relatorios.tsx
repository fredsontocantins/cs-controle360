import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi, reportsApi, releaseApi } from '../services/api';
import { Button, Select, Card, TipoBadge, Badge, PdfUploadCard, PdfIntelligencePanel, Input } from '../components';

type Section = 'executivo' | 'performance' | 'modulos' | 'releases' | 'temas' | 'tickets' | 'auditoria';

export function Relatorios() {
  const queryClient = useQueryClient();
  const [selectedRelease, setSelectedRelease] = useState<string>('');
  const [activeSection, setActiveSection] = useState<Section>('executivo');
  const [textPreview, setTextPreview] = useState<string>('');
  const [isTextLoading, setIsTextLoading] = useState(false);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [auditState, setAuditState] = useState<string>('todos');
  const [auditSearch, setAuditSearch] = useState<string>('');

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: report, isLoading } = useQuery({
    queryKey: ['reports', 'ticket-summary', selectedRelease],
    queryFn: () => reportsApi.ticketSummary(selectedRelease ? Number(selectedRelease) : undefined),
    enabled: true,
  });

  const { data: reportCycle } = useQuery({
    queryKey: ['report-cycle', selectedRelease],
    queryFn: () => reportsApi.cycle(selectedRelease ? Number(selectedRelease) : undefined),
  });

  const { data: cycleAudit } = useQuery({
    queryKey: ['pdf-intelligence', 'cycle-audit'],
    queryFn: pdfIntelligenceApi.cycleAudit,
  });

  const releaseOptions = [
    { value: '', label: 'Todos os releases' },
    ...releases.map((r) => ({ value: String(r.id), label: `${r.release_name || `Release ${r.id}`} (${r.version})` })),
  ];
  const releaseRecordOptions = useMemo(
    () => releases.map((r) => ({ id: r.id, label: `${r.release_name || `Release ${r.id}`} (${r.version})` })),
    [releases]
  );

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

  const handleGenerateText = async () => {
    setIsTextLoading(true);
    try {
      const result = await reportsApi.summaryText(selectedRelease ? Number(selectedRelease) : undefined);
      setTextPreview(result.report);
      setActiveSection('executivo');
    } finally {
      setIsTextLoading(false);
    }
  };

  const handleOpenHtml = async () => {
    const result = await reportsApi.htmlReport(
      selectedRelease ? Number(selectedRelease) : undefined,
      selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined
    );

    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const handleExportPdf = async () => {
    setIsPdfLoading(true);
    try {
      const blob = await reportsApi.pdfReport(
        selectedRelease ? Number(selectedRelease) : undefined,
        selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined
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

  const closeCycleMutation = useMutation({
    mutationFn: (reopenNew: boolean) => reportsApi.closeCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      reopenNew,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
      periodLabel: selectedRelease ? `Release ${selectedRelease}` : 'Prestação geral',
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['report-cycle', selectedRelease] });
    },
  });

  const openCycleMutation = useMutation({
    mutationFn: () => reportsApi.openCycle({
      releaseId: selectedRelease ? Number(selectedRelease) : undefined,
      scopeLabel: selectedRelease ? releases.find((release) => release.id === Number(selectedRelease))?.release_name : undefined,
      periodLabel: selectedRelease ? `Release ${selectedRelease}` : 'Prestação geral',
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['report-cycle', selectedRelease] });
    },
  });

  const focusModules = report?.module_summary ?? [];
  const focusReleases = report?.release_summary ?? [];
  const focusThemes = report?.themes ?? [];
  const focusTickets = report?.tickets ?? [];
  const insights = report?.insights ?? [];
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
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" className="border-white text-white hover:bg-white hover:text-[#0d3b66]" onClick={handleGenerateText} disabled={isTextLoading}>
              {isTextLoading ? 'Gerando texto...' : 'Gerar texto'}
            </Button>
            <Button type="button" variant="secondary" onClick={handleOpenHtml}>
              Abrir HTML
            </Button>
            <Button type="button" variant="secondary" onClick={handleExportPdf} disabled={isPdfLoading}>
              {isPdfLoading ? 'Exportando PDF...' : 'Exportar PDF'}
            </Button>
          </div>
        </div>
      </div>

      <Card>
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="w-full max-w-sm">
            <Select
              label="Release"
              options={releaseOptions}
              value={selectedRelease}
              onChange={(e) => setSelectedRelease(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {(['executivo', 'performance', 'modulos', 'releases', 'temas', 'tickets', 'auditoria'] as Section[]).map((section) => (
              <Button
                key={section}
                type="button"
                size="sm"
                variant={activeSection === section ? 'primary' : 'outline'}
                onClick={() => setActiveSection(section)}
              >
                {section === 'executivo' && 'Executivo'}
                {section === 'performance' && 'Performance'}
                {section === 'modulos' && 'Módulos'}
                {section === 'releases' && 'Releases'}
                {section === 'temas' && 'Temas'}
                {section === 'tickets' && 'Tickets'}
                {section === 'auditoria' && 'Auditoria'}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      <PdfUploadCard
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
              Status atual: <span className="font-semibold text-gray-900">{reportCycle?.cycle?.status || 'aberto'}</span>.
              {reportCycle?.cycle?.closed_at ? ` Fechado em ${reportCycle.cycle.closed_at.slice(0, 19).replace('T', ' ')}` : ' Ainda aberto para revisão.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={closeCycleMutation.isPending}
              onClick={() => {
                if (!window.confirm('Fechar relatório como prestado?')) return;
                const reopen = window.confirm('Abrir uma nova prestação agora?');
                closeCycleMutation.mutate(reopen);
              }}
            >
              Fechar como prestado
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

      <PdfIntelligencePanel
        scopeType="relatorios"
        scopeLabel="Relatórios Gerenciais"
        scopeId={selectedRelease ? Number(selectedRelease) : null}
        recordOptions={releaseRecordOptions}
      />

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
                <MetricCard title="Releases" value={totals.releases} tone="bg-[#0d3b66]" />
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
                    <Badge variant="warning">{report.top_module.share}% do total</Badge>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <MiniStat label="Tickets" value={report.top_module.tickets} />
                    <MiniStat label="Releases" value={report.top_module.releases} />
                    <MiniStat label="Última versão" value={report.top_module.latest_version} />
                    <MiniStat label="Último release" value={report.top_module.latest_release} />
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
            </>
          )}

          {activeSection === 'performance' && (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <Card className="xl:col-span-1">
                <h2 className="text-xl font-semibold text-gray-900">Distribuição por status</h2>
                <p className="text-sm text-gray-500">Leitura de fila e maturidade operacional.</p>
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
                <h2 className="text-xl font-semibold text-gray-900">Concentração por módulo</h2>
                <p className="text-sm text-gray-500">Onde a operação está mais pressionada.</p>
                <div className="mt-4 space-y-3">
                  {modulePerformance.length > 0 ? (
                    modulePerformance.map((module) => (
                      <BarRow key={module.module} label={module.module} value={module.tickets} total={totals.tickets || 1} suffix={`${module.share}%`} />
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados para o recorte atual.</p>
                  )}
                </div>
              </Card>

              <Card className="xl:col-span-1">
                <h2 className="text-xl font-semibold text-gray-900">Tendência por release</h2>
                <p className="text-sm text-gray-500">Volume entregue por período de aplicação.</p>
                <div className="mt-4 space-y-3">
                  {releasePerformance.length > 0 ? (
                    releasePerformance.map((release) => (
                      <BarRow
                        key={release.id}
                        label={release.release_name}
                        value={release.tickets}
                        total={Math.max(...releasePerformance.map((item) => item.tickets), 1)}
                        suffix={release.applies_on ? release.applies_on.slice(0, 10) : '---'}
                      />
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Sem dados para o recorte atual.</p>
                  )}
                </div>
              </Card>
            </div>
          )}

          {activeSection === 'modulos' && (
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
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Releases</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Correções</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Melhorias</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Tickets</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Última versão</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Share</th>
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
                        <td className="px-4 py-3 text-sm text-gray-700">{module.share}%</td>
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
          )}

          {activeSection === 'releases' && (
            <div className="space-y-4">
              <Card>
                <h2 className="text-xl font-semibold text-gray-900">Visão por Release</h2>
                <p className="text-sm text-gray-500">Release, status e volume de tickets por entrega.</p>
              </Card>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {focusReleases.map((release) => (
                  <Card key={release.id} className={release.tickets > 0 ? 'border-l-4 border-l-[#0d3b66]' : ''}>
                    <div className="flex flex-col gap-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-wider text-gray-500">{release.module}</p>
                          <h3 className="text-lg font-semibold text-gray-900">{release.release_name}</h3>
                          <p className="text-sm text-gray-500">Versão {release.version}</p>
                        </div>
                        <Badge variant={release.tickets > 0 ? 'warning' : 'default'}>{release.tickets} tickets</Badge>
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
                  <div key={theme.theme} className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{theme.count}</Badge>
                      <span className="font-medium text-gray-900">{theme.theme}</span>
                    </div>
                    {theme.examples.length > 0 && (
                      <p className="mt-2 text-xs text-gray-500">Exemplos: {theme.examples.join(', ')}</p>
                    )}
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
                  <Card key={`${ticket.ticket}-${ticket.release_id ?? 'na'}`}>
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
                        {ticket.release && <span>Release: {ticket.release}</span>}
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
    backlog: 'Backlog',
    em_andamento: 'Em Andamento',
    em_revisao: 'Em Revisão',
    concluida: 'Concluída',
    bloqueada: 'Bloqueada',
  }[status] || status;
}
