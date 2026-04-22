import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge, Button } from './';
import type { PdfIntelligenceDocument, PdfUploadNotice } from '../types';

interface PdfRecordUploadButtonProps {
  scopeType: string;
  scopeLabel: string;
  recordId: number;
  recordLabel: string;
  onUploaded?: (payload: {
    documents: PdfIntelligenceDocument[];
    skippedDocuments: PdfUploadNotice[];
  }) => void;
}

export function PdfRecordUploadButton({
  scopeType,
  scopeLabel,
  recordId,
  recordLabel,
  onUploaded,
}: PdfRecordUploadButtonProps) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadedDocuments, setUploadedDocuments] = useState<PdfIntelligenceDocument[]>([]);
  const [skippedDocuments, setSkippedDocuments] = useState<PdfUploadNotice[]>([]);

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) =>
      pdfIntelligenceApi.upload(scopeType, files, recordId, `${scopeLabel} · ${recordLabel}`),
    onSuccess: async (response) => {
      setUploadedDocuments(response.documents ?? []);
      setSkippedDocuments(response.skipped_documents ?? []);
      onUploaded?.({
        documents: response.documents ?? [],
        skippedDocuments: response.skipped_documents ?? [],
      });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'application-context'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'cycle-audit'] });
    },
  });

  const previewItems = [
    ...(uploadedDocuments.map((document) => ({
      key: `doc-${document.id}`,
      filename: document.filename,
      status: document.analysis_state || 'pending',
      pdfUrl: document.pdf_url || `/${document.pdf_path.replace(/^\/+/, '')}`,
      message: document.analysis_state === 'analyzed'
        ? 'PDF anexado e já lido pelo processamento.'
        : 'PDF anexado com sucesso e aguardando processamento.',
    }))),
    ...(skippedDocuments.map((notice) => ({
      key: `skip-${notice.filename}-${notice.status}`,
      filename: notice.filename,
      status: notice.status,
      pdfUrl: notice.pdf_url || null,
      message: notice.message,
    }))),
  ];

  const statusLabel = (value: string) => {
    const normalized = value.toLowerCase();
    if (['analyzed', 'read'].includes(normalized)) return 'Lido';
    if (['already_analyzed', 'duplicate', 'reused'].includes(normalized)) return 'Já lido';
    if (['pending', 'staged', 'new'].includes(normalized)) return 'Pendente';
    return value;
  };

  const statusTone = (value: string) => {
    const normalized = value.toLowerCase();
    if (['already_analyzed', 'duplicate', 'reused'].includes(normalized)) return 'warning';
    if (['analyzed', 'read'].includes(normalized)) return 'success';
    return 'info';
  };

  return (
    <div className="space-y-3">
      <Button
        size="sm"
        variant="success"
        onClick={() => inputRef.current?.click()}
        disabled={uploadMutation.isPending}
        >
          {uploadMutation.isPending ? 'Adicionando...' : 'Adicionar PDF'}
        </Button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length > 0) {
            uploadMutation.mutate(files);
          }
          e.target.value = '';
        }}
      />
      {previewItems.length > 0 && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
          <p className="text-sm font-semibold text-emerald-900">PDF anexado com sucesso</p>
          <div className="mt-2 space-y-2">
            {previewItems.map((item) => (
              <div key={item.key} className="rounded-lg border border-emerald-200 bg-white px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-gray-900">{item.filename}</p>
                  <Badge variant={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                </div>
                <p className="mt-1 text-xs text-gray-600">{item.message}</p>
                {item.pdfUrl && (
                  <a
                    href={item.pdfUrl}
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
    </div>
  );
}
