import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge, Button, Card, Select } from './';
import type { PdfIntelligenceDocument, PdfUploadNotice } from '../types';

interface RecordOption {
  id: number;
  label: string;
}

interface PdfUploadCardProps {
  scopeType: string;
  scopeLabel: string;
  scopeId?: number | null;
  recordOptions?: RecordOption[];
}

export function PdfUploadCard({
  scopeType,
  scopeLabel,
  scopeId = null,
  recordOptions = [],
}: PdfUploadCardProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(scopeId);
  const [notices, setNotices] = useState<PdfUploadNotice[]>([]);
  const [uploadedDocuments, setUploadedDocuments] = useState<PdfIntelligenceDocument[]>([]);

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
    setNotices([]);
    setUploadedDocuments([]);
  }, [activeScopeId]);

  const scopeKey = useMemo(() => [scopeType, activeScopeId ?? 'global'], [scopeType, activeScopeId]);

  const uploadMutation = useMutation({
    mutationFn: () => pdfIntelligenceApi.upload(activeScopeId !== null ? scopeType : 'auto', files, activeScopeId, activeScopeLabel),
    onSuccess: async (response) => {
      setFiles([]);
      setNotices(response.skipped_documents ?? []);
      setUploadedDocuments(response.documents ?? []);
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', ...scopeKey] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'application-context'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'cycle-audit'] });
    },
  });

  const statusLabel = (value: string) => {
    const normalized = value.toLowerCase();
    if (['analyzed', 'read'].includes(normalized)) return 'Lido';
    if (['already_analyzed', 'duplicate', 'reused'].includes(normalized)) return 'Já lido';
    if (['pending', 'staged', 'new'].includes(normalized)) return 'Pendente';
    return value;
  };

  return (
    <Card className="border border-dashed border-[#0d3b66]/20 bg-white/95">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2">
            <Badge variant="info">Adicionar PDF</Badge>
            <Badge variant="warning">{activeScopeLabel}</Badge>
          </div>
          <h2 className="mt-3 text-lg font-semibold text-gray-900">Adicionar PDFs ao sistema</h2>
          <p className="mt-2 text-sm text-gray-600">
            Envie arquivos para deixar disponíveis no sistema. O processamento da inteligência acontece no menu Relatórios.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
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
            disabled={files.length === 0 || uploadMutation.isPending}
            onClick={() => uploadMutation.mutate()}
          >
            {uploadMutation.isPending ? 'Salvando...' : `Adicionar PDF (${files.length})`}
          </Button>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4 rounded-2xl bg-gray-50 p-4">
          <p className="text-sm font-semibold text-gray-900">Arquivos selecionados</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <Badge key={file.name} variant="default">{file.name}</Badge>
            ))}
          </div>
        </div>
      )}

      {(uploadedDocuments.length > 0 || notices.length > 0) && (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-semibold text-emerald-900">PDF anexado com sucesso</p>
          <div className="mt-2 space-y-2">
            {uploadedDocuments.map((document) => (
              <div key={document.id} className="rounded-xl border border-emerald-200 bg-white px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-gray-900">{document.filename}</p>
                  <Badge variant={document.analysis_state === 'analyzed' ? 'success' : 'warning'}>
                    {statusLabel(document.analysis_state || 'pending')}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-gray-600">
                  {document.analysis_state === 'analyzed'
                    ? 'PDF já foi lido pelo processamento.'
                    : 'PDF anexado e aguardando processamento no menu Relatórios.'}
                </p>
                {document.pdf_url && (
                  <a
                    href={document.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-xs font-medium text-[#0d3b66] hover:underline"
                  >
                    Ver PDF
                  </a>
                )}
              </div>
            ))}
            {notices.map((notice) => (
              <div key={`${notice.filename}-${notice.status}`} className="rounded-xl border border-emerald-200 bg-white px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-gray-900">{notice.filename}</p>
                  <Badge variant="warning">{statusLabel(notice.status)}</Badge>
                </div>
                <p className="mt-1 text-xs text-gray-600">{notice.message}</p>
                {notice.pdf_url && (
                  <a
                    href={notice.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-xs font-medium text-[#0d3b66] hover:underline"
                  >
                    Ver PDF
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </Card>
  );
}
