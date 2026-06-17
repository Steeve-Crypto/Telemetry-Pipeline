"use client";

import { usePathname } from "next/navigation";

import { AppShell } from "./app-shell";

const BARE_ROUTES = ["/welcome"];

export function ShellGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (BARE_ROUTES.includes(pathname)) {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}