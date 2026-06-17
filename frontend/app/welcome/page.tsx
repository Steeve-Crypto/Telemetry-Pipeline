import { ArrowRight, Radio, Shield, Zap } from "lucide-react";
import Link from "next/link";

"use client";

import { OnboardingChecklist } from "@/components/onboarding/checklist";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import { useOnboardingProgress } from "@/hooks/use-onboarding-progress";

const highlights = [
  {
    icon: Zap,
    title: "Ingest at scale",
    body: "MQTT, Kafka, and WebSocket paths with validation, enrichment, and windowed aggregates.",
  },
  {
    icon: Shield,
    title: "Detect anomalies",
    body: "Ensemble scoring blends statistical, isolation forest, and autoencoder methods.",
  },
  {
    icon: Radio,
    title: "Act on signal",
    body: "Live overview, device drill-down, and Grafana ops — one product surface.",
  },
];

export default function WelcomePage() {
  const { metrics, anomalies, status } = useDashboardData();
  const { steps: onboardingSteps } = useOnboardingProgress(status, metrics, anomalies);

  return (
    <div className="relative min-h-screen overflow-hidden bg-canvas">
      <div
        className="pointer-events-none absolute -left-32 -top-24 h-[28rem] w-[28rem] rounded-full bg-accent/15 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-24 top-1/3 h-80 w-80 rounded-full bg-alert/12 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 left-1/3 h-64 w-96 rounded-full bg-accent/8 blur-3xl"
        aria-hidden
      />

      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/welcome" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-input bg-accent text-surface">
            <Radio className="h-4 w-4" strokeWidth={2} aria-hidden />
          </span>
          <div>
            <p className="font-display text-xl leading-none text-ink">Signal</p>
            <p className="text-[10px] uppercase tracking-widest text-muted">Telemetry</p>
          </div>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-input bg-accent px-4 py-2 text-sm font-medium text-surface transition-opacity hover:opacity-90"
          >
            Open dashboard
            <ArrowRight className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          </Link>
        </div>
      </header>

      <main className="relative mx-auto max-w-6xl px-6 pb-20 pt-10">
        <section className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.2em] text-accent">Telemetry pipeline</p>
          <h1 className="mt-4 font-display text-5xl leading-tight text-ink md:text-6xl">
            Ingest → understand → act
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted">
            Signal turns noisy sensor streams into live context — throughput, latency, anomalies,
            and fleet health in one calm operator experience.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-input bg-accent px-5 py-3 text-sm font-medium text-surface"
            >
              Start monitoring
              <ArrowRight className="h-4 w-4" strokeWidth={1.5} aria-hidden />
            </Link>
            <Link
              href="/ops"
              className="inline-flex items-center gap-2 rounded-input border border-border bg-surface px-5 py-3 text-sm text-ink"
            >
              View ops dashboards
            </Link>
          </div>
        </section>

        <section className="mt-12 max-w-2xl">
          <OnboardingChecklist steps={onboardingSteps} compact />
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-3">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <article
                key={item.title}
                className="rounded-card border border-border bg-surface/80 p-6 shadow-card backdrop-blur-sm"
              >
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-input bg-accent/10 text-accent">
                  <Icon className="h-5 w-5" strokeWidth={1.5} aria-hidden />
                </span>
                <h2 className="mt-4 font-display text-xl text-ink">{item.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
              </article>
            );
          })}
        </section>
      </main>
    </div>
  );
}