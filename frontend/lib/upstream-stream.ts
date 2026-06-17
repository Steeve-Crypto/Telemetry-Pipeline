import { NextRequest, NextResponse } from "next/server";

import { getTelemetryApiUrl } from "@/lib/api";
import { resolveTenantApiKey } from "@/lib/tenant-server";

export async function proxyStreamToPipeline(
  request: NextRequest,
): Promise<NextResponse> {
  const tenantId =
    request.nextUrl.searchParams.get("tenant_id") ??
    request.headers.get("x-tenant-id");
  const apiKey =
    request.headers.get("x-api-key") ?? resolveTenantApiKey(tenantId) ?? undefined;
  const base = getTelemetryApiUrl();
  const query = request.nextUrl.search;

  try {
    const headers: HeadersInit = { Accept: "text/event-stream" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    if (tenantId) {
      headers["X-Tenant-Id"] = tenantId;
    }

    const upstream = await fetch(`${base}/api/stream${query}`, {
      headers,
      cache: "no-store",
    });

    if (!upstream.ok || !upstream.body) {
      const body = await upstream.text();
      return new NextResponse(body || "stream unavailable", { status: upstream.status });
    }

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "pipeline stream unreachable", upstream: base },
      { status: 502 },
    );
  }
}