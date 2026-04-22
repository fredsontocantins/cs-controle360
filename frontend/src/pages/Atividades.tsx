import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { atividadeApi, releaseApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, TipoBadge, Badge, PdfIntelligencePanel } from '../components';
import type { Atividade } from '../types';

const STATUS_COLUMNS = [
  { value: 'backlog', label: 'Backlog', hint: 'Itens recebidos e ainda não iniciados.' },
  { value: 'em_andamento', label: 'Em Andamento', hint: 'Em execução pela equipe.' },
  { value: 'em_revisao', label: 'Em Revisão', hint: 'Aguardando validação ou ajuste final.' },
  { value: 'concluida', label: 'Concluída', hint: 'Finalizada e pronta para relatório.' },
  { value: 'bloqueada', label: 'Bloqueada', hint: 'Dependência externa ou impedimento.' },
] as const;

type ActivityStatus = Atividade['status'];

export function Atividades() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'kanban' | 'table'>('kanban');
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['atividade'],
    queryFn: () => atividadeApi.list(),
  });

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const createMutation = useMutation({
    mutationFn: atividadeApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade'] });
      setIsModalOpen(false);
      setEditingId(null);
      setFormError(null);
    },
    onError: (error: any) => {
      setFormError(error?.response?.data?.detail || 'Não foi possível salvar a atividade.');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Atividade> }) =>
      atividadeApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade'] });
      setIsModalOpen(false);
      setEditingId(null);
      setFormError(null);
    },
    onError: (error: any) => {
      setFormError(error?.response?.data?.detail || 'Não foi possível atualizar a atividade.');
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ActivityStatus }) =>
      atividadeApi.updateStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['atividade'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: atividadeApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['atividade'] }),
  });

  const releaseOptions = [
    { value: '', label: 'Sem release' },
    ...releases.map((r) => ({ value: String(r.id), label: `${r.release_name} (${r.version})` })),
  ];

  const statusOptions = STATUS_COLUMNS.map((column) => ({ value: column.value, label: column.label }));

  const selectedActivity = useMemo(
    () => items.find((item) => item.id === editingId) ?? null,
    [editingId, items]
  );

  const groupedActivities = useMemo(() => {
    return STATUS_COLUMNS.reduce((acc, column) => {
      acc[column.value] = items.filter((item) => item.status === column.value);
      return acc;
    }, {} as Record<ActivityStatus, Atividade[]>);
  }, [items]);

  const moveActivity = (id: number, status: ActivityStatus) => {
    statusMutation.mutate({ id, status });
  };

  const columns = [
    { key: 'title', label: 'Título' },
    { key: 'ticket', label: 'Ticket' },
    { key: 'tipo', label: 'Tipo', render: (item: Atividade) => <TipoBadge tipo={item.tipo} /> },
    { key: 'owner', label: 'Responsável', render: (item: Atividade) => item.owner || 'Sem responsável' },
    { key: 'status', label: 'Status', render: (item: Atividade) => <Badge variant={statusVariant(item.status)}>{statusLabel(item.status)}</Badge> },
    { key: 'descricao_erro', label: 'Resumo' },
    { key: 'resolucao', label: 'Impacto/Entrega' },
    { key: 'created_at', label: 'Criado em', render: (item: Atividade) => item.created_at?.slice(0, 10) || '---' },
    {
      key: 'actions',
      label: 'Ações',
      render: (item: Atividade) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => { setEditingId(item.id); setFormError(null); setIsModalOpen(true); }}>
            Editar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => moveActivity(item.id, nextStatus(item.status, 1))}>
            Avançar
          </Button>
          <Button size="sm" variant="secondary" onClick={() => moveActivity(item.id, nextStatus(item.status, -1))}>
            Recuar
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
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Atividades</h1>
          <p className="text-gray-500 mt-1">Kanban operacional e registro extraído dos PDFs de release.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="inline-flex rounded-xl border border-gray-200 bg-white p-1">
            <Button
              type="button"
              size="sm"
              variant={viewMode === 'kanban' ? 'primary' : 'outline'}
              onClick={() => setViewMode('kanban')}
            >
              Kanban
            </Button>
            <Button
              type="button"
              size="sm"
              variant={viewMode === 'table' ? 'primary' : 'outline'}
              onClick={() => setViewMode('table')}
              className="ml-1"
            >
              Tabela
            </Button>
          </div>
          <Button onClick={() => { setEditingId(null); setFormError(null); setIsModalOpen(true); }}>
            Nova Atividade
          </Button>
        </div>
      </div>

      {viewMode === 'kanban' ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
          {STATUS_COLUMNS.map((column) => (
            <KanbanColumn
              key={column.value}
              title={column.label}
              hint={column.hint}
              activities={groupedActivities[column.value]}
              onDrop={(activityId) => moveActivity(activityId, column.value)}
              onDragStart={(activityId) => setDraggedId(activityId)}
              onDragEnd={() => setDraggedId(null)}
              onMove={(activityId, direction) => moveActivity(activityId, nextStatus(column.value, direction))}
              onEdit={(activityId) => { setEditingId(activityId); setFormError(null); setIsModalOpen(true); }}
              onDelete={(activityId) => deleteMutation.mutate(activityId)}
              draggedId={draggedId}
            />
          ))}
        </div>
      ) : (
        <Card>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d3b66]"></div>
            </div>
          ) : (
            <DataTable columns={columns} data={items} keyExtractor={(item) => item.id} />
          )}
        </Card>
      )}

      <PdfIntelligencePanel
        scopeType="atividade"
        scopeLabel="Atividades"
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.ticket} • ${item.title || 'Atividade'}`,
        }))}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); setFormError(null); }}
        title={editingId ? 'Editar Atividade' : 'Nova Atividade'}
      >
        <AtividadeForm
          releaseOptions={releaseOptions}
          statusOptions={statusOptions}
          initialValue={selectedActivity}
          errorMessage={formError}
          onCancel={() => { setIsModalOpen(false); setEditingId(null); setFormError(null); }}
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

function KanbanColumn({
  title,
  hint,
  activities,
  onDrop,
  onDragStart,
  onDragEnd,
  onMove,
  onEdit,
  onDelete,
  draggedId,
}: {
  title: string;
  hint: string;
  activities: Atividade[];
  onDrop: (activityId: number) => void;
  onDragStart: (activityId: number) => void;
  onDragEnd: () => void;
  onMove: (activityId: number, direction: -1 | 1) => void;
  onEdit: (activityId: number) => void;
  onDelete: (activityId: number) => void;
  draggedId: number | null;
}) {
  return (
    <div
      className="rounded-2xl border border-gray-200 bg-white/90 p-4 shadow-sm"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const raw = e.dataTransfer.getData('text/plain');
        const activityId = Number(raw);
        if (!Number.isNaN(activityId)) {
          onDrop(activityId);
        }
      }}
    >
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">{title}</h3>
          <Badge variant="info">{activities.length}</Badge>
        </div>
        <p className="mt-2 text-xs text-gray-500">{hint}</p>
      </div>

      <div className="space-y-3">
        {activities.map((activity) => (
          <article
            key={activity.id}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData('text/plain', String(activity.id));
              e.dataTransfer.effectAllowed = 'move';
              onDragStart(activity.id);
            }}
            onDragEnd={onDragEnd}
            className={`cursor-grab rounded-xl border p-3 transition-all ${
              draggedId === activity.id
                ? 'border-[#0d3b66] shadow-md ring-2 ring-[#0d3b66]/20'
                : 'border-gray-200 hover:border-[#0d3b66]/30 hover:shadow-sm'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900 line-clamp-2">{activity.title || activity.ticket}</p>
                <p className="text-xs font-semibold text-[#0d3b66]">{activity.ticket}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <TipoBadge tipo={activity.tipo} />
              <Badge variant="default">{activity.owner || 'Sem responsável'}</Badge>
              <Badge variant={statusVariant(activity.status)}>{statusLabel(activity.status)}</Badge>
            </div>
              </div>
              <span className="text-[11px] text-gray-400">{activity.created_at?.slice(0, 10) || '---'}</span>
            </div>

            <p className="mt-3 text-sm font-medium text-gray-900 line-clamp-2">
              {activity.descricao_erro || 'Sem descrição'}
            </p>
            <p className="mt-2 text-xs text-gray-600 line-clamp-3">
              {activity.resolucao || 'Sem resolução registrada'}
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button type="button" size="sm" variant="outline" onClick={() => onEdit(activity.id)}>
                Editar
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => onMove(activity.id, -1)}>
                Anterior
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => onMove(activity.id, 1)}>
                Próximo
              </Button>
              <Button type="button" size="sm" variant="danger" onClick={() => onDelete(activity.id)}>
                Excluir
              </Button>
            </div>
          </article>
        ))}

        {activities.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-center text-sm text-gray-500">
            Arraste uma atividade para cá.
          </div>
        )}
      </div>
    </div>
  );
}

