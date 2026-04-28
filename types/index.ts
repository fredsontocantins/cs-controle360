export interface Homologacao {
  id: string;
  module: string;
  module_id: string | null;
  status: string;
  check_date: string | null;
  observation: string | null;
  latest_version: string | null;
  homologation_version: string | null;
  production_version: string | null;
  homologated: string | null;
  client_presentation: string | null;
  applied: string | null;
  monthly_versions: Record<string, unknown> | null;
  requested_production_date: string | null;
  production_date: string | null;
  client: string | null;
  client_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Customizacao {
  id: string;
  stage: string;
  proposal: string;
  subject: string;
  client: string | null;
  module: string | null;
  module_id: string | null;
  owner: string | null;
  received_at: string | null;
  status: string | null;
  pf: number | null;
  value: number | null;
  observations: string | null;
  pdf_path: string | null;
  client_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Atividade {
  id: string;
  title: string;
  release_id: string | null;
  owner: string | null;
  executor: string | null;
  tipo: 'nova_funcionalidade' | 'correcao_bug' | 'melhoria';
  ticket: string | null;
  descricao_erro: string | null;
  resolucao: string | null;
  status: 'backlog' | 'em_andamento' | 'em_revisao' | 'concluida' | 'bloqueada';
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ActivityOwner {
  id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface ActivityStatus {
  id: string;
  key: string;
  label: string;
  hint: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface Release {
  id: string;
  module: string | null;
  module_id: string | null;
  release_name: string;
  version: string;
  applies_on: string | null;
  notes: string | null;
  client: string | null;
  pdf_path: string | null;
  client_id: string | null;
  created_at: string;
}

export interface Cliente {
  id: string;
  name: string;
  segment: string | null;
  owner: string | null;
  notes: string | null;
  created_at: string;
}

export interface Modulo {
  id: string;
  name: string;
  description: string | null;
  owner: string | null;
  created_at: string;
}

export interface Playbook {
  id: string;
  title: string;
  origin: 'manual' | 'erro' | 'release' | 'predicao';
  source_type: string | null;
  source_id: string | null;
  source_key: string | null;
  source_label: string | null;
  area: string | null;
  priority_score: number | null;
  priority_level: 'alta' | 'media' | 'baixa';
  status: 'ativo' | 'prestado' | 'revisar' | 'arquivado';
  summary: string | null;
  content_json: Record<string, unknown> | null;
  metrics_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface ReportCycle {
  id: string;
  cycle_number: number | null;
  scope_type: string | null;
  scope_id: string | null;
  scope_label: string | null;
  period_label: string | null;
  status: 'aberto' | 'prestado';
  notes: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface Profile {
  id: string;
  username: string | null;
  full_name: string | null;
  role: 'admin' | 'user';
  approval_status: 'approved' | 'pending' | 'blocked';
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Summary {
  homologacoes: number;
  customizacoes: number;
  atividades: number;
  releases: number;
  clientes: number;
  modulos: number;
  activity_by_status?: Record<string, number>;
  activity_by_owner?: Array<{ owner: string; count: number }>;
}
