-- CS Controle 360 - Schema SQL para Supabase
-- Este script cria todas as tabelas necessárias para o sistema

-- Tabela de Módulos
CREATE TABLE IF NOT EXISTS modules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  owner TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Clientes
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  segment TEXT,
  owner TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Releases
CREATE TABLE IF NOT EXISTS releases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  module TEXT,
  release_name TEXT NOT NULL,
  version TEXT NOT NULL,
  applies_on DATE,
  notes TEXT,
  client TEXT,
  client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
  pdf_path TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Homologações
CREATE TABLE IF NOT EXISTS homologations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  module TEXT,
  status TEXT DEFAULT 'Em Andamento',
  check_date DATE,
  observation TEXT,
  latest_version TEXT,
  homologation_version TEXT,
  production_version TEXT,
  homologated TEXT DEFAULT 'Não',
  client_presentation TEXT,
  applied TEXT DEFAULT 'Pendente',
  monthly_versions JSONB,
  requested_production_date DATE,
  production_date DATE,
  client TEXT,
  client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Customizações
CREATE TABLE IF NOT EXISTS customizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stage TEXT DEFAULT 'em_elaboracao',
  proposal TEXT NOT NULL,
  subject TEXT NOT NULL,
  client TEXT,
  client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
  module TEXT,
  module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  owner TEXT,
  received_at DATE,
  status TEXT,
  pf INTEGER,
  value DECIMAL(10,2),
  observations TEXT,
  pdf_path TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Atividades
CREATE TABLE IF NOT EXISTS activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  release_id UUID REFERENCES releases(id) ON DELETE SET NULL,
  owner TEXT,
  executor TEXT,
  tipo TEXT DEFAULT 'melhoria' CHECK (tipo IN ('nova_funcionalidade', 'correcao_bug', 'melhoria')),
  ticket TEXT,
  descricao_erro TEXT,
  resolucao TEXT,
  status TEXT DEFAULT 'backlog' CHECK (status IN ('backlog', 'em_andamento', 'em_revisao', 'concluida', 'bloqueada')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Catálogo de Responsáveis de Atividades
CREATE TABLE IF NOT EXISTS activity_owners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Catálogo de Status de Atividades
CREATE TABLE IF NOT EXISTS activity_statuses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  hint TEXT,
  sort_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Playbooks
CREATE TABLE IF NOT EXISTS playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  origin TEXT DEFAULT 'manual' CHECK (origin IN ('manual', 'erro', 'release', 'predicao')),
  source_type TEXT,
  source_id UUID,
  source_key TEXT,
  source_label TEXT,
  area TEXT,
  priority_score INTEGER,
  priority_level TEXT DEFAULT 'media' CHECK (priority_level IN ('alta', 'media', 'baixa')),
  status TEXT DEFAULT 'ativo' CHECK (status IN ('ativo', 'prestado', 'revisar', 'arquivado')),
  summary TEXT,
  content_json JSONB,
  metrics_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);

-- Tabela de Ciclos de Relatório
CREATE TABLE IF NOT EXISTS report_cycles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_number INTEGER,
  scope_type TEXT,
  scope_id UUID,
  scope_label TEXT,
  period_label TEXT,
  status TEXT DEFAULT 'aberto' CHECK (status IN ('aberto', 'prestado')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);

-- Tabela de Documentos PDF (Inteligência)
CREATE TABLE IF NOT EXISTS pdf_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_type TEXT,
  scope_id UUID,
  scope_label TEXT,
  analysis_state TEXT,
  source_document_id UUID,
  allocation_method TEXT,
  allocation_reason TEXT,
  filename TEXT NOT NULL,
  pdf_path TEXT NOT NULL,
  summary_json JSONB,
  report_cycle_id UUID REFERENCES report_cycles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Perfis de Usuário (vinculada ao auth.users do Supabase)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE,
  full_name TEXT,
  role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  approval_status TEXT DEFAULT 'pending' CHECK (approval_status IN ('approved', 'pending', 'blocked')),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de Log de Auditoria de Auth
CREATE TABLE IF NOT EXISTS auth_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  actor_username TEXT,
  target_user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  target_username TEXT,
  event_type TEXT NOT NULL,
  status TEXT,
  provider TEXT,
  message TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE homologations ENABLE ROW LEVEL SECURITY;
ALTER TABLE customizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_cycles ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdf_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_logs ENABLE ROW LEVEL SECURITY;

-- Políticas RLS: Permitir leitura para usuários autenticados
CREATE POLICY "Authenticated users can read modules" ON modules FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read clients" ON clients FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read releases" ON releases FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read homologations" ON homologations FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read customizations" ON customizations FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read activities" ON activities FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read activity_owners" ON activity_owners FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read activity_statuses" ON activity_statuses FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read playbooks" ON playbooks FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read report_cycles" ON report_cycles FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read pdf_documents" ON pdf_documents FOR SELECT TO authenticated USING (true);
CREATE POLICY "Users can read own profile" ON profiles FOR SELECT TO authenticated USING (auth.uid() = id);

-- Políticas RLS: Permitir escrita para usuários autenticados
CREATE POLICY "Authenticated users can insert modules" ON modules FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update modules" ON modules FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete modules" ON modules FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert clients" ON clients FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update clients" ON clients FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete clients" ON clients FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert releases" ON releases FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update releases" ON releases FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete releases" ON releases FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert homologations" ON homologations FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update homologations" ON homologations FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete homologations" ON homologations FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert customizations" ON customizations FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update customizations" ON customizations FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete customizations" ON customizations FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert activities" ON activities FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update activities" ON activities FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete activities" ON activities FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert activity_owners" ON activity_owners FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update activity_owners" ON activity_owners FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert activity_statuses" ON activity_statuses FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update activity_statuses" ON activity_statuses FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert playbooks" ON playbooks FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update playbooks" ON playbooks FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can delete playbooks" ON playbooks FOR DELETE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert report_cycles" ON report_cycles FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update report_cycles" ON report_cycles FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert pdf_documents" ON pdf_documents FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update pdf_documents" ON pdf_documents FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);

-- Trigger para criar perfil automaticamente ao criar usuário
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, username, full_name, role, approval_status)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data ->> 'username', NEW.email),
    COALESCE(NEW.raw_user_meta_data ->> 'full_name', NULL),
    'user',
    'approved'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_activities_release_id ON activities(release_id);
CREATE INDEX IF NOT EXISTS idx_activities_status ON activities(status);
CREATE INDEX IF NOT EXISTS idx_homologations_module_id ON homologations(module_id);
CREATE INDEX IF NOT EXISTS idx_customizations_client_id ON customizations(client_id);
CREATE INDEX IF NOT EXISTS idx_releases_module_id ON releases(module_id);
CREATE INDEX IF NOT EXISTS idx_pdf_documents_scope ON pdf_documents(scope_type, scope_id);
