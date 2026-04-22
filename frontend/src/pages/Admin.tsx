import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, moduloApi, clienteApi } from '../services/api';
import { Button, Input, DataTable, Card } from '../components';
import type { AuthAuditLog, AuthUser, Modulo, Cliente } from '../types';

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

  const { data: usersData } = useQuery({
    queryKey: ['auth', 'users'],
    queryFn: () => authApi.users(),
  });

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['auth', 'audit-logs'],
    queryFn: () => authApi.auditLogs(50),
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

  const approveUserMutation = useMutation({
    mutationFn: authApi.approveUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
  });

  const deactivateUserMutation = useMutation({
    mutationFn: authApi.deactivateUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
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

  const userColumns = [
    { key: 'username', label: 'Usuário' },
    { key: 'email', label: 'E-mail' },
    { key: 'provider', label: 'Origem' },
    { key: 'approval_status', label: 'Status' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: AuthUser) => (
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => approveUserMutation.mutate(item.id)}>
            Aprovar
          </Button>
          <Button size="sm" variant="danger" onClick={() => deactivateUserMutation.mutate(item.id)}>
            Bloquear
          </Button>
        </div>
      ),
    },
  ];

  const auditColumns = [
    { key: 'created_at', label: 'Data', render: (item: AuthAuditLog) => new Date(item.created_at).toLocaleString('pt-BR') },
    { key: 'event_type', label: 'Evento' },
    { key: 'status', label: 'Status' },
    { key: 'actor_username', label: 'Ator' },
    { key: 'target_username', label: 'Alvo' },
    { key: 'provider', label: 'Origem' },
    {
      key: 'message',
      label: 'Mensagem',
      render: (item: AuthAuditLog) => item.message || '—',
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administração</h1>
        <p className="text-gray-500 mt-1">Gerencie módulos e clientes do sistema</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Acessos pendentes" className="lg:col-span-2">
          {usersData?.users?.some((user) => user.approval_status !== 'approved') ? (
            <DataTable
              columns={userColumns}
              data={usersData.users.filter((user) => user.approval_status !== 'approved')}
              keyExtractor={(item) => item.id}
            />
          ) : (
            <p className="text-sm text-gray-500">Nenhum acesso pendente no momento.</p>
          )}
        </Card>

        <Card title="Auditoria de acesso" className="lg:col-span-2">
          {auditLoading ? (
            <div className="flex justify-center py-4">Carregando...</div>
          ) : auditData?.logs?.length ? (
            <DataTable
              columns={auditColumns}
              data={auditData.logs}
              keyExtractor={(item) => item.id}
            />
          ) : (
            <p className="text-sm text-gray-500">Nenhum evento de auditoria registrado ainda.</p>
          )}
        </Card>

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
