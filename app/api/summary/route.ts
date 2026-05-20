import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
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

  // Get activity by status (Server-side aggregation)
  const { data: statusStats } = await supabase
    .from("activities")
    .select("status")
    .then(({ data }) => {
      const counts: Record<string, number> = {};
      data?.forEach((a) => {
        counts[a.status] = (counts[a.status] || 0) + 1;
      });
      return { data: counts };
    });

  // Get activity by owner (Server-side aggregation)
  const { data: ownerStats } = await supabase
    .from("activities")
    .select("owner")
    .then(({ data }) => {
      const counts: Record<string, number> = {};
      data?.forEach((a) => {
        if (a.owner) {
          counts[a.owner] = (counts[a.owner] || 0) + 1;
        }
      });
      const sorted = Object.entries(counts)
        .map(([owner, count]) => ({ owner, count }))
        .sort((a, b) => b.count - a.count);
      return { data: sorted };
    });

  return NextResponse.json({
    homologacoes: homologacoes ?? 0,
    customizacoes: customizacoes ?? 0,
    atividades: atividades ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusStats ?? {},
    activity_by_owner: ownerStats ?? [],
  });
}
