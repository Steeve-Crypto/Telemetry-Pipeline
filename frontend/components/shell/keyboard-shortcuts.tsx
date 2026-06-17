"use client";

import { CommandPalette } from "@/components/shell/command-palette";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";

export function KeyboardShortcuts() {
  const { paletteOpen, closePalette } = useKeyboardShortcuts();

  return <CommandPalette open={paletteOpen} onClose={closePalette} />;
}