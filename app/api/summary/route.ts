import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // Optimization: Consolidate activities operations into a single query fetching 'status' and 'owner'.
  // This avoids 3 separate DB round-trips for the same 'activities' table (head count, select status, select owner)
  // and allows executing all summary queries concurrently in a single Promise.all batch.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { data: activitiesData, count: activitiesCount },
    { count: releases },
    { count: clientes },
    { count: modulos },
  ] = await Promise.all([
    supabase.from("homologations").select("*", { count: "exact", head: true }),
    supabase.from("customizations").select("*", { count: "exact", head: true }),
    supabase.from("activities").select("status, owner", { count: "exact" }),
    supabase.from("releases").select("*", { count: "exact", head: true }),
    supabase.from("clients").select("*", { count: "exact", head: true }),
    supabase.from("modules").select("*", { count: "exact", head: true }),
  ]);

  const activities = activitiesData ?? [];
  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  // Single pass aggregation over activities to calculate total count, status counts, and owner counts
  for (let i = 0; i < activities.length; i++) {
    const a = activities[i];
    if (a.status) {
      statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
    }
    if (a.owner) {
      ownerCounts[a.owner] = (ownerCounts[a.owner] || 0) + 1;
    }
  }

  const ownerArray = Object.entries(ownerCounts)
    .map(([owner, count]) => ({ owner, count }))
    .sort((a, b) => b.count - a.count);

  return NextResponse.json({
    homologacoes: homologacoes ?? 0,
    customizacoes: customizacoes ?? 0,
    atividades: activitiesCount ?? activities.length,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
