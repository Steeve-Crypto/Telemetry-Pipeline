export function ThemeScript() {
  const script = `
    (function () {
      try {
        var stored = localStorage.getItem("signal-theme");
        var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        var dark = stored === "dark" || (stored !== "light" && prefersDark);
        if (dark) document.documentElement.classList.add("dark");
      } catch (e) {}
    })();
  `;

  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}