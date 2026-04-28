import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "-";
  return new Date(date).toLocaleDateString("pt-BR");
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return "-";
  return new Date(date).toLocaleString("pt-BR");
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export const statusColors: Record<string, string> = {
  backlog: "bg-gray-100 text-gray-700",
  em_andamento: "bg-blue-100 text-blue-700",
  em_revisao: "bg-yellow-100 text-yellow-700",
  concluida: "bg-green-100 text-green-700",
  bloqueada: "bg-red-100 text-red-700",
  ativo: "bg-green-100 text-green-700",
  prestado: "bg-blue-100 text-blue-700",
  revisar: "bg-yellow-100 text-yellow-700",
  arquivado: "bg-gray-100 text-gray-700",
  approved: "bg-green-100 text-green-700",
  pending: "bg-yellow-100 text-yellow-700",
  blocked: "bg-red-100 text-red-700",
};

export const tipoLabels: Record<string, string> = {
  nova_funcionalidade: "Nova Funcionalidade",
  correcao_bug: "Correção de Bug",
  melhoria: "Melhoria",
};

export const statusLabels: Record<string, string> = {
  backlog: "Backlog",
  em_andamento: "Em Andamento",
  em_revisao: "Em Revisão",
  concluida: "Concluída",
  bloqueada: "Bloqueada",
};
