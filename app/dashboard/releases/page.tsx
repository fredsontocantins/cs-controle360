import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

async function getReleases() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("releases")
    .select("*")
    .order("created_at", { ascending: false });
  return data ?? [];
}

export default async function ReleasesPage() {
  const releases = await getReleases();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Releases</h1>
          <p className="text-muted-foreground mt-1">
            Gerenciamento de versões e releases
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lista de Releases</CardTitle>
        </CardHeader>
        <CardContent>
          {releases.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhum release registrado ainda.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Nome
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Versão
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Módulo
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Cliente
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Data Aplicação
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Notas
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {releases.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-border last:border-0 hover:bg-muted/50"
                    >
                      <td className="py-3 px-4 text-sm font-medium text-foreground">
                        {r.release_name}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        <span className="font-mono bg-muted px-2 py-0.5 rounded">
                          {r.version}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {r.module || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {r.client || "-"}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground">
                        {formatDate(r.applies_on)}
                      </td>
                      <td className="py-3 px-4 text-sm text-muted-foreground max-w-xs truncate">
                        {r.notes || "-"}
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
