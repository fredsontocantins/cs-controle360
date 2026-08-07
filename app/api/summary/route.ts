import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  const supabase = await createClient();

  // ⚡ Bolt Optimization: Fetch status and owner for all activities in a single query
  // and count them in memory. This reduces the total number of Supabase queries
  // from 8 down to 6 (eliminating redundant SELECT count and separate status/owner queries),
  // reducing network roundtrips, connection overhead, and database CPU usage.
  const [
    { count: homologacoes },
    { count: customizacoes },
    { count: releases },
    { count: clientes },
    { count: modulos },
    { data: activitiesData },
  ] = await Promise.all([
    supabase.from("homologations").select("*", { count: "exact", head: true }),
    supabase.from("customizations").select("*", { count: "exact", head: true }),
    supabase.from("releases").select("*", { count: "exact", head: true }),
    supabase.from("clients").select("*", { count: "exact", head: true }),
    supabase.from("modules").select("*", { count: "exact", head: true }),
    supabase.from("activities").select("status, owner"),
  ]);

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
    atividades: activitiesData?.length ?? 0,
    releases: releases ?? 0,
    clientes: clientes ?? 0,
    modulos: modulos ?? 0,
    activity_by_status: statusCounts,
    activity_by_owner: ownerArray,
  });
}
