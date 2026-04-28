import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { atividadeApi, releaseApi, reportsApi } from '../services/api';
import { Button, Input, Select, DataTable, Modal, Card, TipoBadge, Badge, PdfRecordUploadButton, PdfRecordStatusBadge, PdfIntelligencePanel } from '../components';
import type { Atividade, ActivityOwnerCatalog, ActivityStatusCatalog } from '../types';

type ActivityStatus = Atividade['status'];
type ViewMode = 'kanban' | 'table' | 'catalogos';

const DEFAULT_STATUS_COLUMNS = [
  { value: 'backlog', label: 'Pendente', hint: 'Itens recebidos e ainda não iniciados.' },
  { value: 'em_andamento', label: 'Em Andamento', hint: 'Em execução pela equipe.' },
  { value: 'em_revisao', label: 'Em Revisão', hint: 'Aguardando validação ou ajuste final.' },
  { value: 'concluida', label: 'Concluída', hint: 'Finalizada e pronta para relatório.' },
  { value: 'bloqueada', label: 'Bloqueada', hint: 'Dependência externa ou impedimento.' },
] as const;

export function Atividades() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('kanban');
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [intelligenceId, setIntelligenceId] = useState<number | null>(null);
  const [ownerForm, setOwnerForm] = useState({ name: '', sort_order: 0, is_active: true });
  const [statusForm, setStatusForm] = useState({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
  const [editingOwnerId, setEditingOwnerId] = useState<number | null>(null);
  const [editingStatusId, setEditingStatusId] = useState<number | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['atividade'],
    queryFn: () => atividadeApi.list(),
  });

  const { data: releases = [] } = useQuery({
    queryKey: ['release'],
    queryFn: releaseApi.list,
  });

  const { data: catalogs } = useQuery({
    queryKey: ['atividade', 'catalogos'],
    queryFn: atividadeApi.catalogs,
  });
  const { data: reportCycles = [] } = useQuery({
    queryKey: ['reports', 'cycles'],
    queryFn: () => reportsApi.cycles(),
  });
  const openCycle = reportCycles.find((cycle) => cycle.status === 'aberto') ?? null;
  const reportCycleId = openCycle?.id;
  const focusedActivity = items.find((item) => item.id === intelligenceId) ?? null;
  const reportFocus = focusedActivity
    ? {
        type: 'ticket',
        value: focusedActivity.ticket || String(focusedActivity.id),
        label: `Atividade: ${focusedActivity.ticket || `ID ${focusedActivity.id}`} · ${focusedActivity.title || 'Sem título'}`,
      }
    : null;

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
    anchor.download = reportCycleId ? `atividades-ciclo-${reportCycleId}.pdf` : 'atividades-relatorio.pdf';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  };

  const createOwnerMutation = useMutation({
    mutationFn: atividadeApi.createOwner,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setOwnerForm({ name: '', sort_order: 0, is_active: true });
      setEditingOwnerId(null);
    },
  });

  const updateOwnerMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { name?: string; sort_order?: number; is_active?: number } }) =>
      atividadeApi.updateOwner(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setOwnerForm({ name: '', sort_order: 0, is_active: true });
      setEditingOwnerId(null);
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
      setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
      setEditingStatusId(null);
    },
  });

  const updateStatusCatalogMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { key?: string; label?: string; hint?: string; sort_order?: number; is_active?: number } }) =>
      atividadeApi.updateStatusCatalog(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] });
      setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
      setEditingStatusId(null);
    },
  });

  const deleteStatusMutation = useMutation({
    mutationFn: atividadeApi.deleteStatus,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['atividade', 'catalogos'] }),
  });

  const releaseOptions = [
    { value: '', label: 'Sem release' },
    ...releases.map((r) => ({ value: String(r.id), label: `${r.release_name} (${r.version})` })),
  ];

  const statusColumns = useMemo(() => {
    const source = catalogs?.statuses?.length ? catalogs.statuses : DEFAULT_STATUS_COLUMNS;
    return source.map((status) => ({
      value: ('key' in status ? status.key : status.value) as ActivityStatus,
      label: status.label,
      hint: status.hint || '',
    }));
  }, [catalogs?.statuses]);

  const ownerOptions = useMemo(() => {
    const options = (catalogs?.owners ?? []).map((owner) => ({ value: owner.name, label: owner.name }));
    return [{ value: '', label: 'Selecione...' }, ...options];
  }, [catalogs?.owners]);

  const statusOptions = statusColumns.map((column) => ({ value: column.value, label: column.label }));
  const activityOwners = catalogs?.owners ?? [];
  const activityStatuses = catalogs?.statuses ?? [];

  const selectedActivity = useMemo(
    () => items.find((item) => item.id === editingId) ?? null,
    [editingId, items]
  );

  const groupedActivities = useMemo(() => {
    return statusColumns.reduce((acc, column) => {
      acc[column.value] = items.filter((item) => item.status === column.value);
      return acc;
    }, {} as Record<ActivityStatus, Atividade[]>);
  }, [items, statusColumns]);

  const moveActivity = (id: number, status: ActivityStatus) => {
    statusMutation.mutate({ id, status });
  };

  const columns = [
    { key: 'title', label: 'Título' },
    { key: 'ticket', label: 'Ticket' },
    {
      key: 'pdf',
      label: 'PDF',
      render: (item: Atividade) => <PdfRecordStatusBadge scopeType="atividade" recordId={item.id} />,
    },
    { key: 'tipo', label: 'Tipo', render: (item: Atividade) => <TipoBadge tipo={item.tipo} /> },
    { key: 'owner', label: 'Responsável', render: (item: Atividade) => item.owner || 'Sem responsável' },
    { key: 'executor', label: 'Executante', render: (item: Atividade) => item.executor || 'Sem executante' },
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
          <Button size="sm" variant="secondary" onClick={() => setIntelligenceId(item.id)}>
            Ver inteligência
          </Button>
          <PdfRecordUploadButton
            scopeType="atividade"
            scopeLabel="Atividades"
            recordId={item.id}
            recordLabel={`${item.ticket} • ${item.title || 'Atividade'}`}
          />
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
            <Button
              type="button"
              size="sm"
              variant={viewMode === 'catalogos' ? 'primary' : 'outline'}
              onClick={() => setViewMode('catalogos')}
              className="ml-1"
            >
              Catálogos
            </Button>
          </div>
          <Button type="button" variant="outline" onClick={() => void exportText()}>
            Texto do ciclo
          </Button>
          <Button type="button" variant="secondary" onClick={() => void openHtml()}>
            HTML do ciclo
          </Button>
          <Button type="button" variant="secondary" onClick={() => void exportPdf()}>
            PDF do ciclo
          </Button>
          <Button onClick={() => { setEditingId(null); setFormError(null); setIsModalOpen(true); }}>
            Nova Atividade
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

      {viewMode === 'kanban' ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
          {statusColumns.map((column) => (
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
      ) : viewMode === 'catalogos' ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <Card
            title={editingOwnerId ? 'Editar responsável' : 'Responsáveis'}
            action={
              <div className="flex gap-2">
                {editingOwnerId && (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditingOwnerId(null);
                      setOwnerForm({ name: '', sort_order: 0, is_active: true });
                    }}
                  >
                    Cancelar
                  </Button>
                )}
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    const payload = {
                      name: ownerForm.name.trim(),
                      sort_order: Number(ownerForm.sort_order) || 0,
                      is_active: ownerForm.is_active ? 1 : 0,
                    };
                    if (!payload.name) return;
                    if (editingOwnerId) {
                      updateOwnerMutation.mutate({ id: editingOwnerId, payload });
                    } else {
                      createOwnerMutation.mutate(payload);
                    }
                  }}
                  disabled={!ownerForm.name.trim()}
                >
                  {editingOwnerId ? 'Salvar' : 'Adicionar'}
                </Button>
              </div>
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <Input
                label="Nome"
                placeholder="Responsável"
                value={ownerForm.name}
                onChange={(e) => setOwnerForm({ ...ownerForm, name: e.target.value })}
              />
              <Input
                label="Ordem"
                type="number"
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
            <DataTable
              columns={[
                { key: 'id', label: 'ID' },
                { key: 'name', label: 'Nome' },
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
                        onClick={() => deleteOwnerMutation.mutate(item.id)}
                      >
                        Excluir
                      </Button>
                    </div>
                  ),
                },
              ]}
              data={activityOwners}
              keyExtractor={(item) => item.id}
            />
          </Card>

          <Card
            title={editingStatusId ? 'Editar status' : 'Status'}
            action={
              <div className="flex gap-2">
                {editingStatusId && (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditingStatusId(null);
                      setStatusForm({ key: '', label: '', hint: '', sort_order: 0, is_active: true });
                    }}
                  >
                    Cancelar
                  </Button>
                )}
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    const payload = {
                      key: statusForm.key.trim(),
                      label: statusForm.label.trim(),
                      hint: statusForm.hint.trim(),
                      sort_order: Number(statusForm.sort_order) || 0,
                      is_active: statusForm.is_active ? 1 : 0,
                    };
                    if (!payload.key || !payload.label) return;
                    if (editingStatusId) {
                      updateStatusCatalogMutation.mutate({ id: editingStatusId, payload });
                    } else {
                      createStatusMutation.mutate(payload);
                    }
                  }}
                  disabled={!statusForm.key.trim() || !statusForm.label.trim()}
                >
                  {editingStatusId ? 'Salvar' : 'Adicionar'}
                </Button>
              </div>
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
              <Input
                label="Chave"
                placeholder="backlog"
                value={statusForm.key}
                onChange={(e) => setStatusForm({ ...statusForm, key: e.target.value })}
              />
              <Input
                label="Rótulo"
                placeholder="Pendente"
                value={statusForm.label}
                onChange={(e) => setStatusForm({ ...statusForm, label: e.target.value })}
              />
              <Input
                label="Dica"
                placeholder="Itens recebidos..."
                value={statusForm.hint}
                onChange={(e) => setStatusForm({ ...statusForm, hint: e.target.value })}
              />
              <Input
                label="Ordem"
                type="number"
                value={statusForm.sort_order}
                onChange={(e) => setStatusForm({ ...statusForm, sort_order: Number(e.target.value) })}
              />
            </div>
            <label className="mb-4 flex w-fit items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={statusForm.is_active}
                onChange={(e) => setStatusForm({ ...statusForm, is_active: e.target.checked })}
              />
              Ativo
            </label>
            <DataTable
              columns={[
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
                        onClick={() => deleteStatusMutation.mutate(item.id)}
                      >
                        Excluir
                      </Button>
                    </div>
                  ),
                },
              ]}
              data={activityStatuses}
              keyExtractor={(item) => item.id}
            />
          </Card>
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

      <Card title="Inteligência da Atividade" action={intelligenceId ? (
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
              <MiniStat label="Ticket" value={items.find((item) => item.id === intelligenceId)?.ticket || '—'} />
              <MiniStat label="Título" value={items.find((item) => item.id === intelligenceId)?.title || '—'} />
              <MiniStat label="Responsável" value={items.find((item) => item.id === intelligenceId)?.owner || '—'} />
              <MiniStat label="Executante" value={items.find((item) => item.id === intelligenceId)?.executor || '—'} />
              <MiniStat label="Status" value={statusLabel((items.find((item) => item.id === intelligenceId)?.status || 'backlog') as ActivityStatus)} />
            </div>
            <p className="text-sm text-gray-600">
              {items.find((item) => item.id === intelligenceId)?.descricao_erro || 'Sem descrição cadastrada.'}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Selecione uma atividade na tabela ou no kanban para ver o foco inteligente.</p>
        )}
      </Card>

      <PdfIntelligencePanel
        scopeType="atividade"
        scopeLabel="Atividades"
        scopeId={intelligenceId}
        recordOptions={items.map((item) => ({
          id: item.id,
          label: `${item.ticket} • ${item.title || 'Atividade'}`,
        }))}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingId(null); setFormError(null); }}
        title={editingId ? 'Editar Atividade' : 'Nova Atividade'}
        footer={editingId ? (
          <div className="flex justify-end">
            <PdfRecordUploadButton
              scopeType="atividade"
              scopeLabel="Atividades"
              recordId={editingId}
              recordLabel={items.find((item) => item.id === editingId)?.ticket || `Atividade ${editingId}`}
            />
          </div>
        ) : undefined}
      >
        <AtividadeForm
          releaseOptions={releaseOptions}
          statusOptions={statusOptions}
          ownerOptions={ownerOptions}
          initialValue={selectedActivity}
          errorMessage={formError}
          openCycleLabel={openCycle ? openCycle.period_label || `Prestação ${openCycle.cycle_number || openCycle.id}` : null}
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

function MiniStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-gray-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-gray-900">{value}</p>
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
              <Badge variant="info">{activity.executor || activity.owner || 'Sem executante'}</Badge>
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
  ownerOptions,
  initialValue,
  errorMessage,
  openCycleLabel,
  onCancel,
  onSubmit,
  isLoading,
}: {
  releaseOptions: Array<{ value: string; label: string }>;
  statusOptions: Array<{ value: string; label: string }>;
  ownerOptions: Array<{ value: string; label: string }>;
  initialValue: Atividade | null;
  errorMessage: string | null;
  openCycleLabel: string | null;
  onCancel: () => void;
  onSubmit: (data: Partial<Atividade>) => void;
  isLoading: boolean;
}) {
  const executorOptions = useMemo(
    () => [
      { value: '', label: 'Selecione...' },
      ...ownerOptions.filter((option) => option.value).map((option) => ({ value: option.value, label: option.label })),
      { value: '__custom__', label: 'Outro executante' },
    ],
    [ownerOptions]
  );
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
  const [executorMode, setExecutorMode] = useState('');
  const [executorCustom, setExecutorCustom] = useState('');

  useEffect(() => {
    if (initialValue) {
      const normalizedExecutor = (initialValue.executor || '').trim();
      const matchedOwner = ownerOptions.find((option) => option.value === normalizedExecutor);
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
      if (matchedOwner) {
        setExecutorMode(matchedOwner.value);
        setExecutorCustom('');
      } else if (normalizedExecutor) {
        setExecutorMode('__custom__');
        setExecutorCustom(normalizedExecutor);
      } else {
        setExecutorMode('');
        setExecutorCustom('');
      }
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
    setExecutorMode('');
    setExecutorCustom('');
  }, [initialValue, ownerOptions]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
      onSubmit({
        ...formData,
        title: formData.title || formData.ticket || formData.descricao_erro || 'Atividade sem título',
        release_id: formData.release_id ? Number(formData.release_id) : null,
        owner: formData.owner || '',
        executor: executorMode === '__custom__' ? executorCustom.trim() : executorMode,
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
              A atividade será gravada apenas no ciclo atual. Fechamentos anteriores permanecem apenas em relatórios.
            </p>
          </div>
          <Badge variant={openCycleLabel ? 'success' : 'warning'}>
            {openCycleLabel ? 'Mês ativo' : 'Aguardando abertura'}
          </Badge>
        </div>
      </Card>
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
          label="Versão"
          options={releaseOptions}
          value={formData.release_id}
          onChange={(e) => setFormData({ ...formData, release_id: e.target.value })}
        />
        <Select
          label="Status"
          options={statusOptions}
          value={formData.status}
          required
          onChange={(e) => setFormData({ ...formData, status: e.target.value as ActivityStatus })}
        />
      </div>
      <div className="grid grid-cols-1 gap-4">
        <Select
          label="Responsável"
          options={ownerOptions}
          value={formData.owner}
          required
          onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
        />
        <Select
          label="Executante"
          options={executorOptions}
          value={executorMode}
          required
          onChange={(e) => setExecutorMode(e.target.value)}
        />
        {executorMode === '__custom__' ? (
          <Input
            label="Executante personalizado"
            placeholder="Nome de quem está executando a atividade"
            value={executorCustom}
            onChange={(e) => setExecutorCustom(e.target.value)}
            required
          />
        ) : null}
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
    backlog: 'Pendente',
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
