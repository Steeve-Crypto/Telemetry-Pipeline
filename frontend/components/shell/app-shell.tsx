import { KeyboardShortcuts } from "./keyboard-shortcuts";
import { Sidebar } from "./sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-canvas">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-input focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:text-ink"
      >
        Skip to main content
      </a>
      <KeyboardShortcuts />
      <Sidebar />
      <main id="main-content" className="flex min-w-0 flex-1 flex-col" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}