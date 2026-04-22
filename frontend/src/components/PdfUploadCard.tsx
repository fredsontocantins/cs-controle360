import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge, Button, Card, Select } from './';
import type { PdfUploadNotice } from '../types';

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
  }, [activeScopeId]);

  const scopeKey = useMemo(() => [scopeType, activeScopeId ?? 'global'], [scopeType, activeScopeId]);

  const uploadMutation = useMutation({
    mutationFn: () => pdfIntelligenceApi.upload(activeScopeId !== null ? scopeType : 'auto', files, activeScopeId, activeScopeLabel),
    onSuccess: async (response) => {
      setFiles([]);
      setNotices(response.skipped_documents ?? []);
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', ...scopeKey] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'application-context'] });
      await queryClient.invalidateQueries({ queryKey: ['pdf-intelligence', 'cycle-audit'] });
    },
  });

  return (
    <Card className="border border-dashed border-[#0d3b66]/20 bg-white/95">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2">
            <Badge variant="info">Upload de PDF</Badge>
            <Badge variant="warning">{activeScopeLabel}</Badge>
          </div>
          <h2 className="mt-3 text-lg font-semibold text-gray-900">Subir e processar PDFs desta tela</h2>
          <p className="mt-2 text-sm text-gray-600">
            Envie arquivos agora ou depois. O sistema identifica o contexto automaticamente e reaproveita PDFs já analisados.
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
            {uploadMutation.isPending ? 'Analisando...' : `Processar (${files.length})`}
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

      {notices.length > 0 && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900">Arquivos descartados da análise atual</p>
          <div className="mt-2 space-y-2">
            {notices.map((notice) => (
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
