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

  // Optimized aggregation using rpc or single query if possible,
  // but since we are using Supabase JS client and might not have rpc configured,
  // we'll optimize by fetching only necessary columns and doing it in parallel.

  const [
    { data: activityByStatus },
    { data: activityByOwner }
  ] = await Promise.all([
    supabase.from("activities").select("status"),
    supabase.from("activities").select("owner")
  ]);

  const statusCounts: Record<string, number> = {};
  activityByStatus?.forEach((a) => {
    statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
  });

  const ownerCounts: Record<string, number> = {};
  activityByOwner?.forEach((a) => {
    if (a.owner) {
      ownerCounts[a.owner] = (ownerCounts[a.owner] || 0) + 1;
    }
  });

  const ownerArray = Object.entries(ownerCounts)
    .map(([owner, count]) => ({ owner, count }))
    .sort((a, b) => b.count - a.count);

  return NextResponse.json({
    homologacoes: homologacoes ?? 0,
    customizacoes: customizacoes ?? 0,
    atividades: atividades ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
