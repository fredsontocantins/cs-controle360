import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customizacaoApi, moduloApi, clienteApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, TipoBadge, PdfIntelligencePanel } from '../components';
import type { Customizacao } from '../types';

export function Customizacoes() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

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
    { key: 'stage', label: 'Estágio', render: (item: Customizacao) => <TipoBadge tipo={item.stage} /> },
    { key: 'proposal', label: 'Proposta' },
    { key: 'subject', label: 'Assunto' },
    { key: 'owner', label: 'Responsável' },
    { key: 'pf', label: 'PF' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Customizacao) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setIsModalOpen(true); }}>
            Editar
          </Button>
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
        <Button onClick={() => { setEditingId(null); setIsModalOpen(true); }}>
          Nova Customização
        </Button>
      </div>

      <PdfIntelligencePanel
        scopeType="customizacao"
        scopeLabel="Customizações"
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.proposal || item.subject || `Customização ${item.id}`}`,
        }))}
      />

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d3b66]"></div>
          </div>
        ) : (
          <DataTable columns={columns} data={items} keyExtractor={(item) => item.id} />
        )}
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); }}
        title={editingId ? 'Editar Customização' : 'Nova Customização'}
      >
        <CustomizacaoForm
          stageOptions={stageOptions}
          moduleOptions={moduleOptions}
          clientOptions={clientOptions}
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

function CustomizacaoForm({
  stageOptions,
  moduleOptions,
  clientOptions,
  onCancel,
  onSubmit,
  isLoading,
}: {
  stageOptions: any[];
  moduleOptions: any[];
  clientOptions: any[];
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
