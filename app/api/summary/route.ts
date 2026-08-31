import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export const runtime = 'edge';

export async function GET() {
  const supabase = await createClient();

  // Bolt Optimization: Consolidate 3 separate activities database queries into 1 projection query.
  // Reduces total backend DB queries from 8 to 6 and eliminates duplicate network round-trips.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: releases },
    { count: clientes },
    { count: modulos },
    activitiesRes,
  ] = await Promise.all([
    supabase.from("homologations").select("*", { count: "exact", head: true }),
    supabase.from("customizations").select("*", { count: "exact", head: true }),
    supabase.from("releases").select("*", { count: "exact", head: true }),
    supabase.from("clients").select("*", { count: "exact", head: true }),
    supabase.from("modules").select("*", { count: "exact", head: true }),
    supabase.from("activities").select("status, owner", { count: "exact" }),
  ]);

  const atividades = activitiesRes.count ?? 0;
  const activities = activitiesRes.data ?? [];

  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  // Single-pass O(N) aggregation over activities for status and owner
  activities.forEach((a) => {
    if (a.status) {
      statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
    }
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
