import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { moduloApi, clienteApi } from '../services/api';
import { Button, Input, DataTable, Card } from '../components';
import type { Modulo, Cliente } from '../types';

export function Admin() {
  const queryClient = useQueryClient();
  const [newModule, setNewModule] = useState('');
  const [newClient, setNewClient] = useState({ name: '', segment: '', owner: '' });

  const { data: modules = [], isLoading: modulesLoading } = useQuery({
    queryKey: ['modulo'],
    queryFn: moduloApi.list,
  });

  const { data: clients = [], isLoading: clientsLoading } = useQuery({
    queryKey: ['cliente'],
    queryFn: clienteApi.list,
  });

  const createModuleMutation = useMutation({
    mutationFn: moduloApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modulo'] });
      setNewModule('');
    },
  });

  const deleteModuleMutation = useMutation({
    mutationFn: moduloApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['modulo'] }),
  });

  const createClientMutation = useMutation({
    mutationFn: clienteApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cliente'] });
      setNewClient({ name: '', segment: '', owner: '' });
    },
  });

  const deleteClientMutation = useMutation({
    mutationFn: clienteApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cliente'] }),
  });

  const moduleColumns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nome' },
    { key: 'description', label: 'Descrição' },
    { key: 'owner', label: 'Responsável' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Modulo) => (
        <Button size="sm" variant="danger" onClick={() => deleteModuleMutation.mutate(item.id)}>
          Excluir
        </Button>
      ),
    },
  ];

  const clientColumns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nome' },
    { key: 'segment', label: 'Segmento' },
    { key: 'owner', label: 'Responsável' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Cliente) => (
        <Button size="sm" variant="danger" onClick={() => deleteClientMutation.mutate(item.id)}>
          Excluir
        </Button>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administração</h1>
        <p className="text-gray-500 mt-1">Gerencie módulos e clientes do sistema</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Módulos" action={
          <Button size="sm" onClick={() => createModuleMutation.mutate({ name: newModule })} disabled={!newModule}>
            Adicionar
          </Button>
        }>
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="Nome do módulo"
              value={newModule}
              onChange={(e) => setNewModule(e.target.value)}
              className="flex-1"
            />
          </div>
          {modulesLoading ? (
            <div className="flex justify-center py-4">Carregando...</div>
          ) : (
            <DataTable columns={moduleColumns} data={modules} keyExtractor={(item) => item.id} />
          )}
        </Card>

        <Card title="Clientes" action={
          <Button size="sm" onClick={() => createClientMutation.mutate(newClient)} disabled={!newClient.name}>
            Adicionar
          </Button>
        }>
          <div className="space-y-2 mb-4">
            <Input
              placeholder="Nome do cliente"
              value={newClient.name}
              onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
            />
            <div className="flex gap-2">
              <Input
                placeholder="Segmento"
                value={newClient.segment}
                onChange={(e) => setNewClient({ ...newClient, segment: e.target.value })}
              />
              <Input
                placeholder="Responsável"
                value={newClient.owner}
                onChange={(e) => setNewClient({ ...newClient, owner: e.target.value })}
              />
            </div>
          </div>
          {clientsLoading ? (
            <div className="flex justify-center py-4">Carregando...</div>
          ) : (
            <DataTable columns={clientColumns} data={clients} keyExtractor={(item) => item.id} />
          )}
        </Card>
      </div>
    </div>
  );
}
