import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getAuthUser, summaryApi, playbooksApi, pdfIntelligenceApi } from '../services/api';
import { StatCard, PdfIntelligencePanel, Card, Badge, Button } from '../components';

export function Dashboard() {
  const queryClient = useQueryClient();
  const user = getAuthUser();
  const { data: summary, isLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: summaryApi.get,
  });

  const { data: playbookDashboard } = useQuery({
    queryKey: ['playbooks', 'dashboard'],
    queryFn: playbooksApi.dashboard,
  });

  const { data: pdfContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });

  const generatePredictionsMutation = useMutation({
    mutationFn: playbooksApi.generatePredictions,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        queryClient.invalidateQueries({ queryKey: ['playbooks', 'dashboard'] }),
      ]);
    },
  });

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
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Visão geral do sistema CS Controle 360</p>
        </div>
      </div>

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
          <StatCard title="Releases" value={summary?.releases ?? 0} />
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
          <StatCard title="Playbooks" value={playbookDashboard?.totals?.playbooks ?? 0} />
        </Link>
        <Link to="/relatorios">
          <StatCard title="PDFs do ciclo" value={pdfContext?.cycle_documents ?? pdfContext?.total_documents ?? 0} />
        </Link>
      </div>

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
                <p className="font-medium text-gray-900">Releases</p>
                <p className="text-sm text-gray-500">Gerenciar releases e notas</p>
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
                <p className="font-medium text-gray-900">Playbooks</p>
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

        <Card title="Playbooks Inteligentes" className="xl:col-span-1">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <MiniStat label="Cobertura de processos" value={`${playbookDashboard?.coverage?.processos ?? 0}%`} />
              <MiniStat label="Cobertura de erros" value={`${playbookDashboard?.coverage?.erros ?? 0}%`} />
              <MiniStat label="Pendências" value={playbookDashboard?.coverage?.areas_sem_documentacao?.length ?? 0} />
              <MiniStat label="Playbooks ativos" value={playbookDashboard?.totals?.playbooks ?? 0} />
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-900">Riscos críticos</p>
              <div className="mt-3 space-y-2">
                {(playbookDashboard?.ranking ?? []).slice(0, 4).map((item) => (
                  <div key={item.erro} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
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
                  </div>
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
                Abrir painel de Playbooks
              </Link>
            </div>
          </div>
        </Card>

        <Card title="Inteligência de PDFs" className="xl:col-span-1">
          <div className="space-y-4">
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
      </div>

        <Card title="Alertas Inteligentes">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-gray-500">Previsões locais transformadas em alertas e playbooks.</p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => generatePredictionsMutation.mutate()}
            disabled={generatePredictionsMutation.isPending}
          >
            {generatePredictionsMutation.isPending ? 'Gerando...' : 'Gerar playbooks preditivos'}
          </Button>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(pdfContext?.predictions ?? []).slice(0, 3).map((item) => (
            <div
              key={item.title}
              className={`rounded-2xl border p-4 ${
                item.confidence >= 80
                  ? 'border-red-200 bg-red-50'
                  : item.confidence >= 60
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-sky-200 bg-sky-50'
              }`}
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
            </div>
          ))}
          {(pdfContext?.predictions ?? []).length === 0 && (
            <p className="text-sm text-gray-500">Nenhum alerta disponível no momento.</p>
          )}
        </div>
      </Card>

      <PdfIntelligencePanel scopeType="dashboard" scopeLabel="Dashboard" />
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
