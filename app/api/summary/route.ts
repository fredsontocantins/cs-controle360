import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // Performance Optimization: Fetch all entity counts and activity projection (status + owner)
  // in a single concurrent Promise.all batch.
  // This merges 3 separate queries on 'activities' (exact head count, status SELECT, and owner SELECT)
  // into 1 query, reducing total DB queries from 8 to 6 and network roundtrips from 3 to 1.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: releases },
    { count: clientes },
    { count: modulos },
    { count: atividadesCount, data: activityData },
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

  // Single-pass aggregation for both status and owner counts
  activityData?.forEach((a) => {
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
    atividades: atividadesCount ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
