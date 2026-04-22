import type { ReactNode } from 'react';
import { Badge, Button } from './';

type DrawerMetric = {
  label: string;
  value: string | number;
};

interface ExecutiveInsightDrawerProps {
  open: boolean;
  title: string;
  subtitle?: string;
  badge?: string;
  metrics?: DrawerMetric[];
  bullets?: string[];
  onClose: () => void;
  actions?: ReactNode;
}

export function ExecutiveInsightDrawer({
  open,
  title,
  subtitle,
  badge,
  metrics = [],
  bullets = [],
  onClose,
  actions,
}: ExecutiveInsightDrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Fechar painel"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-gray-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-6 py-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              {badge && <Badge variant="info">{badge}</Badge>}
              <span className="text-xs uppercase tracking-wider text-gray-500">Análise Executiva</span>
            </div>
            <h3 className="mt-2 text-xl font-semibold text-gray-900">{title}</h3>
            {subtitle && <p className="mt-1 text-sm text-gray-600">{subtitle}</p>}
          </div>
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Fechar
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {metrics.length > 0 && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {metrics.map((metric) => (
                <div key={`${metric.label}-${metric.value}`} className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-wider text-gray-500">{metric.label}</p>
                  <p className="mt-1 text-base font-semibold text-gray-900">{metric.value}</p>
                </div>
              ))}
            </div>
          )}

          {actions && <div className="mt-4">{actions}</div>}

          <div className="mt-5 space-y-3">
            {bullets.map((bullet, index) => (
              <div key={`${title}-${index}`} className="rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Inteligência {index + 1}</p>
                <p className="mt-1 text-sm text-gray-700">{bullet}</p>
              </div>
            ))}
            {bullets.length === 0 && <p className="text-sm text-gray-500">Sem inteligência adicional para este recorte.</p>}
          </div>
        </div>
      </aside>
    </div>
  );
}
