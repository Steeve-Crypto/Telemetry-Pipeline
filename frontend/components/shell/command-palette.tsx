"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { SearchInput } from "@/components/ui/search-input";
import { useTenant } from "@/contexts/tenant-context";
import { fetchDevices } from "@/lib/api";
import type { DeviceSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/devices", label: "Devices" },
  { href: "/anomalies", label: "Anomalies" },
  { href: "/ops", label: "Ops" },
  { href: "/welcome", label: "Welcome" },
];

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const { tenantId } = useTenant();
  const [query, setQuery] = useState("");
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setQuery("");
    setActiveIndex(0);
    fetchDevices(tenantId).then(({ data }) => setDevices(data));
    const id = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(id);
  }, [open, tenantId]);

  const deviceMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return devices.slice(0, 8);
    }

    return devices
      .filter(
        (device) =>
          device.device_id.toLowerCase().includes(q) ||
          device.sensor_type.toLowerCase().includes(q),
      )
      .slice(0, 8);
  }, [devices, query]);

  const navMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return NAV_ITEMS;
    }

    return NAV_ITEMS.filter((item) => item.label.toLowerCase().includes(q));
  }, [query]);

  const items = useMemo(
    () => [
      ...navMatches.map((item) => ({
        type: "nav" as const,
        key: item.href,
        label: item.label,
        hint: "Go to page",
        href: item.href,
      })),
      ...deviceMatches.map((device) => ({
        type: "device" as const,
        key: device.device_id,
        label: device.device_id,
        hint: device.sensor_type,
        href: `/devices/${encodeURIComponent(device.device_id)}`,
      })),
    ],
    [navMatches, deviceMatches],
  );

  const goTo = useCallback(
    (href: string) => {
      onClose();
      router.push(href);
    },
    [onClose, router],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, Math.max(items.length - 1, 0)));
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((index) => Math.max(index - 1, 0));
        return;
      }

      if (event.key === "Enter" && items[activeIndex]) {
        event.preventDefault();
        goTo(items[activeIndex].href);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, items, activeIndex, goTo, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/30 px-4 pt-24 backdrop-blur-sm"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search and navigate"
        className="w-full max-w-xl rounded-card border border-border bg-surface p-4 shadow-card"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <SearchInput
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
          }}
          placeholder="Search devices or pages…"
          aria-label="Search devices or pages"
        />

        <ul className="mt-3 max-h-72 overflow-y-auto" role="listbox">
          {items.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-muted">No matches</li>
          ) : (
            items.map((item, index) => (
              <li key={`${item.type}-${item.key}`} role="option" aria-selected={index === activeIndex}>
                <button
                  type="button"
                  className={cn(
                    "flex w-full items-center justify-between rounded-input px-3 py-2 text-left text-sm",
                    index === activeIndex
                      ? "bg-accent/10 text-ink"
                      : "text-muted hover:bg-canvas hover:text-ink",
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => goTo(item.href)}
                >
                  <span>{item.label}</span>
                  <span className="text-xs">{item.hint}</span>
                </button>
              </li>
            ))
          )}
        </ul>

        <p className="mt-3 text-center text-[11px] text-muted">
          <kbd className="rounded border border-border px-1.5 py-0.5 font-mono">↑↓</kbd> navigate
          {" · "}
          <kbd className="rounded border border-border px-1.5 py-0.5 font-mono">Enter</kbd> open
          {" · "}
          <kbd className="rounded border border-border px-1.5 py-0.5 font-mono">Esc</kbd> close
        </p>
      </div>
    </div>
  );
}