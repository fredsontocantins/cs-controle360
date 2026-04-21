import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { releaseApi, moduloApi, clienteApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, PdfIntelligencePanel } from '../components';
import type { Release } from '../types';

export function Releases() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) =>
      releaseApi.uploadPdf(id, file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['release'] });
      queryClient.invalidateQueries({ queryKey: ['atividade'] });
      setUploadingId(null);
      alert(result.status === 'uploaded_and_processed'
        ? `PDF processado! ${result.activities_created} atividades extraídas.`
        : 'Upload concluído.');
    },
  });

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
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setIsModalOpen(true); }}>
            Editar
          </Button>
          <Button
            size="sm"
            variant="success"
            onClick={() => { setUploadingId(item.id); fileInputRef.current?.click(); }}
          >
            Upload PDF
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
          <h1 className="text-2xl font-bold text-gray-900">Releases</h1>
          <p className="text-gray-500 mt-1">Gerencie releases e faça upload de notas em PDF</p>
        </div>
        <Button onClick={() => { setEditingId(null); setIsModalOpen(true); }}>
          Nova Release
        </Button>
      </div>

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d3b66]"></div>
          </div>
        ) : (
          <DataTable columns={columns} data={items} keyExtractor={(item) => item.id} />
        )}
      </Card>

      <PdfIntelligencePanel
        scopeType="release"
        scopeLabel="Releases"
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.release_name || `Release ${item.id}`} (${item.version})`,
        }))}
      />

      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept="application/pdf"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && uploadingId) {
            uploadMutation.mutate({ id: uploadingId, file });
          }
          e.target.value = '';
        }}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); }}
        title={editingId ? 'Editar Release' : 'Nova Release'}
      >
        <ReleaseForm
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

function ReleaseForm({
  moduleOptions,
  clientOptions,
  onCancel,
  onSubmit,
  isLoading,
}: {
  moduleOptions: any[];
  clientOptions: any[];
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
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Nome da Release"
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
