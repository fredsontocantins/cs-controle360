import { useQuery } from '@tanstack/react-query';
import { pdfIntelligenceApi } from '../services/api';
import { Badge } from './';

interface PdfRecordStatusBadgeProps {
  scopeType: string;
  recordId: number;
}

export function PdfRecordStatusBadge({ scopeType, recordId }: PdfRecordStatusBadgeProps) {
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['pdf-intelligence', scopeType, recordId],
    queryFn: () => pdfIntelligenceApi.list(scopeType, recordId),
  });

  if (isLoading) {
    return <Badge variant="default">PDF...</Badge>;
  }

  if (!documents.length) {
    return <Badge variant="default">Sem PDF</Badge>;
  }

  const analyzedCount = documents.filter((document) => {
    const state = String(document.analysis_state || '').toLowerCase();
    return state === 'analyzed' || state === 'read';
  }).length;
  const pendingCount = documents.length - analyzedCount;

  if (analyzedCount > 0 && pendingCount === 0) {
    return <Badge variant="success">Lido ({documents.length})</Badge>;
  }

  if (analyzedCount > 0) {
    return <Badge variant="info">Parcial ({documents.length})</Badge>;
  }

  return <Badge variant="warning">Anexado ({documents.length})</Badge>;
}
