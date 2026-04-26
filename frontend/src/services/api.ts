import axios from 'axios';
import type {
  AuthAuditLog,
  AuthResponse,
  AuthUser,
  Homologacao,
  Customizacao,
  Atividade,
  ActivityCatalogs,
  Release,
  Cliente,
  Modulo,
  TicketSummary,
  Summary,
  PdfIntelligenceDocument,
  PdfApplicationContext,
  PdfCycleAudit,
  PdfProcessResponse,
  PdfUploadResponse,
  Playbook,
  PlaybookDashboard,
  ReportCycle,
  ConsolidatedIntelligence,
  ApiEnvelope,
  ModuleStats,
} from '../types';

const API_BASE = '/api';
const AUTH_TOKEN_KEY = 'cs360_auth_token';
const AUTH_USER_KEY = 'cs360_auth_user';
const AUTH_EXPIRES_KEY = 'cs360_auth_expires_at';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

function getStoredToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

function getStoredUser() {
  const value = window.localStorage.getItem(AUTH_USER_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as AuthUser;
  } catch {
    return null;
  }
}

function getStoredExpiry() {
  return window.localStorage.getItem(AUTH_EXPIRES_KEY);
}

export function setAuthSession(token: string, user: AuthUser, expiresAt?: string | null) {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  if (expiresAt) {
    window.localStorage.setItem(AUTH_EXPIRES_KEY, expiresAt);
  } else {
    window.localStorage.removeItem(AUTH_EXPIRES_KEY);
  }
}

export function clearAuthSession() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_USER_KEY);
  window.localStorage.removeItem(AUTH_EXPIRES_KEY);
}

export function getAuthUser() {
  return getStoredUser();
}

export function getAuthToken() {
  return getStoredToken();
}

export function getAuthSessionExpiresAt() {
  return getStoredExpiry();
}

export function getAuthSessionRemainingMs() {
  const expiresAt = getStoredExpiry();
  if (!expiresAt) {
    return null;
  }
  const expiry = new Date(expiresAt);
  const remaining = expiry.getTime() - Date.now();
  return Number.isFinite(remaining) ? Math.max(0, remaining) : null;
}

export function isAuthSessionExpired() {
  const remaining = getAuthSessionRemainingMs();
  return remaining !== null && remaining <= 0;
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthSession();
    }
    return Promise.reject(error);
  },
);

// Helper to unwrap standardized envelope responses
function unwrapData<T>(response: { data: ApiEnvelope<T> | T }): T {
  const raw = response.data as Record<string, unknown>;
  if (raw && typeof raw === 'object' && 'status' in raw && 'data' in raw && 'meta' in raw) {
    return (raw as unknown as ApiEnvelope<T>).data;
  }
  return response.data as T;
}

