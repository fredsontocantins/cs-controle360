import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckSquare,
  FileText,
  ListTodo,
  Package,
  Users,
  Layers,
} from "lucide-react";

async function getSummary() {
  const supabase = await createClient();

  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: atividades },
    { count: releases },
    { count: clientes },
    { count: modulos },
  ] = await Promise.all([
    supabase.from("homologations").select("*", { count: "exact", head: true }),
    supabase.from("customizations").select("*", { count: "exact", head: true }),
    supabase.from("activities").select("*", { count: "exact", head: true }),
    supabase.from("releases").select("*", { count: "exact", head: true }),
    supabase.from("clients").select("*", { count: "exact", head: true }),
    supabase.from("modules").select("*", { count: "exact", head: true }),
  ]);

  return {
    homologacoes: homologacoes ?? 0,
    customizacoes: customizacoes ?? 0,
    atividades: atividades ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
  };
}

async function getRecentActivities() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("activities")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(5);
  return data ?? [];
}

export default async function DashboardPage() {
  const [summary, recentActivities] = await Promise.all([
    getSummary(),
    getRecentActivities(),
  ]);

  const stats = [
    {
      name: "Homologações",
      value: summary.homologacoes,
      icon: CheckSquare,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      name: "Customizações",
      value: summary.customizacoes,
      icon: FileText,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      name: "Atividades",
      value: summary.atividades,
      icon: ListTodo,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      name: "Releases",
      value: summary.releases,
      icon: Package,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
    {
      name: "Clientes",
      value: summary.clientes,
      icon: Users,
      color: "text-pink-600",
      bgColor: "bg-pink-100",
    },
    {
      name: "Módulos",
      value: summary.modulos,
      icon: Layers,
      color: "text-indigo-600",
      bgColor: "bg-indigo-100",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Visão geral do sistema de controle
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="flex items-center gap-4 py-6">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {stat.name}
                </p>
                <p className="text-2xl font-bold text-foreground">
                  {stat.value}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Activities */}
      <Card>
        <CardHeader>
          <CardTitle>Atividades Recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {recentActivities.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              Nenhuma atividade registrada ainda.
            </p>
          ) : (
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-center justify-between py-3 border-b border-border last:border-0"
                >
                  <div>
                    <p className="font-medium text-foreground">
                      {activity.title}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {activity.owner || "Sem responsável"}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      activity.status === "concluida"
                        ? "bg-green-100 text-green-700"
                        : activity.status === "em_andamento"
                        ? "bg-blue-100 text-blue-700"
                        : activity.status === "bloqueada"
                        ? "bg-red-100 text-red-700"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {activity.status === "concluida"
                      ? "Concluída"
                      : activity.status === "em_andamento"
                      ? "Em Andamento"
                      : activity.status === "bloqueada"
                      ? "Bloqueada"
                      : activity.status === "em_revisao"
                      ? "Em Revisão"
                      : "Backlog"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
