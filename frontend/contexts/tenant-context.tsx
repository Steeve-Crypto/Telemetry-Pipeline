"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { fetchAppConfig } from "@/lib/api";
import { getStoredTenantId, setStoredTenantId } from "@/lib/client-fetch";

interface TenantContextValue {
  tenantId: string | null;
  tenants: string[];
  tenancyEnabled: boolean;
  setTenantId: (tenantId: string) => void;
  loading: boolean;
}

const TenantContext = createContext<TenantContextValue | null>(null);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [tenantId, setTenantIdState] = useState<string | null>(null);
  const [tenants, setTenants] = useState<string[]>([]);
  const [tenancyEnabled, setTenancyEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function load() {
      const stored = getStoredTenantId();
      const { data } = await fetchAppConfig(stored);

      if (!active) {
        return;
      }

      setTenancyEnabled(data.tenancy.enabled);
      setTenants(data.tenancy.tenants);

      const initial =
        stored ??
        (data.tenancy.enabled ? data.tenancy.default_tenant : null);

      if (initial) {
        setTenantIdState(initial);
        setStoredTenantId(initial);
      }

      setLoading(false);
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  const setTenantId = useCallback((id: string) => {
    setTenantIdState(id);
    setStoredTenantId(id);
  }, []);

  const value = useMemo(
    () => ({ tenantId, tenants, tenancyEnabled, setTenantId, loading }),
    [tenantId, tenants, tenancyEnabled, setTenantId, loading],
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error("useTenant must be used within TenantProvider");
  }
  return ctx;
}