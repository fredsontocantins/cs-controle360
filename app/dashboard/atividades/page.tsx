import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

async function getAtividades() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("activities")
    .select("*")
    .order("created_at", { ascending: false });
  return data ?? [];
}

export default async function AtividadesPage() {
  const atividades = await getAtividades();

  const statusLabels: Record<string, string> = {
    backlog: "Backlog",
    em_andamento: "Em Andamento",
    em_revisao: "Em Revisão",
    concluida: "Concluída",
    bloqueada: "Bloqueada",
  };

  const statusVariants: Record<string, "default" | "info" | "success" | "warning" | "danger"> = {
    backlog: "default",
    em_andamento: "info",
    em_revisao: "warning",
    concluida: "success",
    bloqueada: "danger",
  };

  const tipoLabels: Record<string, string> = {
    nova_funcionalidade: "Nova Funcionalidade",
    correcao_bug: "Correção de Bug",
    melhoria: "Melhoria",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Atividades</h1>
          <p className="text-muted-foreground mt-1">
            Gerenciamento de atividades e tickets
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Atividades</CardTitle>
        </CardHeader>
        <CardContent>
          {atividades.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma atividade registrada ainda.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Título
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Tipo
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Responsável
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Ticket
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Criado em
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {atividades.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-border last:border-0 hover:bg-muted/50"
                    >
                      <td className="py-3 px-4 text-sm font-medium text-foreground">
                        {a.title}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {tipoLabels[a.tipo] || a.tipo}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={statusVariants[a.status] || "default"}>
                          {statusLabels[a.status] || a.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {a.owner || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {a.ticket || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {formatDate(a.created_at)}
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
