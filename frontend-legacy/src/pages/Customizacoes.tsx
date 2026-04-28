import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customizacaoApi, moduloApi, clienteApi, reportsApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, Badge, TipoBadge, PdfRecordUploadButton, PdfRecordStatusBadge, PdfIntelligencePanel } from '../components';
import type { Customizacao } from '../types';

export function Customizacoes() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [intelligenceId, setIntelligenceId] = useState<number | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['customizacao'],
    queryFn: customizacaoApi.list,
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
  const focusedCustomizacao = items.find((item) => item.id === intelligenceId) ?? null;
  const reportFocus = focusedCustomizacao
    ? {
        type: 'module',
        value: focusedCustomizacao.module || String(focusedCustomizacao.module_id || ''),
        label: `Customização: ${focusedCustomizacao.proposal || focusedCustomizacao.subject || `ID ${focusedCustomizacao.id}`}`,
      }
    : null;

  const createMutation = useMutation({
    mutationFn: customizacaoApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customizacao'] });
      setIsModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Customizacao> }) =>
      customizacaoApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customizacao'] });
      setIsModalOpen(false);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: customizacaoApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customizacao'] }),
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
    anchor.download = reportCycleId ? `customizacoes-ciclo-${reportCycleId}.pdf` : 'customizacoes-relatorio.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const stageOptions = [
    { value: 'em_elaboracao', label: 'Em Elaboração' },
    { value: 'em_aprovacao', label: 'Em Aprovação' },
    { value: 'aprovadas', label: 'Aprovadas' },
    { value: 'aprovadas_sc', label: 'Propostas Aprovadas SC' },
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
    { key: 'client', label: 'Cliente' },
    { key: 'module', label: 'Módulo' },
    {
      key: 'pdf',
      label: 'PDF',
      render: (item: Customizacao) => <PdfRecordStatusBadge scopeType="customizacao" recordId={item.id} />,
    },
    { key: 'stage', label: 'Estágio', render: (item: Customizacao) => <TipoBadge tipo={item.stage} /> },
    { key: 'proposal', label: 'Proposta' },
    { key: 'subject', label: 'Assunto' },
    { key: 'owner', label: 'Responsável' },
    { key: 'pf', label: 'PF' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Customizacao) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setIsModalOpen(true); }}>
            Editar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceId(item.id)}>
            Ver inteligência
          </Button>
          <PdfRecordUploadButton
            scopeType="customizacao"
            scopeLabel="Customizações"
            recordId={item.id}
            recordLabel={item.proposal || item.subject || `Customização ${item.id}`}
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
          <h1 className="text-2xl font-bold text-gray-900">Customizações</h1>
          <p className="text-gray-500 mt-1">Gerencie proposals e customizações</p>
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
            Nova Customização
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

      <Card title="Inteligência da Customização" action={intelligenceId ? (
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
              <MiniStat label="Cliente" value={items.find((item) => item.id === intelligenceId)?.client || '—'} />
              <MiniStat label="Módulo" value={items.find((item) => item.id === intelligenceId)?.module || '—'} />
              <MiniStat label="Estágio" value={items.find((item) => item.id === intelligenceId)?.stage || '—'} />
              <MiniStat label="Responsável" value={items.find((item) => item.id === intelligenceId)?.owner || '—'} />
            </div>
            <p className="text-sm text-gray-600">
              {items.find((item) => item.id === intelligenceId)?.observations || 'Sem observações cadastradas.'}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Selecione uma customização na tabela para ver o foco inteligente.</p>
        )}
      </Card>

      <PdfIntelligencePanel
        scopeType="customizacao"
        scopeLabel="Customizações"
        scopeId={intelligenceId}
        recordOptions={items.map((item) => ({
          id: item.id,
          label: item.proposal || item.subject || `Customização ${item.id}`,
        }))}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); }}
        title={editingId ? 'Editar Customização' : 'Nova Customização'}
        footer={editingId ? (
          <div className="flex justify-end">
            <PdfRecordUploadButton
              scopeType="customizacao"
              scopeLabel="Customizações"
              recordId={editingId}
              recordLabel={items.find((item) => item.id === editingId)?.proposal || `Customização ${editingId}`}
            />
          </div>
        ) : undefined}
      >
        <CustomizacaoForm
          stageOptions={stageOptions}
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

function CustomizacaoForm({
  stageOptions,
  moduleOptions,
  clientOptions,
  openCycleLabel,
  onCancel,
  onSubmit,
  isLoading,
}: {
  stageOptions: any[];
  moduleOptions: any[];
  clientOptions: any[];
  openCycleLabel: string | null;
  onCancel: () => void;
  onSubmit: (data: Partial<Customizacao>) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    stage: 'em_elaboracao',
    proposal: '',
    subject: '',
    client_id: '',
    module_id: '',
    owner: '',
    pf: '',
    value: '',
    observations: '',
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          ...formData,
          client_id: formData.client_id ? Number(formData.client_id) : null,
          module_id: formData.module_id ? Number(formData.module_id) : null,
          pf: formData.pf ? Number(formData.pf) : null,
          value: formData.value ? Number(formData.value) : null,
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
              O cadastro atual pertence somente ao ciclo operacional ativo. O histórico fechado fica no relatório.
            </p>
          </div>
          <Badge variant={openCycleLabel ? 'success' : 'warning'}>
            {openCycleLabel ? 'Mês ativo' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Estágio"
          options={stageOptions}
          value={formData.stage}
          onChange={(e) => setFormData({ ...formData, stage: e.target.value })}
        />
        <Input
          label="Proposta"
          value={formData.proposal}
          onChange={(e) => setFormData({ ...formData, proposal: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Cliente"
          options={clientOptions}
          value={formData.client_id}
          onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
        />
        <Select
          label="Módulo"
          options={moduleOptions}
          value={formData.module_id}
          onChange={(e) => setFormData({ ...formData, module_id: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Assunto"
          value={formData.subject}
          onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
        />
        <Input
          label="Responsável"
          value={formData.owner}
          onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="PF"
          type="number"
          step="0.1"
          value={formData.pf}
          onChange={(e) => setFormData({ ...formData, pf: e.target.value })}
        />
        <Input
          label="Valor"
          type="number"
          step="0.01"
          value={formData.value}
          onChange={(e) => setFormData({ ...formData, value: e.target.value })}
        />
      </div>
      <Input
        label="Observações"
        value={formData.observations}
        onChange={(e) => setFormData({ ...formData, observations: e.target.value })}
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
