import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi, releaseApi, playbooksApi, reportsApi } from '../services/api';
import { Badge, Button, Card, Input, Select, Textarea } from '../components';
import type { Playbook } from '../types';

type Section = 'manual' | 'erro' | 'release' | 'lista' | 'dashboard' | 'sugestoes' | 'predicoes';

export function Playbooks() {
  const queryClient = useQueryClient();
  const [section, setSection] = useState<Section>('dashboard');
  const [selectedRelease, setSelectedRelease] = useState<string>('');

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: playbooks = [] } = useQuery({
    queryKey: ['playbooks'],
    queryFn: playbooksApi.list,
  });

  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['playbooks', 'dashboard'],
    queryFn: playbooksApi.dashboard,
  });

  const { data: suggestionsData } = useQuery({
    queryKey: ['playbooks', 'suggestions'],
    queryFn: playbooksApi.suggestions,
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

  const createManualMutation = useMutation({
    mutationFn: playbooksApi.createManual,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'suggestions'] }),
      ]);
    },
  });

  const generateErrorMutation = useMutation({
    mutationFn: () => playbooksApi.generateErrors(8),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'suggestions'] }),
      ]);
    },
  });

  const generateReleaseMutation = useMutation({
    mutationFn: (releaseId: number) => playbooksApi.generateRelease(releaseId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'suggestions'] }),
      ]);
    },
  });

  const generatePredictionMutation = useMutation({
    mutationFn: () => playbooksApi.generatePredictions(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'suggestions'] }),
      ]);
    },
  });

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

  const releaseOptions = [
    { value: '', label: 'Selecione uma release' },
    ...releases.map((release) => ({ value: String(release.id), label: `${release.release_name || `Release ${release.id}`} (${release.version})` })),
  ];

  const metrics = dashboard?.totals ?? {
    playbooks: playbooks.length,
    manual: playbooks.filter((item) => item.origin === 'manual').length,
    errors: playbooks.filter((item) => item.origin === 'erro').length,
    releases: playbooks.filter((item) => item.origin === 'release').length,
  };

  const currentStatus = cycle?.status || 'aberto';

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-[#0d3b66] via-[#184e77] to-[#1d5c85] p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.35em] text-white/70">Playbooks</p>
            <h1 className="mt-2 text-3xl font-bold">Motor inteligente de conhecimento operacional</h1>
            <p className="mt-3 text-white/85">
              Gere playbooks a partir de erros, releases e criação manual. Feche a prestação de contas como prestado e abra um novo ciclo quando necessário.
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
              Gerar por release
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
                {item === 'dashboard' && 'Dashboard'}
                {item === 'manual' && 'Manual'}
                {item === 'erro' && 'Erros'}
                {item === 'release' && 'Release'}
                {item === 'predicoes' && 'Previsões'}
                {item === 'lista' && 'Listagem'}
                {item === 'sugestoes' && 'Sugestões'}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat label="Playbooks" value={metrics.playbooks} />
        <Stat label="Manuais" value={metrics.manual} />
        <Stat label="Por erro" value={metrics.errors} />
        <Stat label="Por release" value={metrics.releases} />
        <Stat label="Preditivos" value={dashboard?.totals?.predictions ?? 0} />
      </div>

      <Card>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Prestação de contas</h2>
            <p className="text-sm text-gray-500">
              Status atual: {currentStatus}. Você pode fechar como prestado e abrir uma nova prestação no mesmo recorte.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const close = window.confirm('Fechar este relatório como prestado?');
                if (!close) return;
                const reopen = window.confirm('Abrir uma nova prestação agora?');
                closeCycleMutation.mutate(reopen);
              }}
              disabled={closeCycleMutation.isPending}
            >
              Fechar como prestado
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => openCycleMutation.mutate()}
              disabled={openCycleMutation.isPending}
            >
              Nova prestação
            </Button>
          </div>
        </div>
      </Card>

      {section === 'dashboard' && (
        <DashboardSection loading={dashboardLoading} dashboard={dashboard ?? null} />
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
              <p className="text-sm text-gray-500">Analisa atividades, frequência, impacto e reincidência para gerar playbooks automáticos.</p>
            </div>
            <Button type="button" onClick={() => generateErrorMutation.mutate()} disabled={generateErrorMutation.isPending}>
              {generateErrorMutation.isPending ? 'Gerando...' : 'Gerar playbooks críticos'}
            </Button>
          </div>
        </Card>
      )}

      {section === 'release' && (
        <Card>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Gerar por release (PDF)</h2>
              <p className="text-sm text-gray-500">Usa os PDFs já lidos para extrair funcionalidades, melhorias e correções que exigem aprendizado.</p>
            </div>
            <Button
              type="button"
              onClick={() => selectedRelease && generateReleaseMutation.mutate(Number(selectedRelease))}
              disabled={!selectedRelease || generateReleaseMutation.isPending}
            >
              {generateReleaseMutation.isPending ? 'Gerando...' : 'Gerar para release'}
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
                Usa a inteligência da aplicação para criar playbooks automáticos a partir dos riscos e oportunidades previstos.
              </p>
            </div>
            <Button
              type="button"
              onClick={() => generatePredictionMutation.mutate()}
              disabled={generatePredictionMutation.isPending}
            >
              {generatePredictionMutation.isPending ? 'Gerando...' : 'Gerar playbooks preditivos'}
            </Button>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {(pdfContext?.predictions ?? []).slice(0, 4).map((item) => (
              <div key={item.title} className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
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
              </div>
            ))}
            {(pdfContext?.predictions ?? []).length === 0 && (
              <p className="text-sm text-gray-500">Sem previsões disponíveis no momento.</p>
            )}
          </div>
        </Card>
      )}

      {section === 'lista' && (
        <PlaybookList
          playbooks={playbooks}
          onRefresh={() => queryClient.invalidateQueries({ queryKey: ['playbooks'] })}
        />
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
}: {
  playbooks: Playbook[];
  onRefresh: () => void;
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

  return (
    <Card>
      <h2 className="text-xl font-semibold text-gray-900">Listagem de playbooks</h2>
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
              <tr key={playbook.id}>
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
                    <Button type="button" size="sm" variant="outline" onClick={() => window.open(`/api/playbooks/${playbook.id}/html`, '_blank', 'noopener,noreferrer')}>
                      Ver
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={() => {
                      const anchor = document.createElement('a');
                      anchor.href = `/api/playbooks/${playbook.id}/pdf`;
                      anchor.download = `${playbook.title}.pdf`;
                      anchor.click();
                    }}>
                      PDF
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
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">Nenhum playbook criado ainda.</td>
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
}: {
  loading: boolean;
  dashboard: any | null;
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
        <h2 className="text-xl font-semibold text-gray-900">Erros vs Playbooks</h2>
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
                  <Badge variant={row.playbook_criado === 'Sim' ? 'success' : 'warning'}>{row.playbook_criado}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-gray-900">Sugestões automáticas</h2>
          <ul className="mt-4 space-y-2 text-sm text-gray-700">
            {(dashboard.suggestions || []).map((item: string) => (
              <li key={item}>• {item}</li>
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
    release: 'Release',
    predicao: 'Preditivo',
  }[origin] || origin;
}
