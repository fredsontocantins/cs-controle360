import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge, Button, Card, Select } from './';
import type { PdfIntelligenceDocument } from '../types';

interface RecordOption {
  id: number;
  label: string;
}

interface PdfIntelligencePanelProps {
  scopeType: string;
  scopeLabel: string;
  scopeId?: number | null;
  recordOptions?: RecordOption[];
}

export function PdfIntelligencePanel({
  scopeType,
  scopeLabel,
  scopeId = null,
  recordOptions = [],
}: PdfIntelligencePanelProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [preview, setPreview] = useState<PdfIntelligenceDocument | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(scopeId);

  useEffect(() => {
    if (scopeId !== null && scopeId !== undefined) {
      setSelectedRecordId(scopeId);
    }
  }, [scopeId, scopeType]);

  const activeScopeId = recordOptions.length > 0 ? selectedRecordId : scopeId;
  const activeScopeLabel = useMemo(() => {
    if (recordOptions.length > 0 && activeScopeId !== null) {
      return recordOptions.find((option) => option.id === activeScopeId)?.label || scopeLabel;
    }
    return scopeLabel;
  }, [activeScopeId, recordOptions, scopeLabel]);

  useEffect(() => {
    setSelectedId(null);
    setPreview(null);
  }, [activeScopeId]);

  const scopeKey = useMemo(() => [scopeType, activeScopeId ?? 'global'], [scopeType, activeScopeId]);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['pdf-intelligence', ...scopeKey],
    queryFn: () => pdfIntelligenceApi.list(scopeType, activeScopeId ?? undefined),
  });

  const { data: applicationContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });

  const globalDocuments = applicationContext?.documents ?? [];
  const combinedDocuments = useMemo(() => {
    const byId = new Map<number, PdfIntelligenceDocument>();
    [...globalDocuments, ...documents].forEach((doc) => {
      byId.set(doc.id, doc);
    });
    return [...byId.values()].sort((left, right) => {
      const leftTime = new Date(left.created_at).getTime();
      const rightTime = new Date(right.created_at).getTime();
      return rightTime - leftTime;
    });
  }, [documents, globalDocuments]);

  const selectedDocument = useMemo(() => {
    if (preview) return preview;
    if (selectedId) return combinedDocuments.find((doc) => doc.id === selectedId) ?? null;
    return combinedDocuments[0] ?? null;
  }, [combinedDocuments, preview, selectedId]);

  const handleDownloadPdf = async (documentId: number) => {
    const blob = await pdfIntelligenceApi.pdf(documentId);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `inteligencia-${scopeType}-${documentId}.pdf`;
    anchor.click();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
  };

  const handleViewHtml = async (documentId: number) => {
    const result = await pdfIntelligenceApi.html(documentId);
    const blob = new Blob([result.html], { type: 'text/html;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
  };

  const handleDownloadText = async (documentId: number) => {
    const targetDocument = combinedDocuments.find((doc) => doc.id === documentId);
    if (!targetDocument) {
      return;
    }
    const lines = [
      'CS CONTROLE 360 - Inteligência de PDF',
      `Arquivo: ${targetDocument.filename}`,
      `Escopo: ${targetDocument.scope_label || scopeLabel}`,
      `Status: ${targetDocument.analysis_state || 'pending'}`,
      `Resumo: ${targetDocument.summary?.summary || 'Sem resumo disponível.'}`,
      '',
      'Temas',
      ...(targetDocument.summary?.themes ?? []).map((theme) => `- ${theme.theme} (${theme.count})`),
      '',
      'Seções',
      ...(targetDocument.summary?.sections ?? []).map((section) => `- ${section.section} (${section.count})`),
      '',
      'Ações',
      ...(targetDocument.summary?.action_items ?? []).map((item) => `- ${item}`),
      '',
      'Recomendações',
      ...(targetDocument.summary?.recommendations ?? []).map((item) => `- ${item}`),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const anchor = window.document.createElement('a');
    anchor.href = url;
    anchor.download = `inteligencia-${scopeType}-${documentId}.txt`;
    anchor.click();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
  };

  return (
    <Card className="border border-dashed border-[#0d3b66]/20 bg-white/95">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2">
            <Badge variant="info">PDF Inteligente</Badge>
            <Badge variant="warning">{activeScopeLabel}</Badge>
          </div>
          <h2 className="mt-3 text-xl font-semibold text-gray-900">Inteligência consolidada dos PDFs</h2>
          <p className="mt-2 text-sm text-gray-600">
            Use o bloco de processamento no menu Relatórios para consolidar os PDFs pendentes e consulte aqui o resultado da inteligência gerada.
          </p>
          <p className="mt-2 text-xs uppercase tracking-wider text-gray-500">
            Contexto atual: {activeScopeLabel}{activeScopeId !== null ? ` #${activeScopeId}` : ''}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="info">Base global: {globalDocuments.length}</Badge>
            <Badge variant="warning">Contexto da tela: {documents.length}</Badge>
            <Badge variant="success">Total visível: {combinedDocuments.length}</Badge>
          </div>
        </div>

        {recordOptions.length > 0 && (
          <div className="min-w-[240px]">
            <Select
              label="Vincular ao registro"
              options={[
                { value: '', label: 'Selecione...' },
                ...recordOptions.map((option) => ({ value: String(option.id), label: option.label })),
              ]}
              value={selectedRecordId !== null ? String(selectedRecordId) : ''}
              onChange={(e) => {
                const value = e.target.value;
                setSelectedRecordId(value ? Number(value) : null);
                setSelectedId(null);
                setPreview(null);
              }}
            />
          </div>
        )}
      </div>

      <div className="mt-4 rounded-2xl border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-gray-900">Inteligência global do ciclo</p>
            <p className="text-xs text-gray-500">
              {applicationContext?.cycle?.period_label || 'Ciclo atual'} | {applicationContext?.cycle_documents ?? applicationContext?.total_documents ?? 0} documento(s) no ciclo | {applicationContext?.all_time_documents ?? applicationContext?.total_documents ?? 0} no histórico
            </p>
          </div>
          <Badge variant={applicationContext?.cycle?.status === 'prestado' ? 'warning' : 'success'}>
            {applicationContext?.cycle?.status || 'aberto'}
          </Badge>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
          {(applicationContext?.predictions ?? []).slice(0, 2).map((item) => (
            <div key={item.title} className="rounded-xl border border-gray-200 bg-white p-3">
              <p className="text-sm font-medium text-gray-900">{item.title}</p>
              <p className="mt-1 text-xs text-gray-500">{item.detail}</p>
            </div>
          ))}
          {(applicationContext?.predictions ?? []).length === 0 && (
            <p className="text-sm text-gray-500">Sem previsões calculadas ainda.</p>
          )}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div>
            <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Seções</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {(applicationContext?.sections ?? []).slice(0, 8).map((section) => (
                <Badge key={section.section} variant="warning">
                  {section.section} ({section.count})
                </Badge>
              ))}
              {(applicationContext?.sections ?? []).length === 0 && <span className="text-sm text-gray-500">Sem seções.</span>}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Termos</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {(applicationContext?.knowledge_terms ?? []).slice(0, 10).map((term) => (
                <Badge key={term.term} variant="success">
                  {term.term} ({term.count})
                </Badge>
              ))}
              {(applicationContext?.knowledge_terms ?? []).length === 0 && <span className="text-sm text-gray-500">Sem termos.</span>}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Problema / Solução</h4>
            <div className="mt-3 space-y-2">
              {(applicationContext?.problem_solution_examples ?? []).slice(0, 3).map((item, index) => (
                <div key={`${item.filename || 'doc'}-${index}`} className="rounded-xl border border-gray-200 bg-white p-3">
                  <p className="text-sm font-medium text-gray-900">{item.filename || 'PDF'}</p>
                  <p className="mt-1 text-xs text-gray-500">{item.problem || 'Problema não identificado'}</p>
                  <p className="mt-1 text-xs text-gray-700">{item.solution || 'Solução não identificada'}</p>
                </div>
              ))}
              {(applicationContext?.problem_solution_examples ?? []).length === 0 && (
                <span className="text-sm text-gray-500">Sem pares problema/solução.</span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-1">
          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Documentos analisados</h3>
              <Badge variant="info">{documents.length}</Badge>
            </div>
            <div className="mt-4 space-y-3">
              {isLoading ? (
                <p className="text-sm text-gray-500">Carregando documentos...</p>
              ) : combinedDocuments.length > 0 ? (
                combinedDocuments.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => {
                      setSelectedId(doc.id);
                      setPreview(doc);
                    }}
                    className={`w-full rounded-2xl border p-3 text-left transition ${
                      selectedDocument?.id === doc.id
                        ? 'border-[#0d3b66] bg-white shadow-sm'
                        : 'border-gray-200 bg-white hover:border-[#0d3b66]/30'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-900 line-clamp-1">{doc.filename}</p>
                        <p className="text-xs text-gray-500">{doc.scope_label || scopeLabel}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge variant="warning">{doc.summary?.ticket_count ?? 0} tickets</Badge>
                        <Badge variant={doc.scope_type === 'global' ? 'info' : 'default'}>
                          {doc.scope_type === 'global' ? 'global' : doc.scope_type}
                        </Badge>
                        {doc.analysis_state && (
                          <Badge variant={doc.analysis_state === 'analyzed' ? 'success' : 'info'}>
                            {doc.analysis_state}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <p className="text-sm text-gray-500">Nenhum PDF processado ainda.</p>
              )}
            </div>
          </div>
        </div>

        <div className="xl:col-span-2">
          {selectedDocument ? (
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wider text-gray-500">{selectedDocument.scope_label || scopeLabel}</p>
                  <h3 className="text-xl font-semibold text-gray-900">{selectedDocument.filename}</h3>
                  <p className="mt-1 text-sm text-gray-600">{selectedDocument.summary?.summary}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => handleDownloadText(selectedDocument.id)}>
                    Ver texto
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => handleViewHtml(selectedDocument.id)}>
                    Ver HTML
                  </Button>
                  <Button type="button" size="sm" variant="secondary" onClick={() => handleDownloadPdf(selectedDocument.id)}>
                    Exportar PDF
                  </Button>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric label="Páginas" value={selectedDocument.summary?.page_count ?? 0} />
                <Metric label="Palavras" value={selectedDocument.summary?.word_count ?? 0} />
                <Metric label="Tickets" value={selectedDocument.summary?.ticket_count ?? 0} />
                <Metric label="Versões" value={selectedDocument.summary?.version_count ?? 0} />
              </div>

              <div className="mt-5">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Temas</h4>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(selectedDocument.summary?.themes ?? []).map((theme) => (
                    <Badge key={theme.theme} variant="info">
                      {theme.theme} ({theme.count})
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div>
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Seções</h4>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(selectedDocument.summary?.sections ?? []).map((section) => (
                      <Badge key={section.section} variant="warning">
                        {section.section} ({section.count})
                      </Badge>
                    ))}
                    {(selectedDocument.summary?.sections ?? []).length === 0 && (
                      <span className="text-sm text-gray-500">Sem seções extraídas.</span>
                    )}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Termos</h4>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(selectedDocument.summary?.knowledge_terms ?? []).slice(0, 10).map((term) => (
                      <Badge key={term.term} variant="success">
                        {term.term} ({term.count})
                      </Badge>
                    ))}
                    {(selectedDocument.summary?.knowledge_terms ?? []).length === 0 && (
                      <span className="text-sm text-gray-500">Sem termos de conhecimento.</span>
                    )}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Problema / Solução</h4>
                  <div className="mt-3 space-y-2">
                    {(selectedDocument.summary?.problem_solution_pairs ?? []).length > 0 ? (
                      (selectedDocument.summary?.problem_solution_pairs ?? []).slice(0, 3).map((item, index) => (
                        <div key={`${item.problem}-${index}`} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">{item.problem || 'Problema não identificado'}</p>
                          <p className="mt-1 text-sm text-gray-700">{item.solution || 'Solução não identificada'}</p>
                        </div>
                      ))
                    ) : (
                      <span className="text-sm text-gray-500">Sem pares problema/solução.</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div>
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Ações extraídas</h4>
                  <ul className="mt-3 space-y-2 text-sm text-gray-700">
                    {(selectedDocument.summary?.action_items ?? []).map((item) => <li key={item}>• {item}</li>)}
                    {(selectedDocument.summary?.action_items ?? []).length === 0 && <li>Sem ações destacadas.</li>}
                  </ul>
                </div>
                <div>
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-700">Recomendações</h4>
                  <ul className="mt-3 space-y-2 text-sm text-gray-700">
                    {(selectedDocument.summary?.recommendations ?? []).map((item) => <li key={item}>• {item}</li>)}
                    {(selectedDocument.summary?.recommendations ?? []).length === 0 && <li>Sem recomendações.</li>}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center text-sm text-gray-500">
              Use o menu Relatórios para processar PDFs pendentes e gerar inteligência contextual.
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl bg-gray-50 p-3">
      <p className="text-[11px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}
