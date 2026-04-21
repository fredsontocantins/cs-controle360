import axios from 'axios';
import type {
  Homologacao,
  Customizacao,
  Atividade,
  Release,
  Cliente,
  Modulo,
  TicketSummary,
  Summary,
  PdfIntelligenceDocument,
  PdfApplicationContext,
  PdfCycleAudit,
  Playbook,
  PlaybookDashboard,
  ReportCycle,
} from '../types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Homologação
export const homologacaoApi = {
  list: () => api.get<Homologacao[]>('/homologacao').then(r => r.data),
  get: (id: number) => api.get<Homologacao>(`/homologacao/${id}`).then(r => r.data),
  create: (data: Partial<Homologacao>) => api.post<Homologacao>('/homologacao', data).then(r => r.data),
  update: (id: number, data: Partial<Homologacao>) => api.put<Homologacao>(`/homologacao/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/homologacao/${id}`),
};

// Customização
export const customizacaoApi = {
  list: () => api.get<Customizacao[]>('/customizacao').then(r => r.data),
  get: (id: number) => api.get<Customizacao>(`/customizacao/${id}`).then(r => r.data),
  create: (data: Partial<Customizacao>) => api.post<Customizacao>('/customizacao', data).then(r => r.data),
  update: (id: number, data: Partial<Customizacao>) => api.put<Customizacao>(`/customizacao/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/customizacao/${id}`),
};

// Atividade
export const atividadeApi = {
  list: (releaseId?: number) => api.get<Atividade[]>('/atividade', { params: releaseId ? { release_id: releaseId } : {} }).then(r => r.data),
  get: (id: number) => api.get<Atividade>(`/atividade/${id}`).then(r => r.data),
  create: (data: Partial<Atividade>) => api.post<Atividade>('/atividade', data).then(r => r.data),
  update: (id: number, data: Partial<Atividade>) => api.put<Atividade>(`/atividade/${id}`, data).then(r => r.data),
  updateStatus: (id: number, status: Atividade['status']) => api.patch<Atividade>(`/atividade/${id}/status`, null, { params: { status } }).then(r => r.data),
  delete: (id: number) => api.delete(`/atividade/${id}`),
};

// Release
export const releaseApi = {
  list: () => api.get<Release[]>('/release').then(r => r.data),
  get: (id: number) => api.get<Release>(`/release/${id}`).then(r => r.data),
  create: (data: Partial<Release>) => api.post<Release>('/release', data).then(r => r.data),
  update: (id: number, data: Partial<Release>) => api.put<Release>(`/release/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/release/${id}`),
  uploadPdf: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/release/${id}/upload-pdf`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};

// PDF Intelligence
export const pdfIntelligenceApi = {
  list: (scopeType?: string, scopeId?: number) => api.get<PdfIntelligenceDocument[]>('/pdf-intelligence', {
    params: {
      ...(scopeType && { scope_type: scopeType }),
      ...(scopeId !== undefined && { scope_id: scopeId }),
    },
  }).then(r => r.data),
  upload: (scopeType: string, files: File[], scopeId?: number | null, scopeLabel?: string | null) => {
    const formData = new FormData();
    formData.append('scope_type', scopeType);
    if (scopeId !== undefined && scopeId !== null) {
      formData.append('scope_id', String(scopeId));
    }
    if (scopeLabel) {
      formData.append('scope_label', scopeLabel);
    }
    files.forEach((file) => formData.append('files', file));
    return api.post<{ status: string; documents: PdfIntelligenceDocument[] }>('/pdf-intelligence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  get: (id: number) => api.get<PdfIntelligenceDocument>(`/pdf-intelligence/${id}`).then(r => r.data),
  html: (id: number) => api.get<{ html: string }>(`/pdf-intelligence/${id}/html`).then(r => r.data),
  pdf: (id: number) => api.get(`/pdf-intelligence/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),
  applicationContext: () => api.get<PdfApplicationContext>('/pdf-intelligence/application-context').then(r => r.data),
  cycleAudit: () => api.get<PdfCycleAudit>('/pdf-intelligence/cycle-audit').then(r => r.data),
};

// Cliente
export const clienteApi = {
  list: () => api.get<Cliente[]>('/cliente').then(r => r.data),
  get: (id: number) => api.get<Cliente>(`/cliente/${id}`).then(r => r.data),
  create: (data: Partial<Cliente>) => api.post<Cliente>('/cliente', data).then(r => r.data),
  update: (id: number, data: Partial<Cliente>) => api.put<Cliente>(`/cliente/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/cliente/${id}`),
};

// Módulo
export const moduloApi = {
  list: () => api.get<Modulo[]>('/modulo').then(r => r.data),
  get: (id: number) => api.get<Modulo>(`/modulo/${id}`).then(r => r.data),
  create: (data: Partial<Modulo>) => api.post<Modulo>('/modulo', data).then(r => r.data),
  update: (id: number, data: Partial<Modulo>) => api.put<Modulo>(`/modulo/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/modulo/${id}`),
};

// Reports
export const reportsApi = {
  ticketSummary: (releaseId?: number) => api.get<TicketSummary>('/reports/ticket-summary', {
    params: releaseId ? { release_id: releaseId } : {},
  }).then(r => r.data),
  htmlReport: (releaseId?: number, releaseName?: string) => api.get<{ html: string }>('/reports/html', {
    params: { ...(releaseId && { release_id: releaseId }), ...(releaseName && { release_name: releaseName }) },
  }).then(r => r.data),
  summaryText: (releaseId?: number) => api.get<{ report: string }>('/reports/summary-text', {
    params: releaseId ? { release_id: releaseId } : {},
  }).then(r => r.data),
  pdfReport: (releaseId?: number, releaseName?: string) => api.get('/reports/pdf', {
    params: { ...(releaseId && { release_id: releaseId }), ...(releaseName && { release_name: releaseName }) },
    responseType: 'blob',
  }).then(r => r.data),
  cycle: (releaseId?: number) => api.get<{ cycle: ReportCycle | null }>('/playbooks/cycle', {
    params: releaseId ? { release_id: releaseId } : {},
  }).then(r => r.data),
  closeCycle: (payload: { releaseId?: number; notes?: string; reopenNew?: boolean; scopeLabel?: string; periodLabel?: string }) =>
    api.post<{ status: string; closed_cycle: ReportCycle | null; opened_new: boolean; new_cycle: ReportCycle | null }>('/playbooks/cycle/close', {
      scope_type: 'reports',
      scope_id: payload.releaseId ?? null,
      notes: payload.notes ?? null,
      reopen_new: payload.reopenNew ?? false,
      scope_label: payload.scopeLabel ?? null,
      period_label: payload.periodLabel ?? null,
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
  list: () => api.get<Playbook[]>('/playbooks').then(r => r.data),
  dashboard: () => api.get<PlaybookDashboard>('/playbooks/dashboard').then(r => r.data),
  suggestions: () => api.get<{ suggestions: string[]; coverage: PlaybookDashboard['coverage'] }>('/playbooks/suggestions').then(r => r.data),
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
  get: () => api.get<Summary>('/summary').then(r => r.data),
};

export default api;
