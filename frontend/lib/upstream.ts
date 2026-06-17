import { NextRequest, NextResponse } from "next/server";

import { getTelemetryApiUrl } from "@/lib/api";

export async function proxyToPipeline(
  request: NextRequest,
  path: string,
): Promise<NextResponse> {
  const apiKey = request.headers.get("x-api-key") ?? undefined;
  const base = getTelemetryApiUrl();
  const query = request.nextUrl.search;

  try {
    const headers: HeadersInit = { Accept: "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const upstream = await fetch(`${base}${path}${query}`, {
      headers,
      cache: "no-store",
    });

    const body = await upstream.text();

    return new NextResponse(body, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: "pipeline unreachable", upstream: base },
      { status: 502 },
    );
  }
}