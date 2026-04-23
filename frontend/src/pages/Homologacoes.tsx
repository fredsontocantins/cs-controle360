import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { homologacaoApi, moduloApi, clienteApi, reportsApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, Badge, PdfRecordUploadButton, PdfRecordStatusBadge, PdfIntelligencePanel } from '../components';
import type { Homologacao } from '../types';

export function Homologacoes() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [intelligenceId, setIntelligenceId] = useState<number | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['homologacao'],
    queryFn: homologacaoApi.list,
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
  const focusedHomologacao = items.find((item) => item.id === intelligenceId) ?? null;
  const reportFocus = focusedHomologacao
    ? {
        type: 'module',
        value: focusedHomologacao.module || String(focusedHomologacao.module_id || ''),
        label: `Homologação: ${focusedHomologacao.module || `ID ${focusedHomologacao.id}`} ${focusedHomologacao.client ? `• ${focusedHomologacao.client}` : ''}`,
      }
    : null;

  const createMutation = useMutation({
    mutationFn: homologacaoApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['homologacao'] });
      setIsModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Homologacao> }) =>
      homologacaoApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['homologacao'] });
      setIsModalOpen(false);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: homologacaoApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['homologacao'] }),
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
    anchor.download = reportCycleId ? `homologacoes-ciclo-${reportCycleId}.pdf` : 'homologacoes-relatorio.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const statusOptions = [
    { value: 'Pendente', label: 'Pendente' },
    { value: 'Em Homologação', label: 'Em Homologação' },
    { value: 'Homologado', label: 'Homologado' },
    { value: 'Em Produção', label: 'Em Produção' },
    { value: 'Concluído', label: 'Concluído' },
  ];

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
    { key: 'module', label: 'Módulo' },
    { key: 'client', label: 'Cliente' },
    {
      key: 'pdf',
      label: 'PDF',
      render: (item: Homologacao) => <PdfRecordStatusBadge scopeType="homologacao" recordId={item.id} />,
    },
    {
      key: 'status',
      label: 'Status',
      render: (item: Homologacao) => <Badge variant={item.status === 'Homologado' ? 'success' : 'warning'}>{item.status || '---'}</Badge>,
    },
    { key: 'homologation_version', label: 'Versão Homologação' },
    { key: 'production_version', label: 'Versão Produção' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Homologacao) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setIsModalOpen(true); }}>
            Editar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceId(item.id)}>
            Ver inteligência
          </Button>
          <PdfRecordUploadButton
            scopeType="homologacao"
            scopeLabel="Homologações"
            recordId={item.id}
            recordLabel={`${item.module || 'Sem módulo'}${item.client ? ` • ${item.client}` : ''}`}
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
          <h1 className="text-2xl font-bold text-gray-900">Homologações</h1>
          <p className="text-gray-500 mt-1">Gerencie o controle de versões e homologações</p>
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
            Nova Homologação
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

      <Card title="Inteligência da Homologação" action={intelligenceId ? (
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
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceId(null)}>
            Limpar foco
          </Button>
        </div>
      ) : undefined}>
        {intelligenceId ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <MiniStat label="Módulo" value={items.find((item) => item.id === intelligenceId)?.module || '—'} />
              <MiniStat label="Cliente" value={items.find((item) => item.id === intelligenceId)?.client || '—'} />
              <MiniStat label="Status" value={items.find((item) => item.id === intelligenceId)?.status || '—'} />
              <MiniStat label="Versão" value={items.find((item) => item.id === intelligenceId)?.latest_version || '—'} />
            </div>
            <p className="text-sm text-gray-600">
              {items.find((item) => item.id === intelligenceId)?.observation || 'Sem observação cadastrada.'}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Selecione uma homologação na tabela para ver o foco inteligente.</p>
        )}
      </Card>

      <PdfIntelligencePanel
        scopeType="homologacao"
        scopeLabel="Homologações"
        scopeId={intelligenceId}
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.module || 'Sem módulo'}${item.client ? ` • ${item.client}` : ''}`,
        }))}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); }}
        title={editingId ? 'Editar Homologação' : 'Nova Homologação'}
        footer={editingId ? (
          <div className="flex justify-end">
            <PdfRecordUploadButton
              scopeType="homologacao"
              scopeLabel="Homologações"
              recordId={editingId}
              recordLabel={items.find((item) => item.id === editingId)?.module || `Homologação ${editingId}`}
            />
          </div>
        ) : undefined}
      >
        <HomologacaoForm
          statusOptions={statusOptions}
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

function HomologacaoForm({
  statusOptions,
  moduleOptions,
  clientOptions,
  openCycleLabel,
  onCancel,
  onSubmit,
  isLoading,
}: {
  statusOptions: any[];
  moduleOptions: any[];
  clientOptions: any[];
  openCycleLabel: string | null;
  onCancel: () => void;
  onSubmit: (data: Partial<Homologacao>) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    module_id: '',
    client_id: '',
    status: 'Pendente',
    latest_version: '',
    homologation_version: '',
    production_version: '',
    observation: '',
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
              O registro entra apenas no ciclo atual. Ciclos fechados ficam restritos aos relatórios gerenciais.
            </p>
          </div>
          <Badge variant={openCycleLabel ? 'success' : 'warning'}>
            {openCycleLabel ? 'Mês ativo' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>
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
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Status"
          options={statusOptions}
          value={formData.status}
          onChange={(e) => setFormData({ ...formData, status: e.target.value })}
        />
        <Input
          label="Versão Atual"
          value={formData.latest_version}
          onChange={(e) => setFormData({ ...formData, latest_version: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Versão Homologação"
          value={formData.homologation_version}
          onChange={(e) => setFormData({ ...formData, homologation_version: e.target.value })}
        />
        <Input
          label="Versão Produção"
          value={formData.production_version}
          onChange={(e) => setFormData({ ...formData, production_version: e.target.value })}
        />
      </div>
      <Input
        label="Observação"
        value={formData.observation}
        onChange={(e) => setFormData({ ...formData, observation: e.target.value })}
      />
      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" isLoading={isLoading} loadingText="Salvando...">
          Salvar
        </Button>
      </div>
    </form>
  );
}
