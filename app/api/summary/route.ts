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

  // Optimization: Fetch all activities once to calculate multiple summaries
  const { data: allActivities } = await supabase
    .from("activities")
    .select("status, owner");

  const statusCounts: Record<string, number> = {};
  const ownerCounts: Record<string, number> = {};

  if (allActivities) {
    for (const activity of allActivities) {
      // Activity by status
      const status = activity.status || "unknown";
      statusCounts[status] = (statusCounts[status] || 0) + 1;

      // Activity by owner
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
