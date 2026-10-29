import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // Fetch entity exact counts and activity fields (status, owner) in a single batch call.
  // Combining the activities count, status, and owner into 1 query reduces database roundtrips from 8 to 6.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: activitiesCount, data: activitiesData },
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

  // Process activity status and owner metrics in a single pass
  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  activitiesData?.forEach((a) => {
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
    atividades: activitiesCount ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
