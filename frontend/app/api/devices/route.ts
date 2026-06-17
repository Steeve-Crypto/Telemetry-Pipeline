import { NextRequest } from "next/server";

import { proxyToPipeline } from "@/lib/upstream";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  return proxyToPipeline(request, "/api/devices");
}