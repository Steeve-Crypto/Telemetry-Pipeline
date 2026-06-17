import { NextRequest } from "next/server";

import { proxyStreamToPipeline } from "@/lib/upstream-stream";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyStreamToPipeline(request);
}