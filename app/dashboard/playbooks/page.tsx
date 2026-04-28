import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

async function getPlaybooks() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("playbooks")
    .select("*")
    .order("created_at", { ascending: false });
  return data ?? [];
}

export default async function PlaybooksPage() {
  const playbooks = await getPlaybooks();

  const statusLabels: Record<string, string> = {
    ativo: "Ativo",
    prestado: "Prestado",
    revisar: "Revisar",
    arquivado: "Arquivado",
  };

  const statusVariants: Record<string, "default" | "info" | "success" | "warning" | "danger"> = {
    ativo: "success",
    prestado: "info",
    revisar: "warning",
    arquivado: "default",
  };

  const priorityLabels: Record<string, string> = {
    alta: "Alta",
    media: "Média",
    baixa: "Baixa",
  };

  const priorityVariants: Record<string, "default" | "info" | "success" | "warning" | "danger"> = {
    alta: "danger",
    media: "warning",
    baixa: "default",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Playbooks</h1>
          <p className="text-muted-foreground mt-1">
            Base de conhecimento e procedimentos
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Playbooks</CardTitle>
        </CardHeader>
        <CardContent>
          {playbooks.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhum playbook registrado ainda.
            </p>
          ) : (
            <div className="space-y-4">
              {playbooks.map((p) => (
                <div
                  key={p.id}
                  className="p-4 border border-border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <h3 className="font-medium text-foreground">{p.title}</h3>
                      {p.summary && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {p.summary}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
                        <span>Origem: {p.origin}</span>
                        {p.area && <span>Área: {p.area}</span>}
                        <span>Criado: {formatDate(p.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={priorityVariants[p.priority_level] || "default"}>
                        {priorityLabels[p.priority_level] || p.priority_level}
                      </Badge>
                      <Badge variant={statusVariants[p.status] || "default"}>
                        {statusLabels[p.status] || p.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
