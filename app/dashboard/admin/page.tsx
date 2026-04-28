import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

async function getModules() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("modules")
    .select("*")
    .order("name", { ascending: true });
  return data ?? [];
}

async function getClients() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("clients")
    .select("*")
    .order("name", { ascending: true });
  return data ?? [];
}

export default async function AdminPage() {
  const [modules, clients] = await Promise.all([getModules(), getClients()]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Administração</h1>
          <p className="text-muted-foreground mt-1">
            Gerenciamento de módulos e clientes
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Módulos */}
        <Card>
          <CardHeader>
            <CardTitle>Módulos ({modules.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {modules.length === 0 ? (
              <p className="text-muted-foreground text-sm py-4 text-center">
                Nenhum módulo registrado ainda.
              </p>
            ) : (
              <div className="space-y-3">
                {modules.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 border border-border rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-foreground">{m.name}</h4>
                        {m.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {m.description}
                          </p>
                        )}
                      </div>
                      {m.owner && (
                        <Badge variant="info">{m.owner}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Criado: {formatDate(m.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Clientes */}
        <Card>
          <CardHeader>
            <CardTitle>Clientes ({clients.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {clients.length === 0 ? (
              <p className="text-muted-foreground text-sm py-4 text-center">
                Nenhum cliente registrado ainda.
              </p>
            ) : (
              <div className="space-y-3">
                {clients.map((c) => (
                  <div
                    key={c.id}
                    className="p-3 border border-border rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-foreground">{c.name}</h4>
                        {c.segment && (
                          <p className="text-sm text-muted-foreground mt-1">
                            Segmento: {c.segment}
                          </p>
                        )}
                      </div>
                      {c.owner && (
                        <Badge variant="info">{c.owner}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Criado: {formatDate(c.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
