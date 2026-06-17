/** Server-only tenant → API key resolution (never expose keys to the browser). */

export function resolveTenantApiKey(tenantId: string | null): string | undefined {
  if (!tenantId) {
    return undefined;
  }

  const raw = process.env.TENANT_API_KEYS;
  if (!raw) {
    return undefined;
  }

  try {
    const map = JSON.parse(raw) as Record<string, string>;
    const key = map[tenantId];
    return key || undefined;
  } catch {
    return undefined;
  }
}