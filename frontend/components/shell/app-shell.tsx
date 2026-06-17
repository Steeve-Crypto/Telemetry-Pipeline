import { KeyboardShortcuts } from "./keyboard-shortcuts";
import { Sidebar } from "./sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-canvas">
      <KeyboardShortcuts />
      <Sidebar />
      <main id="main-content" className="flex min-w-0 flex-1 flex-col">
        {children}
      </main>
    </div>
  );
}