import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { releaseApi, moduloApi, clienteApi, atividadeApi, reportsApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, Badge, PdfRecordUploadButton, PdfRecordStatusBadge, PdfIntelligencePanel } from '../components';
import type { Release } from '../types';

export function Releases() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [intelligenceReleaseId, setIntelligenceReleaseId] = useState<number | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: modules = [] } = useQuery({
    queryKey: ['modulo'],
    queryFn: moduloApi.list,
  });

  const { data: clients = [] } = useQuery({
    queryKey: ['cliente'],
    queryFn: clienteApi.list,
  });
  const { data: reportCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles'],
    queryFn: () => reportsApi.cycles(),
  });
  const openCycle = reportCycles.find((cycle) => cycle.status === 'aberto') ?? null;
  const reportCycleId = openCycle?.id;

  const { data: activeReleaseActivities = [] } = useQuery({
    queryKey: ['atividade', 'release', intelligenceReleaseId],
    queryFn: () => atividadeApi.list(intelligenceReleaseId ?? undefined),
    enabled: intelligenceReleaseId !== null,
  });

  const activeRelease = items.find((item) => item.id === intelligenceReleaseId) ?? null;
  const reportFocus = activeRelease
    ? {
        type: 'release',
        value: String(activeRelease.id),
        label: `Versão: ${activeRelease.release_name || `Versão ${activeRelease.id}`} (${activeRelease.version})`,
      }
    : null;

  const createMutation = useMutation({
    mutationFn: releaseApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['release'] });
      setIsModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Release> }) =>
      releaseApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['release'] });
      setIsModalOpen(false);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: releaseApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['release'] }),
  });

  const exportText = async (focus = reportFocus) => {
    await reportsApi.summaryText(undefined, reportCycleId, focus ?? undefined);
  };

  const openHtml = async (focus = reportFocus) => {
    const result = await reportsApi.htmlReport(undefined, undefined, reportCycleId, focus ?? undefined);
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const exportPdf = async (focus = reportFocus) => {
    const blob = await reportsApi.pdfReport(undefined, undefined, reportCycleId, focus ?? undefined);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = reportCycleId ? `releases-ciclo-${reportCycleId}.pdf` : 'releases-relatorio.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const moduleOptions = [
    { value: '', label: 'Selecione...' },
    ...modules.map((m) => ({ value: String(m.id), label: m.name })),
  ];
  const clientOptions = [
    { value: '', label: 'Selecione...' },
    ...clients.map((c) => ({ value: String(c.id), label: c.name })),
  ];

  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'release_name', label: 'Nome' },
    { key: 'version', label: 'Versão' },
    { key: 'module', label: 'Módulo' },
    {
      key: 'pdf',
      label: 'PDF',
      render: (item: Release) => <PdfRecordStatusBadge scopeType="release" recordId={item.id} />,
    },
    { key: 'client', label: 'Cliente' },
    { key: 'applies_on', label: 'Aplica em' },
    {
      key: 'pdf_path',
      label: 'PDF',
      render: (item: Release) => item.pdf_path
        ? <a href={`/${item.pdf_path.replace(/^\/+/, '')}`} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">Ver PDF</a>
        : <span className="text-gray-400">Sem PDF</span>,
    },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Release) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setIsModalOpen(true); }}>
            Editar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceReleaseId(item.id)}>
            Ver inteligência
          </Button>
          <PdfRecordUploadButton
            scopeType="release"
            scopeLabel="Versões"
            recordId={item.id}
            recordLabel={`${item.release_name || `Versão ${item.id}`} (${item.version})`}
          />
          <Button size="sm" variant="danger" onClick={() => deleteMutation.mutate(item.id)}>
            Excluir
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Versões</h1>
          <p className="text-gray-500 mt-1">Gerencie versões e faça upload de notas em PDF</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => void exportText()}>
            Texto do ciclo
          </Button>
          <Button type="button" variant="secondary" onClick={() => void openHtml()}>
            HTML do ciclo
          </Button>
          <Button type="button" variant="secondary" onClick={() => void exportPdf()}>
            PDF do ciclo
          </Button>
          <Button onClick={() => { setEditingId(null); setIsModalOpen(true); }}>
            Nova Versão
          </Button>
        </div>
      </div>

      <Card className="border-l-4 border-l-[#0d3b66]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Ciclo operacional</p>
            <h2 className="mt-1 text-lg font-semibold text-gray-900">
              {openCycle ? `Ciclo aberto: ${openCycle.period_label || `Prestação ${openCycle.cycle_number || openCycle.id}`}` : 'Sem ciclo operacional aberto'}
            </h2>
          </div>
          <Badge variant={openCycle ? 'success' : 'warning'}>
            {openCycle ? 'Operação atual' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d3b66]"></div>
          </div>
        ) : (
          <DataTable columns={columns} data={items} keyExtractor={(item) => item.id} />
        )}
      </Card>

      <Card title="Inteligência da Versão" action={intelligenceReleaseId ? (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => void exportText(reportFocus)}>
            Texto do foco
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void openHtml(reportFocus)}>
            HTML do foco
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void exportPdf(reportFocus)}>
            PDF do foco
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceReleaseId(null)}>
            Limpar foco
          </Button>
        </div>
      ) : undefined}>
        {activeRelease ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <MiniStat label="Nome" value={activeRelease.release_name || `Versão ${activeRelease.id}`} />
              <MiniStat label="Versão" value={activeRelease.version} />
              <MiniStat label="Módulo" value={activeRelease.module || '—'} />
              <MiniStat label="Aplica em" value={activeRelease.applies_on || '—'} />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <MiniStat label="Atividades" value={activeReleaseActivities.length} />
              <MiniStat
                label="Concluídas"
                value={activeReleaseActivities.filter((activity) => activity.status === 'concluida').length}
              />
              <MiniStat
                label="Bloqueadas"
                value={activeReleaseActivities.filter((activity) => activity.status === 'bloqueada').length}
              />
            </div>
            <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-sm font-semibold text-gray-900">Resumo operacional</p>
              <p className="mt-2 text-sm text-gray-600">
                {activeRelease.notes || 'Sem notas de versão cadastradas.'}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Selecione uma versão na tabela para ver o resumo inteligente.</p>
        )}
      </Card>

      <PdfIntelligencePanel
        scopeType="release"
        scopeLabel="Versões"
        scopeId={intelligenceReleaseId}
        recordOptions={items.map((release) => ({
          id: release.id,
          label: `${release.release_name || `Versão ${release.id}`} (${release.version})`,
        }))}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); }}
        title={editingId ? 'Editar Versão' : 'Nova Versão'}
        footer={editingId ? (
          <div className="flex justify-end">
            <PdfRecordUploadButton
              scopeType="release"
              scopeLabel="Versões"
              recordId={editingId}
              recordLabel={items.find((item) => item.id === editingId)?.release_name || `Versão ${editingId}`}
            />
          </div>
        ) : undefined}
      >
        <ReleaseForm
          moduleOptions={moduleOptions}
          clientOptions={clientOptions}
          openCycleLabel={openCycle ? openCycle.period_label || `Prestação ${openCycle.cycle_number || openCycle.id}` : null}
          onCancel={() => { setIsModalOpen(false); setEditingId(null); }}
          onSubmit={(data) => {
            if (editingId) {
              updateMutation.mutate({ id: editingId, data });
            } else {
              createMutation.mutate(data);
            }
          }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      </Modal>
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

function ReleaseForm({
  moduleOptions,
  clientOptions,
  openCycleLabel,
  onCancel,
  onSubmit,
  isLoading,
}: {
  moduleOptions: any[];
  clientOptions: any[];
  openCycleLabel: string | null;
  onCancel: () => void;
  onSubmit: (data: Partial<Release>) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    release_name: '',
    version: '',
    module_id: '',
    client_id: '',
    applies_on: '',
    notes: '',
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          ...formData,
          module_id: formData.module_id ? Number(formData.module_id) : null,
          client_id: formData.client_id ? Number(formData.client_id) : null,
        });
      }}
      className="space-y-4"
    >
      <Card className="border-l-4 border-l-[#0d3b66] bg-[#f8fbff]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Contexto operacional</p>
            <h3 className="mt-1 text-base font-semibold text-gray-900">
              {openCycleLabel ? `Mês em trabalho: ${openCycleLabel}` : 'Sem mês operacional aberto'}
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              A release será registrada apenas no ciclo aberto. O histórico anterior permanece consolidado nos relatórios.
            </p>
          </div>
          <Badge variant={openCycleLabel ? 'success' : 'warning'}>
            {openCycleLabel ? 'Mês ativo' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Nome da Versão"
          value={formData.release_name}
          onChange={(e) => setFormData({ ...formData, release_name: e.target.value })}
          required
        />
        <Input
          label="Versão"
          placeholder="Ex: 1.0.0"
          value={formData.version}
          onChange={(e) => setFormData({ ...formData, version: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Módulo"
          options={moduleOptions}
          value={formData.module_id}
          onChange={(e) => setFormData({ ...formData, module_id: e.target.value })}
        />
        <Select
          label="Cliente"
          options={clientOptions}
          value={formData.client_id}
          onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
        />
      </div>
      <Input
        label="Aplica em"
        type="date"
        value={formData.applies_on}
        onChange={(e) => setFormData({ ...formData, applies_on: e.target.value })}
      />
      <Input
        label="Notas"
        value={formData.notes}
        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
      />
      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>Cancelar</Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Salvando...' : 'Salvar'}
        </Button>
      </div>
    </form>
  );
}
