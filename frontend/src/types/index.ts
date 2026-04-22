export interface Homologacao {
  id: number;
  module: string;
  module_id: number | null;
  status: string;
  check_date: string | null;
  observation: string | null;
  latest_version: string | null;
  homologation_version: string | null;
  production_version: string | null;
  homologated: string | null;
  client_presentation: string | null;
  applied: string | null;
  monthly_versions: Record<string, any> | null;
  requested_production_date: string | null;
  production_date: string | null;
  client: string | null;
  client_id: number | null;
}

export interface Customizacao {
  id: number;
  stage: string;
  proposal: string;
  subject: string;
  client: string;
  module: string;
  module_id: number | null;
  owner: string;
  received_at: string | null;
  status: string;
  pf: number | null;
  value: number | null;
  observations: string | null;
  pdf_path: string | null;
  client_id: number | null;
}

export interface Atividade {
  id: number;
  title: string;
  release_id: number | null;
  owner: string | null;
  executor: string | null;
  tipo: 'nova_funcionalidade' | 'correcao_bug' | 'melhoria';
  ticket: string;
  descricao_erro: string;
  resolucao: string;
  status: 'backlog' | 'em_andamento' | 'em_revisao' | 'concluida' | 'bloqueada';
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ActivityOwnerCatalog {
  id: number;
  name: string;
  sort_order: number;
  is_active: number;
  created_at: string;
}

export interface ActivityStatusCatalog {
  id: number;
  key: 'backlog' | 'em_andamento' | 'em_revisao' | 'concluida' | 'bloqueada' | string;
  label: string;
  hint: string | null;
  sort_order: number;
  is_active: number;
  created_at: string;
}

export interface ActivityCatalogs {
  owners: ActivityOwnerCatalog[];
  statuses: ActivityStatusCatalog[];
}

export interface Release {
  id: number;
  module: string;
  module_id: number | null;
  release_name: string;
  version: string;
  applies_on: string | null;
  notes: string | null;
  client: string;
  pdf_path: string | null;
  client_id: number | null;
  created_at: string;
}

export interface Cliente {
  id: number;
  name: string;
  segment: string;
  owner: string;
  notes: string | null;
  created_at: string;
}

export interface Modulo {
  id: number;
  name: string;
  description: string;
  owner: string;
  created_at: string;
}

export interface TicketSummary {
  generated_at: string;
  total: number;
  scope?: {
    release_id: number | null;
    release_name: string | null;
  };
  current_cycle?: {
    label: string | null;
    cycle_number: number | null;
    homologacoes: number;
    customizacoes: number;
    atividades: number;
    releases: number;
  } | null;
  previous_cycle?: {
    label: string | null;
    cycle_number: number | null;
    homologacoes: number;
    customizacoes: number;
    atividades: number;
    releases: number;
  } | null;
  totals?: {
    modules: number;
    releases: number;
    tickets: number;
    corrections: number;
    improvements: number;
    features: number;
  };
  by_type: {
    correcao_bug: number;
    nova_funcionalidade: number;
    melhoria: number;
  };
  by_status?: Record<string, number>;
  module_summary?: Array<{
    module: string;
    description?: string;
    owner?: string;
    releases: number;
    corrections: number;
    improvements: number;
    features?: number;
    tickets: number;
    latest_version: string;
    latest_release: string;
    share: number;
    themes?: Array<{ theme: string; count: number; examples: string[] }>;
    top_tickets?: Array<{
      ticket: string;
      title: string;
      tipo_label: string;
      status: string;
      descricao: string;
      resolucao: string;
    }>;
    pdf_documents?: number;
    pdf_topics?: string[];
    explanation?: string;
  }>;
  release_summary?: Array<{
    id: number;
    module: string;
    release_name: string;
    version: string;
    applies_on: string | null;
    tickets: number;
    corrections: number;
    improvements: number;
    by_status: Record<string, number>;
    last_activity_at: string | null;
  }>;
  themes?: Array<{
    theme: string;
    count: number;
    examples: string[];
  }>;
  insights?: Array<{
    title: string;
    detail: string;
    severity: 'info' | 'warning' | 'success' | 'danger';
  }>;
  pdf_context?: PdfApplicationContext;
  pdf_totals?: {
    documents: number;
    pages: number;
    words: number;
    tickets: number;
    versions: number;
    dates: number;
  };
  pdf_themes?: Array<{ theme: string; count: number; examples?: string[] }>;
  pdf_recommendations?: string[];
  pdf_actions?: string[];
  pdf_highlights?: Array<{
    id: number;
    filename: string;
    scope_type: string;
    scope_label: string | null;
    summary: string | null;
    themes: Array<{ theme: string; count: number; examples: string[] }>;
    sections?: Array<{ section: string; count: number; snippets?: string[] }>;
  }>;
  pdf_predictions?: Array<{
    type: string;
    title: string;
    detail: string;
    confidence: number;
    action: string;
  }>;
  pdf_problem_solution_examples?: Array<{
    filename?: string;
    problem?: string;
    solution?: string;
  }>;
  top_module?: {
    module: string;
    releases: number;
    corrections: number;
    improvements: number;
    tickets: number;
    latest_version: string;
    latest_release: string;
    share: number;
  } | null;
  top_release?: {
    id: number;
    module: string;
    release_name: string;
    version: string;
    applies_on: string | null;
    tickets: number;
    corrections: number;
    improvements: number;
    by_status: Record<string, number>;
    last_activity_at: string | null;
  } | null;
  tickets: Array<{
    ticket: string;
    tipo: string;
    tipo_label: string;
    status?: string;
    title?: string;
    descricao: string;
    resolucao: string;
    module?: string;
    release?: string;
    version?: string;
    release_id?: number | null;
  }>;
}

export interface PdfIntelligenceDocument {
  id: number;
  scope_type: string;
  scope_id: number | null;
  scope_label: string | null;
  analysis_state?: string | null;
  source_document_id?: number | null;
  allocation_method?: string | null;
  allocation_reason?: string | null;
  filename: string;
  pdf_path: string;
  summary_json?: string;
  summary: {
    scope_type: string;
    scope_id: number | null;
    scope_label: string | null;
    filename: string;
    pdf_path: string;
    page_count: number;
    word_count: number;
    character_count: number;
    ticket_count: number;
    version_count: number;
    date_count: number;
    themes: Array<{ theme: string; count: number; examples: string[] }>;
    sections?: Array<{ section: string; count: number; snippets?: string[] }>;
    problem_solution_pairs?: Array<{ problem: string; solution: string }>;
    knowledge_terms?: Array<{ term: string; count: number }>;
    action_items: string[];
    recommendations: string[];
    summary: string;
    extracted_text: string;
    generated_at: string;
    pdf_url?: string;
  };
  created_at: string;
  pdf_url?: string;
}

export interface PdfUploadNotice {
  filename: string;
  status: 'analyzed' | 'already_analyzed' | 'reused' | 'duplicate' | string;
  message: string;
  existing_document_id?: number | null;
  existing_scope_type?: string | null;
  existing_scope_label?: string | null;
  allocation?: {
    scope_type: string | null;
    scope_id: number | null;
    scope_label: string | null;
    allocation_method?: string | null;
    allocation_reason?: string | null;
  };
  summary?: Record<string, any>;
  pdf_url?: string;
}

export interface PdfUploadResponse {
  status: string;
  documents: PdfIntelligenceDocument[];
  skipped_documents: PdfUploadNotice[];
  messages: string[];
}

export interface PdfProcessResponse {
  status: string;
  documents: PdfIntelligenceDocument[];
  skipped_documents: PdfUploadNotice[];
  messages: string[];
  context: PdfApplicationContext;
  audit?: PdfCycleAudit;
}

export interface Summary {
  homologacoes: number;
  customizacoes: number;
  atividades: number;
  releases: number;
  clientes: number;
  modulos: number;
  current_cycle?: {
    label: string | null;
    cycle_number: number | null;
    homologacoes: number;
    customizacoes: number;
    atividades: number;
    releases: number;
  };
  previous_cycle?: {
    label: string | null;
    cycle_number: number | null;
    homologacoes: number;
    customizacoes: number;
    atividades: number;
    releases: number;
  };
  selected_cycle?: {
    label: string | null;
    cycle_number: number | null;
    homologacoes: number;
    customizacoes: number;
    atividades: number;
    releases: number;
    completed_tasks_total?: number;
    completed_tasks_by_owner?: Array<{
      owner: string;
      count: number;
    }>;
  } | null;
  completed_tasks_total?: number;
  completed_tasks_by_owner?: Array<{
    owner: string;
    count: number;
  }>;
  activity_by_owner?: Array<{
    owner: string;
    count: number;
  }>;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  role: 'admin' | 'user' | string;
  provider: 'local' | 'google' | string;
  approval_status: 'approved' | 'pending' | 'blocked' | string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AuthResponse {
  status: string;
  token: string | null;
  user: AuthUser;
  message?: string | null;
  expires_at?: string | null;
}

export interface AuthAuditLog {
  id: number;
  actor_user_id: number | null;
  actor_username: string | null;
  target_user_id: number | null;
  target_username: string | null;
  event_type: string;
  status: string;
  provider: string | null;
  message: string | null;
  details: Record<string, any> | null;
  created_at: string;
}

export interface Playbook {
  id: number;
  title: string;
  origin: 'manual' | 'erro' | 'release' | 'predicao' | string;
  source_type: string | null;
  source_id: number | null;
  source_key: string | null;
  source_label: string | null;
  area: string | null;
  priority_score: number | null;
  priority_level: 'alta' | 'media' | 'baixa' | string;
  status: 'ativo' | 'prestado' | 'revisar' | 'arquivado' | string;
  summary: string | null;
  content_json: {
    title?: string;
    area?: string;
    how_to?: string[];
    metrics?: Record<string, any>;
    examples?: string[];
    best_practices?: string[];
    checklist?: string[];
    source_summary?: string;
  } | null;
  metrics_json: Record<string, any> | null;
  created_at: string;
  updated_at: string | null;
  closed_at: string | null;
}

export interface PlaybookDashboard {
  totals: {
    playbooks: number;
    manual: number;
    errors: number;
    releases: number;
    predictions: number;
  };
  by_origin: Record<string, number>;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  errors_vs_playbooks: Array<{
    erro: string;
    frequencia: number;
    impacto: number;
    playbook_criado: string;
    status: string;
    reducao_percent: number;
    score: number;
    priority_level: string;
  }>;
  effectiveness: {
    reduction_rate: number;
    avg_execution_time: string;
    adoption_rate: string;
    user_rating: string;
    coverage_processos: number;
    coverage_erros: number;
    avg_priority: number;
  };
  ranking: Array<{
    erro: string;
    frequencia: number;
    impacto: number;
    playbook_criado: string;
    status: string;
    reducao_percent: number;
    score: number;
    priority_level: string;
  }>;
  coverage: {
    processos: number;
    erros: number;
    areas_sem_documentacao: string[];
  };
  suggestions: string[];
}

export interface ReportCycle {
  id: number;
  cycle_number: number | null;
  scope_type: string;
  scope_id: number | null;
  scope_label: string | null;
  period_label: string | null;
  status: 'aberto' | 'prestado' | string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface PdfApplicationContext {
  totals: {
    documents: number;
    pages: number;
    words: number;
    tickets: number;
    versions: number;
    dates: number;
  };
  themes: Array<{ theme: string; count: number; examples: string[] }>;
  sections?: Array<{ section: string; count: number; snippets?: string[] }>;
  knowledge_terms?: Array<{ term: string; count: number }>;
  problem_solution_examples?: Array<{ filename?: string; problem?: string; solution?: string }>;
  scopes: Array<{ scope_type: string; count: number }>;
  action_items: string[];
  recommendations: string[];
  predictions: Array<{
    type: string;
    title: string;
    detail: string;
    confidence: number;
    action: string;
  }>;
  highlights: Array<{
    id: number;
    filename: string;
    scope_type: string;
    scope_label: string | null;
    summary: string | null;
    themes: Array<{ theme: string; count: number; examples: string[] }>;
    sections?: Array<{ section: string; count: number; snippets?: string[] }>;
  }>;
  documents: Array<{
    id: number;
    scope_type: string;
    scope_id: number | null;
    scope_label: string | null;
    report_cycle_id?: number | null;
    filename: string;
    pdf_path: string;
    summary_json?: string;
    summary: {
      scope_type: string;
      scope_id: number | null;
      scope_label: string | null;
      filename: string;
      pdf_path: string;
      page_count: number;
      word_count: number;
      character_count: number;
      ticket_count: number;
      version_count: number;
      date_count: number;
      themes: Array<{ theme: string; count: number; examples: string[] }>;
      sections?: Array<{ section: string; count: number; snippets?: string[] }>;
      problem_solution_pairs?: Array<{ problem: string; solution: string }>;
      knowledge_terms?: Array<{ term: string; count: number }>;
      action_items: string[];
      recommendations: string[];
      summary: string;
      extracted_text: string;
      generated_at: string;
      pdf_url?: string;
    };
    created_at: string;
    pdf_url?: string;
  }>;
  total_documents: number;
  all_time_documents: number;
  cycle_documents: number;
  generated_at: string;
  cycle?: ReportCycle | null;
  cycle_id?: number | null;
}

export interface PdfCycleAudit {
  cycle: ReportCycle | null;
  cycle_id: number | null;
  generated_at: string;
  counts: {
    all: number;
    already_read: number;
    new: number;
    changed: number;
    legacy: number;
    pending: number;
  };
  already_read: Array<Record<string, any>>;
  new_documents: Array<Record<string, any>>;
  changed_documents: Array<Record<string, any>>;
  legacy_documents: Array<Record<string, any>>;
  pending_documents: Array<Record<string, any>>;
}