export const authApi = {
  login: (payload: { username: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', payload).then((r) => r.data),
  googleLogin: (payload: { credential: string }) =>
    api.post<AuthResponse>('/auth/google', payload).then((r) => r.data),
  me: () => api.get<AuthUser>('/auth/me').then((r) => r.data),
  users: (status?: string) =>
    api.get<{ users: AuthUser[] }>('/auth/users', { params: status ? { status } : {} }).then((r) => r.data),
  approveUser: (id: number) => api.post<{ status: string; user: AuthUser }>(`/auth/users/${id}/approve`).then((r) => r.data),
  deactivateUser: (id: number) => api.post<{ status: string; user: AuthUser }>(`/auth/users/${id}/deactivate`).then((r) => r.data),
  auditLogs: (limit = 100) => api.get<{ logs: AuthAuditLog[] }>('/auth/audit-logs', { params: { limit } }).then((r) => r.data),
};

// Homologação
export const homologacaoApi = {
  list: () => api.get('/homologacao').then(r => unwrapData<Homologacao[]>(r)),
  get: (id: number) => api.get(`/homologacao/${id}`).then(r => unwrapData<Homologacao>(r)),
  create: (data: Partial<Homologacao>) => api.post('/homologacao', data).then(r => unwrapData<Homologacao>(r)),
  update: (id: number, data: Partial<Homologacao>) => api.put(`/homologacao/${id}`, data).then(r => unwrapData<Homologacao>(r)),
  delete: (id: number) => api.delete(`/homologacao/${id}`),
  stats: () => api.get('/homologacao/stats').then(r => unwrapData<ModuleStats>(r)),
};

// Customização
export const customizacaoApi = {
  list: () => api.get('/customizacao').then(r => unwrapData<Customizacao[]>(r)),
  get: (id: number) => api.get(`/customizacao/${id}`).then(r => unwrapData<Customizacao>(r)),
  create: (data: Partial<Customizacao>) => api.post('/customizacao', data).then(r => unwrapData<Customizacao>(r)),
  update: (id: number, data: Partial<Customizacao>) => api.put(`/customizacao/${id}`, data).then(r => unwrapData<Customizacao>(r)),
  delete: (id: number) => api.delete(`/customizacao/${id}`),
  stats: () => api.get('/customizacao/stats').then(r => unwrapData<ModuleStats>(r)),
};

// Atividade
export const atividadeApi = {
  list: (releaseId?: number) => api.get('/atividade', { params: releaseId ? { release_id: releaseId } : {} }).then(r => unwrapData<Atividade[]>(r)),
  get: (id: number) => api.get(`/atividade/${id}`).then(r => unwrapData<Atividade>(r)),
  create: (data: Partial<Atividade>) => api.post('/atividade', data).then(r => unwrapData<Atividade>(r)),
  update: (id: number, data: Partial<Atividade>) => api.put(`/atividade/${id}`, data).then(r => unwrapData<Atividade>(r)),
  updateStatus: (id: number, status: Atividade['status']) => api.patch(`/atividade/${id}/status`, null, { params: { status } }).then(r => unwrapData<Atividade>(r)),
  delete: (id: number) => api.delete(`/atividade/${id}`),
  catalogs: () => api.get('/atividade/catalogos').then(r => unwrapData<ActivityCatalogs>(r)),
  createOwner: (payload: { name: string; sort_order?: number }) => api.post('/atividade/catalogos/owners', payload).then(r => unwrapData<Record<string, unknown>>(r)),
  updateOwner: (id: number, payload: { name?: string; sort_order?: number; is_active?: number }) => api.put(`/atividade/catalogos/owners/${id}`, payload).then(r => unwrapData<Record<string, unknown>>(r)),
  deleteOwner: (id: number) => api.delete(`/atividade/catalogos/owners/${id}`),
  createStatus: (payload: { key: string; label: string; hint?: string; sort_order?: number }) => api.post('/atividade/catalogos/statuses', payload).then(r => unwrapData<Record<string, unknown>>(r)),
  updateStatusCatalog: (id: number, payload: { key?: string; label?: string; hint?: string; sort_order?: number; is_active?: number }) => api.put(`/atividade/catalogos/statuses/${id}`, payload).then(r => unwrapData<Record<string, unknown>>(r)),
  deleteStatus: (id: number) => api.delete(`/atividade/catalogos/statuses/${id}`),
  stats: () => api.get('/atividade/stats').then(r => unwrapData<ModuleStats>(r)),
};

// Release
export const releaseApi = {
  list: () => api.get('/release').then(r => unwrapData<Release[]>(r)),
  get: (id: number) => api.get(`/release/${id}`).then(r => unwrapData<Release>(r)),
  create: (data: Partial<Release>) => api.post('/release', data).then(r => unwrapData<Release>(r)),
  update: (id: number, data: Partial<Release>) => api.put(`/release/${id}`, data).then(r => unwrapData<Release>(r)),
  delete: (id: number) => api.delete(`/release/${id}`),
  uploadPdf: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/release/${id}/upload-pdf`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => unwrapData<Record<string, unknown>>(r));
  },
  stats: () => api.get('/release/stats').then(r => unwrapData<ModuleStats>(r)),
};

// PDF Intelligence
export const pdfIntelligenceApi = {
  list: (scopeType?: string, scopeId?: number) => api.get<PdfIntelligenceDocument[]>('/pdf-intelligence', {
    params: {
      ...(scopeType && { scope_type: scopeType }),
      ...(scopeId !== undefined && { scope_id: scopeId }),
    },
  }).then(r => r.data),
  stage: (scopeType: string, files: File[], scopeId?: number | null, scopeLabel?: string | null) => {
    const formData = new FormData();
    formData.append('scope_type', scopeType);
    if (scopeId !== undefined && scopeId !== null) {
      formData.append('scope_id', String(scopeId));
    }
    if (scopeLabel) {
      formData.append('scope_label', scopeLabel);
    }
    files.forEach((file) => formData.append('files', file));
    return api.post<PdfUploadResponse>('/pdf-intelligence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  upload: (scopeType: string, files: File[], scopeId?: number | null, scopeLabel?: string | null) =>
    pdfIntelligenceApi.stage(scopeType, files, scopeId, scopeLabel),
  process: (payload: { documentIds?: number[]; scopeType?: string | null; scopeId?: number | null; scopeLabel?: string | null }) =>
    api.post<PdfProcessResponse>('/pdf-intelligence/process', {
      document_ids: payload.documentIds ?? [],
      scope_type: payload.scopeType ?? null,
      scope_id: payload.scopeId ?? null,
      scope_label: payload.scopeLabel ?? null,
    }).then((r) => r.data),
  get: (id: number) => api.get<PdfIntelligenceDocument>(`/pdf-intelligence/${id}`).then(r => r.data),
  html: (id: number) => api.get<{ html: string }>(`/pdf-intelligence/${id}/html`).then(r => r.data),
  pdf: (id: number) => api.get(`/pdf-intelligence/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  applicationContext: () => api.get<PdfApplicationContext>('/pdf-intelligence/application-context').then(r => r.data),
  cycleAudit: () => api.get<PdfCycleAudit>('/pdf-intelligence/cycle-audit').then(r => r.data),
};

// Cliente
export const clienteApi = {
  list: () => api.get('/cliente').then(r => unwrapData<Cliente[]>(r)),
  get: (id: number) => api.get(`/cliente/${id}`).then(r => unwrapData<Cliente>(r)),
  create: (data: Partial<Cliente>) => api.post('/cliente', data).then(r => unwrapData<Cliente>(r)),
  update: (id: number, data: Partial<Cliente>) => api.put(`/cliente/${id}`, data).then(r => unwrapData<Cliente>(r)),
  delete: (id: number) => api.delete(`/cliente/${id}`),
  stats: () => api.get('/cliente/stats').then(r => unwrapData<ModuleStats>(r)),
};

// Módulo
export const moduloApi = {
  list: () => api.get('/modulo').then(r => unwrapData<Modulo[]>(r)),
  get: (id: number) => api.get(`/modulo/${id}`).then(r => unwrapData<Modulo>(r)),
  create: (data: Partial<Modulo>) => api.post('/modulo', data).then(r => unwrapData<Modulo>(r)),
  update: (id: number, data: Partial<Modulo>) => api.put(`/modulo/${id}`, data).then(r => unwrapData<Modulo>(r)),
  delete: (id: number) => api.delete(`/modulo/${id}`),
  stats: () => api.get('/modulo/stats').then(r => unwrapData<ModuleStats>(r)),
};

// Reports — Intelligence Hub
export const reportsApi = {
  intelligence: (releaseId?: number, cycleId?: number) =>
    api.get('/reports/intelligence', {
      params: {
        ...(releaseId && { release_id: releaseId }),
        ...(cycleId && { cycle_id: cycleId }),
      },
    }).then(r => unwrapData<ConsolidatedIntelligence>(r)),
  ticketSummary: (releaseId?: number, cycleId?: number, focus?: { type?: string; value?: string; label?: string }) => api.get<TicketSummary>('/reports/ticket-summary', {
    params: {
      ...(releaseId && { release_id: releaseId }),
      ...(cycleId && { cycle_id: cycleId }),
      ...(focus?.type && { focus_type: focus.type }),
      ...(focus?.value && { focus_value: focus.value }),
      ...(focus?.label && { focus_label: focus.label }),
    },
  }).then(r => r.data),
  htmlReport: (releaseId?: number, releaseName?: string, cycleId?: number, focus?: { type?: string; value?: string; label?: string }) => api.get<{ html: string }>('/reports/html', {
    params: {
      ...(releaseId && { release_id: releaseId }),
      ...(releaseName && { release_name: releaseName }),
      ...(cycleId && { cycle_id: cycleId }),
      ...(focus?.type && { focus_type: focus.type }),
      ...(focus?.value && { focus_value: focus.value }),
      ...(focus?.label && { focus_label: focus.label }),
    },
  }).then(r => r.data),
  summaryText: (releaseId?: number, cycleId?: number, focus?: { type?: string; value?: string; label?: string }) => api.get<{ report: string }>('/reports/summary-text', {
    params: {
      ...(releaseId && { release_id: releaseId }),
      ...(cycleId && { cycle_id: cycleId }),
      ...(focus?.type && { focus_type: focus.type }),
      ...(focus?.value && { focus_value: focus.value }),
      ...(focus?.label && { focus_label: focus.label }),
    },
  }).then(r => r.data),
  pdfReport: (releaseId?: number, releaseName?: string, cycleId?: number, focus?: { type?: string; value?: string; label?: string }) => api.get('/reports/pdf', {
    params: {
      ...(releaseId && { release_id: releaseId }),
      ...(releaseName && { release_name: releaseName }),
      ...(cycleId && { cycle_id: cycleId }),
      ...(focus?.type && { focus_type: focus.type }),
      ...(focus?.value && { focus_value: focus.value }),
      ...(focus?.label && { focus_label: focus.label }),
    },
    responseType: 'blob',
  }).then(r => r.data),
  cycles: (releaseId?: number) => api.get<ReportCycle[]>('/reports/cycles', {
    params: releaseId ? { release_id: releaseId } : {},
  }).then(r => r.data),
  cycle: (releaseId?: number) => api.get<{ cycle: ReportCycle | null }>('/playbooks/cycle', {
    params: releaseId ? { release_id: releaseId } : {},
  }).then(r => r.data),
  closeCycle: (payload: { releaseId?: number; notes?: string; reopenNew?: boolean; scopeLabel?: string; closedPeriodLabel?: string; nextPeriodLabel?: string }) =>
    api.post<{ status: string; closed_cycle: ReportCycle | null; opened_new: boolean; new_cycle: ReportCycle | null }>('/playbooks/cycle/close', {
      scope_type: 'reports',
      scope_id: payload.releaseId ?? null,
      notes: payload.notes ?? null,
      reopen_new: payload.reopenNew ?? false,
      scope_label: payload.scopeLabel ?? null,
      closed_period_label: payload.closedPeriodLabel ?? null,
      next_period_label: payload.nextPeriodLabel ?? null,
    }).then(r => r.data),
  openCycle: (payload: { releaseId?: number; scopeLabel?: string; periodLabel?: string }) =>
    api.post<{ status: string; cycle: ReportCycle | null; id: number }>('/playbooks/cycle/open', {
      scope_type: 'reports',
      scope_id: payload.releaseId ?? null,
      scope_label: payload.scopeLabel ?? null,
      period_label: payload.periodLabel ?? null,
    }).then(r => r.data),
};

// Playbooks
export const playbooksApi = {
  list: (cycleId?: number) => api.get<Playbook[]>('/playbooks', { params: cycleId ? { cycle_id: cycleId } : {} }).then(r => r.data),
  dashboard: (cycleId?: number) => api.get<PlaybookDashboard>('/playbooks/dashboard', { params: cycleId ? { cycle_id: cycleId } : {} }).then(r => r.data),
  suggestions: (cycleId?: number) => api.get<{ suggestions: string[]; coverage: PlaybookDashboard['coverage'] }>('/playbooks/suggestions', { params: cycleId ? { cycle_id: cycleId } : {} }).then(r => r.data),
  createManual: (data: { title: string; area: string; objective?: string; audience?: string; notes?: string }) =>
    api.post<Playbook>('/playbooks/manual', data).then(r => r.data),
  generateErrors: (limit = 5) => api.post<{ status: string; playbooks: Playbook[] }>(`/playbooks/generate/errors?limit=${limit}`, {}).then(r => r.data),
  generateRelease: (releaseId: number) => api.post<{ status: string; playbooks: Playbook[] }>(`/playbooks/generate/release/${releaseId}`, {}).then(r => r.data),
  generatePredictions: () => api.post<{ status: string; playbooks: Playbook[]; predictions: Array<{ type: string; title: string; detail: string; confidence: number; action: string }> }>('/playbooks/generate/predictions', {}).then(r => r.data),
  update: (id: number, data: Partial<Playbook>) => api.put<Playbook>(`/playbooks/${id}`, data).then(r => r.data),
  updateStatus: (id: number, status: Playbook['status']) => api.patch<Playbook>(`/playbooks/${id}/status`, { status }).then(r => r.data),
  delete: (id: number) => api.delete(`/playbooks/${id}`),
  html: (id: number) => api.get<{ html: string }>(`/playbooks/${id}/html`).then(r => r.data),
  pdf: (id: number) => api.get(`/playbooks/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
};

// Summary
export const summaryApi = {
  get: (cycleId?: number) => api.get<Summary>('/summary', { params: cycleId ? { cycle_id: cycleId } : {} }).then(r => r.data),
};

export default api;
