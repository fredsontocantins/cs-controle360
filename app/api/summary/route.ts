import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // Optimization ⚡: Single projection query for activities fetching count, status, and owner together.
  // Reduces backend database requests from 8 to 6, eliminating redundant network round-trips.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: releases },
    { count: clientes },
    { count: modulos },
    { count: atividades, data: activitiesData },
  ] = await Promise.all([
    supabase.from("homologations").select("*", { count: "exact", head: true }),
    supabase.from("customizations").select("*", { count: "exact", head: true }),
    supabase.from("releases").select("*", { count: "exact", head: true }),
    supabase.from("clients").select("*", { count: "exact", head: true }),
    supabase.from("modules").select("*", { count: "exact", head: true }),
    supabase.from("activities").select("status, owner", { count: "exact" }),
  ]);

  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  if (activitiesData) {
    for (const activity of activitiesData) {
      if (activity.status) {
        statusCounts[activity.status] = (statusCounts[activity.status] || 0) + 1;
      }
      if (activity.owner) {
        ownerCounts[activity.owner] = (ownerCounts[activity.owner] || 0) + 1;
      }
    }
  }

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
