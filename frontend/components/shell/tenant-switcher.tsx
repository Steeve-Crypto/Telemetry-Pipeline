"use client";

import { Building2, ChevronDown } from "lucide-react";

import { useTenant } from "@/contexts/tenant-context";
import { cn } from "@/lib/utils";

export function TenantSwitcher() {
  const { tenantId, tenants, tenancyEnabled, setTenantId, loading } = useTenant();

  if (loading || !tenancyEnabled || tenants.length === 0) {
    return null;
  }

  return (
    <label className="relative inline-flex items-center gap-2">
      <Building2 className="h-3.5 w-3.5 text-muted" aria-hidden />
      <span className="sr-only">Select tenant</span>
      <select
        value={tenantId ?? tenants[0]}
        onChange={(e) => setTenantId(e.target.value)}
        className={cn(
          "appearance-none rounded-pill border border-border bg-surface py-1.5 pl-3 pr-8",
          "text-xs font-medium text-ink shadow-sm transition-colors",
          "hover:border-accent/40 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20",
        )}
      >
        {tenants.map((tenant) => (
          <option key={tenant} value={tenant}>
            {tenant}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2 h-3.5 w-3.5 text-muted"
        aria-hidden
      />
    </label>
  );
}