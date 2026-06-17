"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function useKeyboardShortcuts() {
  const router = useRouter();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const pendingGo = useRef(false);
  const pendingTimer = useRef<number | null>(null);

  useEffect(() => {
    const clearPending = () => {
      pendingGo.current = false;
      if (pendingTimer.current !== null) {
        window.clearTimeout(pendingTimer.current);
        pendingTimer.current = null;
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (paletteOpen && event.key === "Escape") {
        event.preventDefault();
        setPaletteOpen(false);
        return;
      }

      if (isTypingTarget(event.target)) {
        return;
      }

      if (event.key === "/") {
        event.preventDefault();
        setPaletteOpen(true);
        return;
      }

      if (event.key === "g") {
        clearPending();
        pendingGo.current = true;
        pendingTimer.current = window.setTimeout(clearPending, 1200);
        return;
      }

      if (pendingGo.current && event.key === "o") {
        event.preventDefault();
        clearPending();
        router.push("/");
        return;
      }

      if (pendingGo.current) {
        clearPending();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      clearPending();
    };
  }, [paletteOpen, router]);

  return {
    paletteOpen,
    openPalette: () => setPaletteOpen(true),
    closePalette: () => setPaletteOpen(false),
  };
}