interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
  };

  return (
    <span
      className={`
        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  );
}

// Type-specific badges
export function TipoBadge({ tipo }: { tipo: string }) {
  const config: Record<string, { label: string; variant: BadgeProps['variant'] }> = {
    nova_funcionalidade: { label: 'Nova Funcionalidade', variant: 'success' },
    correcao_bug: { label: 'Correção de Bug', variant: 'danger' },
    melhoria: { label: 'Melhoria', variant: 'info' },
    em_elaboracao: { label: 'Em Elaboração', variant: 'warning' },
    em_aprovacao: { label: 'Em Aprovação', variant: 'warning' },
    aprovadas: { label: 'Aprovadas', variant: 'success' },
    aprovadas_sc: { label: 'Aprovadas SC', variant: 'info' },
    backlog: { label: 'Backlog', variant: 'warning' },
    em_andamento: { label: 'Em Andamento', variant: 'info' },
    em_revisao: { label: 'Em Revisão', variant: 'warning' },
    concluida: { label: 'Concluída', variant: 'success' },
    bloqueada: { label: 'Bloqueada', variant: 'danger' },
  };

  const { label, variant } = config[tipo] || { label: tipo, variant: 'default' as const };

  return <Badge variant={variant}>{label}</Badge>;
}
