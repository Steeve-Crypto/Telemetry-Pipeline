"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DeviceCard } from "@/components/devices/device-card";
import { ConnectionStatusBadge } from "@/components/shell/connection-status";
import { TenantSwitcher } from "@/components/shell/tenant-switcher";
import { FilterChips } from "@/components/ui/filter-chips";
import { PageHeader } from "@/components/ui/page-header";
import { SearchInput } from "@/components/ui/search-input";
import { useTenant } from "@/contexts/tenant-context";
import { fetchDevices } from "@/lib/api";
import type { ConnectionStatus, DeviceSummary } from "@/lib/types";

export function DevicesPage() {
  const { tenantId } = useTenant();
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [query, setQuery] = useState("");
  const [sensorFilter, setSensorFilter] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const { data, ok } = await fetchDevices(tenantId);
    setDevices(data);
    setStatus(ok ? "live" : "offline");
  }, [tenantId]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  const sensorTypes = useMemo(
    () => [...new Set(devices.map((d) => d.sensor_type))].sort(),
    [devices],
  );

  const filtered = useMemo(() => {
    return devices.filter((device) => {
      const matchesQuery =
        !query ||
        device.device_id.toLowerCase().includes(query.toLowerCase()) ||
        device.sensor_type.toLowerCase().includes(query.toLowerCase());
      const matchesSensor = !sensorFilter || device.sensor_type === sensorFilter;
      return matchesQuery && matchesSensor;
    });
  }, [devices, query, sensorFilter]);

  return (
    <div className="flex flex-1 flex-col px-8 py-8">
      <PageHeader
        title="Devices"
        description="Fleet inventory with live health and last-seen signal."
      >
        <TenantSwitcher />
        <ConnectionStatusBadge status={status} />
      </PageHeader>

      <div className="mt-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <SearchInput
          placeholder="Search devices or sensor types…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-md"
        />
        <FilterChips
          options={sensorTypes}
          value={sensorFilter}
          onChange={setSensorFilter}
        />
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {filtered.map((device) => (
          <DeviceCard key={device.device_id} device={device} />
        ))}
      </section>

      {filtered.length === 0 && (
        <p className="mt-12 text-center text-sm text-muted">No devices match your filters.</p>
      )}
    </div>
  );
}