function AtividadeForm({
  releaseOptions,
  statusOptions,
  initialValue,
  errorMessage,
  onCancel,
  onSubmit,
  isLoading,
}: {
  releaseOptions: Array<{ value: string; label: string }>;
  statusOptions: Array<{ value: string; label: string }>;
  initialValue: Atividade | null;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (data: Partial<Atividade>) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    title: '',
    release_id: '',
    owner: '',
    tipo: 'correcao_bug' as Atividade['tipo'],
    ticket: '',
    descricao_erro: '',
    resolucao: '',
    status: 'backlog' as ActivityStatus,
  });

  useEffect(() => {
    if (initialValue) {
      setFormData({
        title: initialValue.title || initialValue.ticket || '',
        release_id: initialValue.release_id ? String(initialValue.release_id) : '',
        owner: initialValue.owner || '',
        tipo: initialValue.tipo,
        ticket: initialValue.ticket || '',
        descricao_erro: initialValue.descricao_erro || '',
        resolucao: initialValue.resolucao || '',
        status: initialValue.status,
      });
      return;
    }

    setFormData({
      title: '',
      release_id: '',
      owner: '',
      tipo: 'correcao_bug',
      ticket: '',
      descricao_erro: '',
      resolucao: '',
      status: 'backlog',
    });
  }, [initialValue]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          ...formData,
          title: formData.title || formData.ticket || formData.descricao_erro || 'Atividade sem título',
          release_id: formData.release_id ? Number(formData.release_id) : null,
          owner: formData.owner || '',
        });
      }}
      className="space-y-4"
    >
      {errorMessage && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4">
        <Input
          label="Título"
          placeholder="Resumo da atividade"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Release"
          options={releaseOptions}
          value={formData.release_id}
          onChange={(e) => setFormData({ ...formData, release_id: e.target.value })}
        />
        <Select
          label="Status"
          options={statusOptions}
          value={formData.status}
          onChange={(e) => setFormData({ ...formData, status: e.target.value as ActivityStatus })}
        />
      </div>
      <div className="grid grid-cols-1 gap-4">
        <Input
          label="Responsável"
          placeholder="Nome do responsável"
          value={formData.owner}
          onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Ticket"
          placeholder="Ex: HOM-1234"
          value={formData.ticket}
          onChange={(e) => setFormData({ ...formData, ticket: e.target.value })}
          required
        />
        <Select
          label="Tipo"
          options={[
            { value: 'correcao_bug', label: 'Correção de Bug' },
            { value: 'nova_funcionalidade', label: 'Nova Funcionalidade' },
            { value: 'melhoria', label: 'Melhoria' },
          ]}
          value={formData.tipo}
          onChange={(e) => setFormData({ ...formData, tipo: e.target.value as Atividade['tipo'] })}
        />
      </div>
      <Input
        label="Descrição do Erro/Solicitação"
        value={formData.descricao_erro}
        onChange={(e) => setFormData({ ...formData, descricao_erro: e.target.value })}
      />
      <Input
        label="Resolução"
        value={formData.resolucao}
        onChange={(e) => setFormData({ ...formData, resolucao: e.target.value })}
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

function statusLabel(status: ActivityStatus) {
  return {
    backlog: 'Backlog',
    em_andamento: 'Em Andamento',
    em_revisao: 'Em Revisão',
    concluida: 'Concluída',
    bloqueada: 'Bloqueada',
  }[status];
}

function statusVariant(status: ActivityStatus) {
  return ({
    backlog: 'warning',
    em_andamento: 'info',
    em_revisao: 'warning',
    concluida: 'success',
    bloqueada: 'danger',
  } as const)[status];
}

function nextStatus(status: ActivityStatus, direction: -1 | 1): ActivityStatus {
  const order: ActivityStatus[] = ['backlog', 'em_andamento', 'em_revisao', 'concluida', 'bloqueada'];
  const index = order.indexOf(status);
  if (index === -1) {
    return 'backlog';
  }

  if (status === 'bloqueada' && direction === 1) {
    return 'backlog';
  }

  const nextIndex = Math.max(0, Math.min(order.length - 1, index + direction));
  return order[nextIndex];
}
