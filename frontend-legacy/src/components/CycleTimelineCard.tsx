import type { ReportCycle } from '../types';
import { Badge } from './Badge';
import { Button } from './Button';
import { Card } from './Card';

interface CycleTimelineCardProps {
  title: string;
  description: string;
  currentCycle: ReportCycle | null;
  previousCycle: ReportCycle | null;
  cycles: ReportCycle[];
  selectedCycleId?: string;
  onSelectCycle?: (cycleId: string) => void;
  onOpenPrevious?: () => void;
  onOpenCurrent?: () => void;
}

function cycleLabel(cycle: ReportCycle | null) {
  if (!cycle) {
    return 'Sem referência';
  }
  return cycle.period_label || `Prestação ${cycle.cycle_number || cycle.id}`;
}

function cycleStatusLabel(status: string) {
  return status === 'prestado' ? 'Fechado' : status === 'aberto' ? 'Aberto' : status;
}

export function CycleTimelineCard({
  title,
  description,
  currentCycle,
  previousCycle,
  cycles,
  selectedCycleId,
  onSelectCycle,
  onOpenPrevious,
  onOpenCurrent,
}: CycleTimelineCardProps) {
  const closedCycles = cycles.filter((cycle) => cycle.status === 'prestado');
  const currentLabel = cycleLabel(currentCycle);
  const previousLabel = cycleLabel(previousCycle);

  return (
    <Card title={title}>
      <div className="space-y-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm text-gray-600">{description}</p>
            <p className="mt-2 text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">
              Um mês aberto por vez. O histórico fechado só muda em Relatórios.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {onOpenPrevious && (
              <Button type="button" size="sm" variant="outline" disabled={!previousCycle} onClick={onOpenPrevious}>
                Abrir ciclo anterior
              </Button>
            )}
            {onOpenCurrent && (
              <Button type="button" size="sm" variant="secondary" disabled={!currentCycle || currentCycle.status === 'prestado'} onClick={onOpenCurrent}>
                Destacar mês atual
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-[#0d3b66]/15 bg-[#f8fbff] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês em trabalho</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">{currentLabel}</h3>
              </div>
              <Badge variant={currentCycle?.status === 'aberto' ? 'success' : 'warning'}>
                {cycleStatusLabel(currentCycle?.status || 'sem ciclo')}
              </Badge>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              O sistema grava somente neste ciclo enquanto ele estiver aberto.
            </p>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Mês anterior</p>
                <h3 className="mt-1 text-base font-semibold text-gray-900">{previousLabel}</h3>
              </div>
              <Badge variant={previousCycle ? 'warning' : 'default'}>
                {previousCycle ? cycleStatusLabel(previousCycle.status) : 'Sem histórico'}
              </Badge>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              O mês anterior fica consolidado e visível apenas como histórico e prestação fechada.
            </p>
          </div>
        </div>

        {closedCycles.length > 0 && (
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Linha do tempo</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {closedCycles.slice(0, 6).map((cycle) => {
                const label = cycleLabel(cycle);
                const isSelected = selectedCycleId ? Number(selectedCycleId) === cycle.id : false;
                return (
                  <button
                    key={cycle.id}
                    type="button"
                    className={`rounded-full border px-3 py-2 text-sm transition ${
                      isSelected
                        ? 'border-[#0d3b66] bg-[#0d3b66] text-white'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-[#0d3b66]/30 hover:bg-[#f7fbff]'
                    }`}
                    onClick={() => onSelectCycle?.(String(cycle.id))}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
