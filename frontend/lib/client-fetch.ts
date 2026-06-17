"use client";

const TENANT_STORAGE_KEY = "signal-tenant-id";

export function getStoredTenantId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(TENANT_STORAGE_KEY);
}

export function setStoredTenantId(tenantId: string): void {
  window.localStorage.setItem(TENANT_STORAGE_KEY, tenantId);
}

export async function clientFetch(path: string, tenantId?: string | null): Promise<Response> {
  const headers: HeadersInit = {};
  const tid = tenantId ?? getStoredTenantId();
  if (tid) {
    headers["X-Tenant-Id"] = tid;
  }

  return fetch(path, { headers, cache: "no-store" });
}