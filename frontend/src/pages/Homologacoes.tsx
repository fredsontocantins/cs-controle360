import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { homologacaoApi, moduloApi, clienteApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, Badge, PdfUploadCard, PdfIntelligencePanel } from '../components';
import type { Homologacao } from '../types';

export function Homologacoes() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

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
        <Button onClick={() => { setEditingId(null); setIsModalOpen(true); }}>
          Nova Homologação
        </Button>
      </div>

      <PdfUploadCard
        scopeType="homologacao"
        scopeLabel="Homologações"
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.module || 'Sem módulo'}${item.client ? ` • ${item.client}` : ''}`,
        }))}
      />

      <PdfIntelligencePanel
        scopeType="homologacao"
        scopeLabel="Homologações"
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.module || 'Sem módulo'}${item.client ? ` • ${item.client}` : ''}`,
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
        title={editingId ? 'Editar Homologação' : 'Nova Homologação'}
      >
        <HomologacaoForm
          statusOptions={statusOptions}
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

function HomologacaoForm({
  statusOptions,
  moduleOptions,
  clientOptions,
  onCancel,
  onSubmit,
  isLoading,
}: {
  statusOptions: any[];
  moduleOptions: any[];
  clientOptions: any[];
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
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Salvando...' : 'Salvar'}
        </Button>
      </div>
    </form>
  );
}
