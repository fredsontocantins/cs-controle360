import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // Performance optimization (Bolt ⚡): Merge head count, status, and owner requests for "activities"
  // into a single projection query executed in parallel with other table head counts.
  // This reduces total database round-trips from 8 (6 in Promise.all + 2 sequential) to 6 (all in Promise.all).
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: activitiesResult, data: activitiesData },
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

  // Single-pass aggregation for status and owner counts
  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  if (activitiesData) {
    for (const a of activitiesData) {
      if (a.status) {
        statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
      }
      if (a.owner) {
        ownerCounts[a.owner] = (ownerCounts[a.owner] || 0) + 1;
      }
    }
  }

  const ownerArray = Object.entries(ownerCounts)
    .map(([owner, count]) => ({ owner, count }))
    .sort((a, b) => b.count - a.count);

  return NextResponse.json({
    homologacoes: homologacoes ?? 0,
    customizacoes: customizacoes ?? 0,
    atividades: activitiesResult ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
