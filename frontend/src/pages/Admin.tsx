import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, atividadeApi, moduloApi, clienteApi } from '../services/api';
import { Button, Input, DataTable, Card, Badge, PdfUploadCard } from '../components';
import type {
  ActivityOwnerCatalog,
  ActivityStatusCatalog,
  AuthAuditLog,
  AuthUser,
  Cliente,
  Modulo,
} from '../types';

export function Admin() {
  const queryClient = useQueryClient();
  const [newModule, setNewModule] = useState('');
  const [newClient, setNewClient] = useState({ name: '', segment: '', owner: '' });
  const [ownerForm, setOwnerForm] = useState({ name: '', sort_order: 0, is_active: true });
  const [statusForm, setStatusForm] = useState({
    key: '',
    label: '',
    hint: '',
    sort_order: 0,
    is_active: true,
  });
  const [editingOwnerId, setEditingOwnerId] = useState<number | null>(null);
  const [editingStatusId, setEditingStatusId] = useState<number | null>(null);

  const { data: modules = [], isLoading: modulesLoading } = useQuery({
    queryKey: ['modulo'],
    queryFn: moduloApi.list,
  });

  const { data: clients = [], isLoading: clientsLoading } = useQuery({
    queryKey: ['cliente'],
    queryFn: clienteApi.list,
  });

  const { data: catalogs, isLoading: catalogsLoading } = useQuery({
    queryKey: ['atividade', 'catalogos'],
    queryFn: atividadeApi.catalogs,
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

  const createOwnerMutation = useMutation({
    mutationFn: atividadeApi.createOwner,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setEditingOwnerId(null);
      setOwnerForm({ name: '', sort_order: 0, is_active: true });
    },
  });

  const updateOwnerMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { name?: string; sort_order?: number; is_active?: number } }) =>
      atividadeApi.updateOwner(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setEditingOwnerId(null);
      setOwnerForm({ name: '', sort_order: 0, is_active: true });
    },
  });

  const deleteOwnerMutation = useMutation({
    mutationFn: atividadeApi.deleteOwner,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] }),
  });

  const createStatusMutation = useMutation({
    mutationFn: atividadeApi.createStatus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setEditingStatusId(null);
      setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { key?: string; label?: string; hint?: string; sort_order?: number; is_active?: number } }) =>
      atividadeApi.updateStatusCatalog(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setEditingStatusId(null);
      setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
    },
  });

  const deleteStatusMutation = useMutation({
    mutationFn: atividadeApi.deleteStatus,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] }),
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

  const ownerColumns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Responsável' },
    { key: 'sort_order', label: 'Ordem' },
    {
      key: 'is_active',
      label: 'Ativo',
      render: (item: ActivityOwnerCatalog) => (
        <Badge variant={item.is_active ? 'success' : 'warning'}>{item.is_active ? 'Sim' : 'Não'}</Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: ActivityOwnerCatalog) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setEditingOwnerId(item.id);
              setOwnerForm({
                name: item.name,
                sort_order: item.sort_order ?? 0,
                is_active: Boolean(item.is_active),
              });
            }}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={() => {
              if (window.confirm(`Excluir responsável "${item.name}"?`)) {
                deleteOwnerMutation.mutate(item.id);
              }
            }}
          >
            Excluir
          </Button>
        </div>
      ),
    },
  ];

  const statusColumns = [
    { key: 'id', label: 'ID' },
    { key: 'key', label: 'Chave' },
    { key: 'label', label: 'Status' },
    { key: 'hint', label: 'Ajuda', render: (item: ActivityStatusCatalog) => item.hint || '—' },
    { key: 'sort_order', label: 'Ordem' },
    {
      key: 'is_active',
      label: 'Ativo',
      render: (item: ActivityStatusCatalog) => (
        <Badge variant={item.is_active ? 'success' : 'warning'}>{item.is_active ? 'Sim' : 'Não'}</Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: ActivityStatusCatalog) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setEditingStatusId(item.id);
              setStatusForm({
                key: item.key,
                label: item.label,
                hint: item.hint || '',
                sort_order: item.sort_order ?? 0,
                is_active: Boolean(item.is_active),
              });
            }}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={() => {
              if (window.confirm(`Excluir status "${item.label}"?`)) {
                deleteStatusMutation.mutate(item.id);
              }
            }}
          >
            Excluir
          </Button>
        </div>
      ),
    },
  ];

  const handleSaveOwner = () => {
    const payload = {
      name: ownerForm.name.trim(),
      sort_order: Number(ownerForm.sort_order) || 0,
      is_active: ownerForm.is_active ? 1 : 0,
    };
    if (!payload.name) {
      return;
    }
    if (editingOwnerId) {
      updateOwnerMutation.mutate({ id: editingOwnerId, payload });
    } else {
      createOwnerMutation.mutate(payload);
    }
  };

  const handleSaveStatus = () => {
    const payload = {
      key: statusForm.key.trim(),
      label: statusForm.label.trim(),
      hint: statusForm.hint.trim(),
      sort_order: Number(statusForm.sort_order) || 0,
      is_active: statusForm.is_active ? 1 : 0,
    };
    if (!payload.key || !payload.label) {
      return;
    }
    if (editingStatusId) {
      updateStatusMutation.mutate({ id: editingStatusId, payload });
    } else {
      createStatusMutation.mutate(payload);
    }
  };

  const cancelOwnerEdit = () => {
    setEditingOwnerId(null);
    setOwnerForm({ name: '', sort_order: 0, is_active: true });
  };

  const cancelStatusEdit = () => {
    setEditingStatusId(null);
    setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administração</h1>
        <p className="text-gray-500 mt-1">Gerencie módulos, clientes, responsáveis e status das atividades.</p>
      </div>

      <PdfUploadCard scopeType="global" scopeLabel="Administração" />

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
            <DataTable columns={auditColumns} data={auditData.logs} keyExtractor={(item) => item.id} />
          ) : (
            <p className="text-sm text-gray-500">Nenhum evento de auditoria registrado ainda.</p>
          )}
        </Card>

        <Card
          title="Módulos"
          action={
            <Button size="sm" onClick={() => createModuleMutation.mutate({ name: newModule })} disabled={!newModule}>
              Adicionar
            </Button>
          }
        >
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

        <Card
          title="Clientes"
          action={
            <Button size="sm" onClick={() => createClientMutation.mutate(newClient)} disabled={!newClient.name}>
              Adicionar
            </Button>
          }
        >
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

        <Card
          title={editingOwnerId ? 'Editar responsável' : 'Responsáveis das atividades'}
          action={
            <div className="flex gap-2">
              {editingOwnerId && (
                <Button size="sm" variant="secondary" onClick={cancelOwnerEdit}>
                  Cancelar
                </Button>
              )}
              <Button size="sm" onClick={handleSaveOwner} disabled={!ownerForm.name.trim() || catalogsLoading}>
                {editingOwnerId ? 'Salvar' : 'Adicionar'}
              </Button>
            </div>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            <Input
              placeholder="Nome do responsável"
              value={ownerForm.name}
              onChange={(e) => setOwnerForm({ ...ownerForm, name: e.target.value })}
            />
            <Input
              type="number"
              placeholder="Ordem"
              value={ownerForm.sort_order}
              onChange={(e) => setOwnerForm({ ...ownerForm, sort_order: Number(e.target.value) })}
            />
            <label className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={ownerForm.is_active}
                onChange={(e) => setOwnerForm({ ...ownerForm, is_active: e.target.checked })}
              />
              Ativo
            </label>
          </div>
          {catalogsLoading ? (
            <div className="flex justify-center py-4">Carregando...</div>
          ) : (
            <DataTable columns={ownerColumns} data={catalogs?.owners ?? []} keyExtractor={(item) => item.id} />
          )}
        </Card>

        <Card
          title={editingStatusId ? 'Editar status' : 'Status das atividades'}
          action={
            <div className="flex gap-2">
              {editingStatusId && (
                <Button size="sm" variant="secondary" onClick={cancelStatusEdit}>
                  Cancelar
                </Button>
              )}
              <Button size="sm" onClick={handleSaveStatus} disabled={!statusForm.key.trim() || !statusForm.label.trim() || catalogsLoading}>
                {editingStatusId ? 'Salvar' : 'Adicionar'}
              </Button>
            </div>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
            <Input
              placeholder="Chave"
              value={statusForm.key}
              onChange={(e) => setStatusForm({ ...statusForm, key: e.target.value })}
            />
            <Input
              placeholder="Rótulo"
              value={statusForm.label}
              onChange={(e) => setStatusForm({ ...statusForm, label: e.target.value })}
            />
            <Input
              placeholder="Dica"
              value={statusForm.hint}
              onChange={(e) => setStatusForm({ ...statusForm, hint: e.target.value })}
            />
            <Input
              type="number"
              placeholder="Ordem"
              value={statusForm.sort_order}
              onChange={(e) => setStatusForm({ ...statusForm, sort_order: Number(e.target.value) })}
            />
          </div>
          <label className="mb-4 flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 w-fit">
            <input
              type="checkbox"
              checked={statusForm.is_active}
              onChange={(e) => setStatusForm({ ...statusForm, is_active: e.target.checked })}
            />
            Ativo
          </label>
          {catalogsLoading ? (
            <div className="flex justify-center py-4">Carregando...</div>
          ) : (
            <DataTable columns={statusColumns} data={catalogs?.statuses ?? []} keyExtractor={(item) => item.id} />
          )}
        </Card>
      </div>
    </div>
  );
}
