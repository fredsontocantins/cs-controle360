import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatCurrency } from "@/lib/utils";

async function getCustomizacoes() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("customizations")
    .select("*")
    .order("created_at", { ascending: false });
  return data ?? [];
}

export default async function CustomizacoesPage() {
  const customizacoes = await getCustomizacoes();

  const stageLabels: Record<string, string> = {
    em_elaboracao: "Em Elaboração",
    enviada: "Enviada",
    aprovada: "Aprovada",
    em_desenvolvimento: "Em Desenvolvimento",
    concluida: "Concluída",
    cancelada: "Cancelada",
  };

  const stageVariants: Record<string, "default" | "info" | "success" | "warning" | "danger"> = {
    em_elaboracao: "default",
    enviada: "info",
    aprovada: "success",
    em_desenvolvimento: "warning",
    concluida: "success",
    cancelada: "danger",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Customizações</h1>
          <p className="text-muted-foreground mt-1">
            Gerenciamento de propostas de customização
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Customizações</CardTitle>
        </CardHeader>
        <CardContent>
          {customizacoes.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma customização registrada ainda.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Proposta
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Assunto
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Cliente
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Módulo
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Estágio
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Valor
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Recebido em
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {customizacoes.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-border last:border-0 hover:bg-muted/50"
                    >
                      <td className="py-3 px-4 text-sm font-medium text-foreground">
                        {c.proposal}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {c.subject}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {c.client || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {c.module || "-"}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={stageVariants[c.stage] || "default"}>
                          {stageLabels[c.stage] || c.stage}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {formatCurrency(c.value)}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {formatDate(c.received_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
