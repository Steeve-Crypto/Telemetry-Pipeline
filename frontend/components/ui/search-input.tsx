import { Search } from "lucide-react";

import { cn } from "@/lib/utils";

interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string;
}

export function SearchInput({ className, ...props }: SearchInputProps) {
  return (
    <div className={cn("relative", className)}>
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
        strokeWidth={1.5}
      />
      <input
        type="search"
        className={cn(
          "w-full rounded-input border border-border bg-surface py-2.5 pl-10 pr-4",
          "text-sm text-ink placeholder:text-muted/70",
          "focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20",
        )}
        {...props}
      />
    </div>
  );
}