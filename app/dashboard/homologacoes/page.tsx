import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

async function getHomologacoes() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("homologations")
    .select("*")
    .order("created_at", { ascending: false });
  return data ?? [];
}

export default async function HomologacoesPage() {
  const homologacoes = await getHomologacoes();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Homologações</h1>
          <p className="text-muted-foreground mt-1">
            Gerenciamento de homologações de módulos
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Homologações</CardTitle>
        </CardHeader>
        <CardContent>
          {homologacoes.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma homologação registrada ainda.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Módulo
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Versão Homologação
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Versão Produção
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Cliente
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Data Verificação
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {homologacoes.map((h) => (
                    <tr
                      key={h.id}
                      className="border-b border-border last:border-0 hover:bg-muted/50"
                    >
                      <td className="py-3 px-4 text-sm font-medium text-foreground">
                        {h.module || "-"}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            h.status === "Homologado"
                              ? "success"
                              : h.status === "Em Andamento"
                              ? "info"
                              : "default"
                          }
                        >
                          {h.status || "Pendente"}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {h.homologation_version || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {h.production_version || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {h.client || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {formatDate(h.check_date)}
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
