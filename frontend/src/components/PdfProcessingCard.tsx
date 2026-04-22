import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge, Button, Card, Select } from './';
import type { PdfIntelligenceDocument, PdfUploadNotice } from '../types';

interface RecordOption {
  id: number;
  label: string;
}

interface PdfProcessingCardProps {
  scopeType?: string | null;
  scopeLabel: string;
  scopeId?: number | null;
  recordOptions?: RecordOption[];
}

export function PdfProcessingCard({
  scopeType = 'global',
  scopeLabel,
  scopeId = null,
  recordOptions = [],
}: PdfProcessingCardProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(scopeId);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [uploadNotices, setUploadNotices] = useState<PdfUploadNotice[]>([]);
  const [resultContextMessage, setResultContextMessage] = useState<string | null>(null);

  const { data: applicationContext } = useQuery({
    queryKey: ['pdf-intelligence', 'application-context'],
    queryFn: pdfIntelligenceApi.applicationContext,
  });

  const { data: cycleAudit } = useQuery({
    queryKey: ['pdf-intelligence', 'cycle-audit'],
    queryFn: pdfIntelligenceApi.cycleAudit,
  });

  const pendingDocs = cycleAudit?.pending_documents ?? [];
  const newDocs = cycleAudit?.new_documents ?? [];
  const changedDocs = cycleAudit?.changed_documents ?? [];
  const analyzedDocs = applicationContext?.documents ?? [];

  const currentContextLabel = useMemo(() => {
    if (recordOptions.length > 0 && selectedRecordId !== null) {
      return recordOptions.find((option) => option.id === selectedRecordId)?.label || scopeLabel;
    }
    return scopeLabel;
  }, [recordOptions, scopeLabel, selectedRecordId]);

  const allSelectableDocuments = useMemo(() => {
    const byId = new Map<number, PdfIntelligenceDocument | PdfUploadNotice & { id?: number }>();
    [...analyzedDocs, ...pendingDocs, ...newDocs, ...changedDocs].forEach((doc: any) => {
      const id = Number(doc.id ?? doc.document_id ?? doc.existing_document_id ?? 0);
      if (id > 0) {
        byId.set(id, doc);
      }
    });
    return [...byId.values()].sort((left: any, right: any) => {
      const leftTime = new Date(left.created_at || left.generated_at || 0).getTime();
      const rightTime = new Date(right.created_at || right.generated_at || 0).getTime();
      return rightTime - leftTime;
    });
  }, [analyzedDocs, changedDocs, newDocs, pendingDocs]);

  const stageMutation = useMutation({
    mutationFn: () => pdfIntelligenceApi.stage(
      selectedRecordId !== null ? scopeType ?? 'auto' : 'auto',
      files,
      selectedRecordId ?? scopeId,
      currentContextLabel,
    ),
    onSuccess: async (response) => {
      setUploadNotices(response.skipped_documents ?? []);
      setFiles([]);
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'cycle-audit'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'application-context'] });
    },
  });

  const processMutation = useMutation({
    mutationFn: () => pdfIntelligenceApi.process({
      documentIds: selectedDocumentIds,
      scopeType: scopeType ?? 'global',
      scopeId: selectedRecordId ?? scopeId,
      scopeLabel: currentContextLabel,
    }),
    onSuccess: async (response) => {
      setResultContextMessage(`Processados ${response.documents?.length ?? 0} documento(s).`);
      setSelectedDocumentIds([]);
      setUploadNotices(response.skipped_documents ?? []);
      setFiles([]);
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'cycle-audit'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'application-context'] });
    },
  });

  const handleProcess = async () => {
    if (files.length > 0) {
      await stageMutation.mutateAsync();
    }
    await processMutation.mutateAsync();
  };

  return (
    <Card className="border border-dashed border-[#0d3b66]/20 bg-white/95">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2">
            <Badge variant="info">Relatórios</Badge>
            <Badge variant="warning">{currentContextLabel}</Badge>
          </div>
          <h2 className="mt-3 text-lg font-semibold text-gray-900">Processar PDFs pendentes e selecionados</h2>
          <p className="mt-2 text-sm text-gray-600">
            O botão Processar lê todos os PDFs ainda não analisados e também os documentos que você marcar manualmente.
            PDFs já analisados são descartados da análise atual e continuam disponíveis no histórico.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          {recordOptions.length > 0 && (
            <div className="min-w-[240px]">
              <Select
                label="Recorte"
                options={[
                  { value: '', label: 'Selecione...' },
                  ...recordOptions.map((option) => ({ value: String(option.id), label: option.label })),
                ]}
                value={selectedRecordId !== null ? String(selectedRecordId) : ''}
                onChange={(e) => {
                  const value = e.target.value;
                  setSelectedRecordId(value ? Number(value) : null);
                }}
              />
            </div>
          )}

          <label className="inline-flex cursor-pointer items-center justify-center rounded-lg border-2 border-[#0d3b66] px-4 py-2 text-sm font-medium text-[#0d3b66] hover:bg-[#0d3b66] hover:text-white">
            Selecionar PDFs
            <input
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e) => {
                const picked = Array.from(e.target.files ?? []);
                setFiles((current) => [...current, ...picked]);
                e.target.value = '';
              }}
            />
          </label>

          <Button
            type="button"
            disabled={processMutation.isPending || stageMutation.isPending}
            onClick={() => handleProcess()}
          >
            {processMutation.isPending || stageMutation.isPending ? 'Processando...' : 'Processar pendentes'}
          </Button>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4 rounded-2xl bg-gray-50 p-4">
          <p className="text-sm font-semibold text-gray-900">Arquivos colocados no sistema</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <Badge key={file.name} variant="default">{file.name}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-900">Pendentes e novos</p>
            <Badge variant="warning">{pendingDocs.length + newDocs.length + changedDocs.length}</Badge>
          </div>
          <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
            {[...pendingDocs, ...newDocs, ...changedDocs].map((doc: any) => (
              <label
                key={doc.id}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3"
              >
                <input
                  type="checkbox"
                  checked={selectedDocumentIds.includes(doc.id)}
                  onChange={(e) => {
                    setSelectedDocumentIds((current) => (
                      e.target.checked
                        ? [...current, doc.id]
                        : current.filter((id) => id !== doc.id)
                    ));
                  }}
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                  <p className="text-xs text-gray-500">{doc.scope_label || currentContextLabel}</p>
                </div>
              </label>
            ))}
            {[...pendingDocs, ...newDocs, ...changedDocs].length === 0 && (
              <p className="text-sm text-gray-500">Nenhum PDF pendente para processar.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-900">Selecionados e já processados</p>
            <Badge variant="info">{allSelectableDocuments.length}</Badge>
          </div>
          <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
            {allSelectableDocuments.map((doc: any) => (
              <label
                key={doc.id}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3"
              >
                <input
                  type="checkbox"
                  checked={selectedDocumentIds.includes(doc.id)}
                  onChange={(e) => {
                    setSelectedDocumentIds((current) => (
                      e.target.checked
                        ? [...current, doc.id]
                        : current.filter((id) => id !== doc.id)
                    ));
                  }}
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                  <p className="text-xs text-gray-500">
                    {(doc.scope_label || currentContextLabel)} · {doc.analysis_state || 'analisado'}
                  </p>
                </div>
              </label>
            ))}
            {allSelectableDocuments.length === 0 && (
              <p className="text-sm text-gray-500">Nenhum documento disponível.</p>
            )}
          </div>
        </div>
      </div>

      {resultContextMessage && (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-semibold text-emerald-900">{resultContextMessage}</p>
          <p className="mt-1 text-xs text-emerald-800">A inteligência processada retorna no menu Relatórios e atualiza o contexto geral.</p>
        </div>
      )}

      {uploadNotices.length > 0 && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900">Documentos já tratados ou descartados</p>
          <div className="mt-2 space-y-2">
            {uploadNotices.map((notice) => (
              <div key={`${notice.filename}-${notice.status}`} className="rounded-xl border border-amber-200 bg-white px-3 py-2">
                <p className="text-sm font-medium text-amber-900">{notice.filename}</p>
                <p className="text-xs text-amber-800">{notice.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
